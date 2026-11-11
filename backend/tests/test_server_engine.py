"""Modo "servidor" (modelo grande ONNX) ao lado do modo ESP32: dois modos, sem comparação. Classes e tamanhos são configuração."""
import io
import json
import zipfile

import httpx
import pytest
from fastapi.testclient import TestClient

from app.api.routes import create_app
from app.config import Settings
from app.labels import UnknownClassError, parse_classes
from app.services.assistant.service import Assistant
from app.services.esp32 import Esp32Client
from app.services.server_model import ServerModel, ServerModelUnavailable, try_load
from app.services.storage import ImageStore
from tests.conftest import BLUE, GREEN, KEY, RED, make_jpeg, post


def test_server_engine_classifies_and_never_pumps(client):
    r = post(client, make_jpeg(BLUE, size=(200, 120)), headers=KEY, engine="server", pump="true")
    j = r.json()
    a = j["analise"]
    assert r.status_code == 200 and a["engine"] == "server" and a["classification"] == "SEVERO"
    assert a["cleaning_activated"] is False and a["pump_duration_ms"] == 0 and "não aciona a bomba" in a["pump_reason"]
    assert j["bomba_bloqueada_por_falta_de_chave"] is False                     # não há bomba para bloquear
    assert set(a["probs"]) == {"LIMPO", "MODERADO", "SEVERO"} and a["model_version"] == "teste-sintetico"
    assert (a["width"], a["height"]) == (200, 120)
    assert client.app.state.esp32.status()["online"]                            # o simulador seguiu intocado
    assert client.get("/api/stats").json()["limpezas_acionadas"] == 0


def test_server_engine_does_not_call_the_esp32(repo, settings, server_model):
    def boom(request):
        raise AssertionError("o ESP32 não deveria ser chamado no modo servidor")
    esp = Esp32Client("http://esp.local", "k", transport=httpx.MockTransport(boom))
    app = create_app(settings, repo=repo, esp32=esp, assistant=Assistant(None), store=ImageStore(settings.storage_dir),
                     server_model=server_model)
    with TestClient(app) as c:
        assert post(c, make_jpeg(GREEN), engine="server").status_code == 200


def test_default_engine_is_esp32_and_only_two_modes(client):
    assert post(client, make_jpeg(RED), headers=KEY).json()["analise"]["engine"] == "esp32"
    assert post(client, make_jpeg(RED, noise_seed=2), headers=KEY, engine="both").status_code == 422     # comparar não existe


def test_server_model_missing_is_503_and_stores_nothing(repo, settings, simulator, tmp_path):
    _, url = simulator
    app = create_app(settings, repo=repo, esp32=Esp32Client(url, "chave-esp"), assistant=Assistant(None),
                     store=ImageStore(settings.storage_dir))                      # sem server_model: SERVER_MODEL_DIR não existe
    with TestClient(app) as c:
        cfg = c.get("/api/config").json()["engines"]
        assert cfg["server"]["disponivel"] is False and "faltam" in cfg["server"]["motivo"]
        assert c.get("/api/health").json()["modelo_servidor"] is False
        r = post(c, make_jpeg(RED), engine="server")
        assert r.status_code == 503 and "indisponível" in r.json()["detail"]
        assert c.get("/api/stats").json()["total"] == 0 and not any(c.app.state.store.root.rglob("*.jpg"))
        assert post(c, make_jpeg(RED), headers=KEY, pump="false").status_code == 200     # o modo ESP32 segue funcionando


def test_stats_and_filter_by_engine(client):
    post(client, make_jpeg(RED), headers=KEY, pump="false")
    post(client, make_jpeg(BLUE, noise_seed=1), engine="server")
    post(client, make_jpeg(GREEN, noise_seed=2), engine="server")
    assert client.get("/api/stats").json()["por_motor"] == {"esp32": 1, "server": 2}
    assert client.get("/api/analyses", params={"engine": "server"}).json()["total"] == 2
    assert client.get("/api/analyses", params={"engine": "esp32"}).json()["itens"][0]["engine"] == "esp32"
    assert client.get("/api/analyses", params={"engine": "both"}).status_code == 422


def test_export_training_zip(client):
    ids = [post(client, make_jpeg(c, noise_seed=i), headers=KEY, engine=e, pump="false").json()["analise"]["id"]
           for i, (c, e) in enumerate([(RED, "esp32"), (BLUE, "server"), (GREEN, "server")])]
    assert client.get("/api/export/training.zip").status_code == 401                # exige chave de administrador
    assert client.get("/api/export/training.zip", headers=KEY).status_code == 404   # ninguém revisou ainda
    client.patch(f"/api/analyses/{ids[0]}/label", json={"label": "MODERADO"}, headers=KEY)
    client.patch(f"/api/analyses/{ids[1]}/label", json={"label": "SEVERO"}, headers=KEY)
    r = client.get("/api/export/training.zip", headers=KEY)
    z = zipfile.ZipFile(io.BytesIO(r.content))
    assert r.headers["content-type"] == "application/zip"
    assert sorted(z.namelist()) == sorted([f"MODERADO/{ids[0]}.jpg", f"SEVERO/{ids[1]}.jpg", "labels.csv"])
    assert z.read(f"SEVERO/{ids[1]}.jpg")[:2] == b"\xff\xd8" and "server" in z.read("labels.csv").decode()
    everything = zipfile.ZipFile(io.BytesIO(client.get("/api/export/training.zip", params={"only_reviewed": "false"}, headers=KEY).content))
    assert len(everything.namelist()) == 4
    only_server = zipfile.ZipFile(io.BytesIO(client.get("/api/export/training.zip", params={"engine": "server"}, headers=KEY).content))
    assert sorted(only_server.namelist()) == sorted([f"SEVERO/{ids[1]}.jpg", "labels.csv"])


# ---------- classes e tamanhos são configuráveis ----------
def test_parse_classes():
    assert [l.value for l in parse_classes("LIMPO, SEVERO")] == ["LIMPO", "SEVERO"]
    assert [l.value for l in parse_classes(["limpo", "moderado", "severo"])] == ["LIMPO", "MODERADO", "SEVERO"]
    for bad in ("LIMPO,MODERADO", "LIMPO,LIMPO,SEVERO", "LIMPO,SEVERO,XYZ", "SEVERO", ""):
        with pytest.raises(UnknownClassError):
            parse_classes(bad)


def test_settings_from_env(monkeypatch):
    monkeypatch.setenv("ESP32_CLASSES", "LIMPO,SEVERO")
    monkeypatch.setenv("ESP32_INPUT_SIZE", "128")
    monkeypatch.setenv("SERVER_INPUT_SIZE", "256")
    s = Settings.from_env()
    assert s.esp32_classes == ("LIMPO", "SEVERO") and s.input_size == 128 and s.server_input_size == 256
    monkeypatch.delenv("ESP32_INPUT_SIZE")
    monkeypatch.setenv("INPUT_SIZE", "64")                                          # nome antigo continua valendo
    assert Settings.from_env().input_size == 64
    monkeypatch.setenv("ESP32_CLASSES", "LIMPO,MODERADO")
    with pytest.raises(UnknownClassError):
        Settings.from_env()


def test_esp32_with_two_classes_rejects_a_third(repo, settings, simulator):
    _, url = simulator
    esp = Esp32Client(url, "chave-esp", classes=("LIMPO", "SEVERO"))
    app = create_app(settings, repo=repo, esp32=esp, assistant=Assistant(None), store=ImageStore(settings.storage_dir))
    with TestClient(app) as c:
        assert post(c, make_jpeg(RED), headers=KEY, pump="false").status_code == 200
        r = post(c, make_jpeg(GREEN, noise_seed=1), headers=KEY, pump="false")        # o "ESP32" respondeu MODERADO
        assert r.status_code == 502 and "ESP32_CLASSES" in r.json()["detail"]
        assert c.get("/api/stats").json()["total"] == 1
        assert c.get("/api/config").json()["engines"]["esp32"]["classes"] == ["LIMPO", "MODERADO", "SEVERO"]   # vem de Settings, não do cliente


def test_server_input_size_is_adjustable(tiny_dir):
    assert ServerModel.load(tiny_dir).size == 32                                    # padrão: model_card.json
    assert ServerModel.load(tiny_dir, input_size=64).size == 64                     # SERVER_INPUT_SIZE manda


def test_server_model_loader_errors(tiny_dir, tmp_path):
    model, why = try_load(str(tmp_path / "nao-existe"))
    assert model is None and "faltam" in why
    bad = tmp_path / "bad"
    bad.mkdir()
    for n in ("model.onnx", "model_card.json"):
        (bad / n).write_bytes(open(f"{tiny_dir}/{n}", "rb").read())
    (bad / "labels.json").write_text(json.dumps(["LIMPO", "SEVERO"]))                # card diz 2 classes, o ONNX tem 3 saídas
    model, why = try_load(str(bad))
    assert model is None and "3 saídas" in why
    (bad / "labels.json").write_text(json.dumps(["LIMPO", "XYZ", "SEVERO"]))
    assert "inválido" in try_load(str(bad))[1]
    with pytest.raises(ServerModelUnavailable):
        ServerModel.load(tmp_path / "vazia")


def test_old_database_gets_the_engine_column(tmp_path):
    from sqlalchemy import create_engine, text
    from app.database.repository import Repository
    url = f"sqlite:///{tmp_path}/velho.db"
    old = create_engine(url)
    with old.begin() as c:                                                           # tabela como era antes do modo servidor
        c.execute(text("CREATE TABLE analyses (id INTEGER PRIMARY KEY AUTOINCREMENT, image_path VARCHAR(300) NOT NULL, "
                       "original_filename VARCHAR(255), classification VARCHAR(10) NOT NULL, confidence FLOAT NOT NULL, probs JSON, "
                       "low_confidence BOOLEAN, cleaning_activated BOOLEAN, pump_duration_ms INTEGER, pump_reason VARCHAR(200), "
                       "dirt_level FLOAT, model_version VARCHAR(80), inference_ms INTEGER, round_trip_ms INTEGER, width INTEGER NOT NULL, "
                       "height INTEGER NOT NULL, human_label VARCHAR(10), reviewed_at DATETIME, created_at DATETIME)"))
        c.execute(text("INSERT INTO analyses (image_path, classification, confidence, width, height) VALUES ('a.jpg','LIMPO',0.9,96,96)"))
    old.dispose()
    r = Repository(url)
    r.create_schema()
    assert r.get(1)["engine"] == "esp32"                                              # linhas antigas contam como ESP32
    r.dispose()
