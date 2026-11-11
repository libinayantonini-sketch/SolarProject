"""API HTTP (rotas finas). Lógica em app/services e app/database.

Leitura e análise são abertas (demonstração em rede local). Corrigir rótulo, apagar e liberar a BOMBA exigem
X-API-Key quando ADMIN_API_KEY está definida: sem a chave, a análise roda mas a bomba fica bloqueada.
"""

import hmac
import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Annotated, Literal

from fastapi import Depends, FastAPI, File, Form, Header, HTTPException, Query, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles

from app.config import Settings
from app.database.repository import Repository
from app.labels import Label, suggested_action
from app.schemas.analysis import AskIn, RelabelIn
from app.services.analysis import InvalidImage, analyze
from app.services.assistant.gemini import GeminiClient
from app.services.assistant.search import SearchFilter, describe_filter
from app.services.assistant.service import Assistant
from app.services.esp32 import Esp32Client, Esp32Error
from app.services.server_model import ServerModel, ServerModelUnavailable, try_load
from app.services.export import build_training_zip
from app.services.storage import ImageStore
from app.services.weather import DisabledWeather, WeatherClient

log = logging.getLogger("soiling")


def _public(a: dict) -> dict:
    a = dict(a)
    a["acao_sugerida"] = suggested_action(Label(a["final_label"]), bool(a["needs_review"]))
    return a


def create_app(settings: Settings | None = None, *, repo: Repository | None = None, esp32: Esp32Client | None = None,
               assistant: Assistant | None = None, store: ImageStore | None = None, weather=None,
               server_model: ServerModel | None = None) -> FastAPI:
    cfg = settings or Settings.from_env()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.repo = repo or Repository(cfg.database_url)
        app.state.repo.create_schema()
        app.state.store = store or ImageStore(cfg.storage_dir)
        app.state.esp32 = esp32 or Esp32Client(cfg.esp32_url, cfg.esp32_key, cfg.esp32_timeout_s, classes=cfg.esp32_classes)
        if server_model is not None:
            app.state.server_model, app.state.server_error = server_model, None
        else:
            app.state.server_model, app.state.server_error = try_load(cfg.server_model_dir, cfg.server_input_size)
            if app.state.server_error:
                log.info("modelo do servidor indisponível (opcional): %s", app.state.server_error)
        client = GeminiClient(cfg.gemini_api_key, cfg.gemini_model) if cfg.gemini_enabled else None
        app.state.assistant = assistant or Assistant(client)
        app.state.weather = weather or (WeatherClient(cfg.panel_lat, cfg.panel_lon, cfg.rain_light_mm, cfg.rain_heavy_mm)
                                        if cfg.weather_enabled else DisabledWeather())
        yield
        if repo is None:
            app.state.repo.dispose()

    app = FastAPI(title="Soiling Detection", version="1.0.0", lifespan=lifespan,
                  description="Classifica sujeira em painéis solares. Dois modos: ESP32 (classifica e decide a bomba) e servidor (modelo grande ONNX, sem bomba).")
    if cfg.cors_origins:
        app.add_middleware(CORSMiddleware, allow_origins=list(cfg.cors_origins), allow_methods=["*"], allow_headers=["*"])

    def get_repo(request: Request) -> Repository:
        return request.app.state.repo

    R = Annotated[Repository, Depends(get_repo)]

    def is_admin(key: str | None) -> bool:
        return not cfg.admin_api_key or bool(key and hmac.compare_digest(key, cfg.admin_api_key))

    def admin(x_api_key: Annotated[str | None, Header()] = None) -> None:
        if not is_admin(x_api_key):
            raise HTTPException(401, "chave de administrador ausente ou inválida (cabeçalho X-API-Key)")

    Admin = Depends(admin)

    # ---------------- sistema ----------------
    @app.get("/api/health", tags=["sistema"])
    def health(request: Request, repo_: R):
        return {"status": "ok", "banco": repo_.ping(), "esp32_configurado": request.app.state.esp32.configured,
                "modelo_servidor": request.app.state.server_model is not None,
                "ia_gemini": request.app.state.assistant.enabled, "admin_protegido": bool(cfg.admin_api_key)}

    @app.get("/api/config", tags=["sistema"], summary="Parâmetros que o front precisa (modos disponíveis, classes e tamanhos)")
    def config(request: Request):
        sm: ServerModel | None = request.app.state.server_model
        engines = {
            "esp32": {"disponivel": request.app.state.esp32.configured, "classes": list(cfg.esp32_classes),
                      "input_size": cfg.input_size, "aciona_bomba": True,
                      "motivo": None if request.app.state.esp32.configured else "ESP32_URL não definido"},
            "server": {"disponivel": sm is not None, "classes": sm.info()["classes"] if sm else None,
                       "input_size": sm.size if sm else (cfg.server_input_size or None), "aciona_bomba": False,
                       "versao": sm.version if sm else None, "motivo": request.app.state.server_error},
        }
        return {"engines": engines, "upload_max_side": cfg.upload_max_side, "jpeg_quality": cfg.jpeg_quality,
                "max_upload_mb": cfg.max_upload_mb, "low_confidence_threshold": cfg.low_confidence_threshold,
                "weather": cfg.weather_enabled, "ia_gemini": request.app.state.assistant.enabled,
                "admin_protegido": bool(cfg.admin_api_key)}

    @app.get("/api/weather/advice", tags=["sistema"], summary="Recomendação de chuva (só informa; nunca aciona a bomba)")
    def weather_advice(request: Request):
        return request.app.state.weather.get()

    @app.get("/api/devices/status", tags=["sistema"], summary="O ESP32 está online?")
    def device_status(request: Request):
        return request.app.state.esp32.status()

    # ---------------- análises ----------------
    @app.post("/api/analyze", tags=["análises"], summary="Recebe a foto e classifica no ESP32 (decide a bomba) ou no servidor (sem bomba); grava o resultado")
    async def analyze_route(request: Request, repo_: R, file: Annotated[UploadFile, File()], pump: Annotated[bool, Form()] = True,
                            engine: Annotated[Literal["esp32", "server"], Form()] = "esp32",
                            x_api_key: Annotated[str | None, Header()] = None):
        limit = cfg.max_upload_mb * 1024 * 1024
        data = await file.read(limit + 1)
        if len(data) > limit:
            raise HTTPException(413, f"arquivo maior que {cfg.max_upload_mb} MB")
        if not data:
            raise HTTPException(400, "arquivo vazio")
        pump_allowed = engine == "esp32" and pump and is_admin(x_api_key)
        try:
            row = analyze(data, file.filename or "foto", engine=engine, size=cfg.input_size, max_side=cfg.upload_max_side,
                          quality=cfg.jpeg_quality, low_conf=cfg.low_confidence_threshold, pump=pump_allowed,
                          esp32=request.app.state.esp32, server_model=request.app.state.server_model,
                          server_error=request.app.state.server_error, store=request.app.state.store, repo=repo_)
        except InvalidImage as exc:
            raise HTTPException(422, str(exc))
        except (Esp32Error, ServerModelUnavailable) as exc:
            raise HTTPException(exc.status, str(exc))
        return {"analise": _public(row), "bomba_bloqueada_por_falta_de_chave": bool(engine == "esp32" and pump and not pump_allowed)}

    @app.get("/api/analyses", tags=["análises"])
    def list_analyses(repo_: R, labels: Annotated[list[Label] | None, Query()] = None, needs_review: bool | None = None,
                      engine: Literal["esp32", "server"] | None = None, cleaning_activated: bool | None = None, since: datetime | None = None, until: datetime | None = None,
                      text: Annotated[str | None, Query(max_length=80)] = None, limit: int = 24, offset: int = 0):
        f = SearchFilter(labels=labels, needs_review=needs_review, cleaning_activated=cleaning_activated,
                         since=since, until=until, text=text, engine=engine)
        total, rows = repo_.list(f, limit, offset)
        return {"total": total, "itens": [_public(r) for r in rows]}

    @app.get("/api/analyses/{analysis_id}", tags=["análises"])
    def get_analysis(analysis_id: int, repo_: R):
        a = repo_.get(analysis_id)
        if not a:
            raise HTTPException(404, "análise não encontrada")
        return _public(a)

    @app.get("/api/analyses/{analysis_id}/image", tags=["análises"])
    def get_image(analysis_id: int, request: Request, repo_: R):
        rel = repo_.image_path(analysis_id)
        p = request.app.state.store.resolve(rel) if rel else None
        if not p:
            raise HTTPException(404, "imagem não encontrada")
        return FileResponse(p, media_type="image/jpeg", headers={"Cache-Control": "private, max-age=86400"})

    @app.patch("/api/analyses/{analysis_id}/label", tags=["análises"], dependencies=[Admin])
    def relabel(analysis_id: int, body: RelabelIn, repo_: R):
        a = repo_.relabel(analysis_id, body.label)
        if not a:
            raise HTTPException(404, "análise não encontrada")
        return _public(a)

    @app.delete("/api/analyses/{analysis_id}", tags=["análises"], dependencies=[Admin], status_code=204)
    def delete_analysis(analysis_id: int, request: Request, repo_: R):
        rel = repo_.delete(analysis_id)
        if rel is None:
            raise HTTPException(404, "análise não encontrada")
        request.app.state.store.delete(rel)

    @app.get("/api/export/training.zip", tags=["análises"], dependencies=[Admin],
             summary="Fotos revisadas em pastas por classe (LIMPO/MODERADO/SEVERO) + labels.csv, para retreinar")
    def export_training(request: Request, repo_: R, only_reviewed: bool = True,
                        engine: Literal["esp32", "server"] | None = None):
        rows = [r for r in repo_.export_rows(only_reviewed) if engine is None or r["engine"] == engine]
        if not rows:
            raise HTTPException(404, "nenhuma foto para exportar (revise algumas análises ou use only_reviewed=false)")
        data = build_training_zip(rows, request.app.state.store)
        return Response(data, media_type="application/zip",
                        headers={"Content-Disposition": 'attachment; filename="fotos-para-retreino.zip"'})

    @app.get("/api/stats", tags=["análises"])
    def stats(repo_: R):
        return repo_.stats()

    # ---------------- assistente (Gemini, com plano B) ----------------
    @app.post("/api/assistant/ask", tags=["assistente"])
    def ask(body: AskIn, request: Request, repo_: R):
        a: Assistant = request.app.state.assistant
        now = datetime.now(timezone.utc)
        f, fonte_filtro = a.interpret(body.question, now)
        total, rows = repo_.list(f, 12, 0)
        resumo, fonte = a.summarize(body.question, f, total, repo_.stats(now))
        return {"filtro": f.model_dump(mode="json", exclude_none=True), "filtro_texto": describe_filter(f), "total": total,
                "analises": [_public(r) for r in rows], "resumo": resumo, "fonte": fonte, "fonte_filtro": fonte_filtro}

    @app.post("/api/assistant/explain", tags=["assistente"])
    def explain(body: AskIn, request: Request):
        texto, fonte = request.app.state.assistant.explain(body.question)
        return {"texto": texto, "fonte": fonte, "aviso": "Informação geral gerada por IA; não vem dos dados do projeto."}

    # ---------------- front (build do React) ----------------
    if cfg.frontend_dir and Path(cfg.frontend_dir).is_dir():
        app.mount("/", StaticFiles(directory=cfg.frontend_dir, html=True), name="web")
    return app
