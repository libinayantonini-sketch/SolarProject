import httpx
import pytest
from fastapi.testclient import TestClient

from app.api.routes import create_app
from app.services.assistant.service import Assistant
from app.services.esp32 import Esp32Client
from app.services.storage import ImageStore
from tests.conftest import BLUE, GREEN, KEY, RED, make_jpeg, post


def test_health_config_status(client, simulator):
    h = client.get("/api/health").json()
    assert h["banco"] and h["esp32_configurado"] and h["ia_gemini"] is False and h["admin_protegido"] and h["modelo_servidor"]
    c = client.get("/api/config").json()
    assert c["engines"]["esp32"]["input_size"] == 32 and c["jpeg_quality"] and c["max_upload_mb"] == 1
    assert c["engines"]["esp32"]["classes"] == ["LIMPO", "MODERADO", "SEVERO"] and c["upload_max_side"] == 512
    assert c["engines"]["server"]["disponivel"] and c["engines"]["server"]["classes"] == ["LIMPO", "MODERADO", "SEVERO"]
    s = client.get("/api/devices/status").json()
    assert s["online"] and s["info"]["device"] == "esp32-simulator"


def test_analyze_stores_file_and_row(client):
    r = post(client, make_jpeg(RED), headers=KEY)
    assert r.status_code == 200
    a = r.json()["analise"]
    assert a["classification"] == "LIMPO" and a["cleaning_activated"] is False and a["model_version"] == "teste-sintetico"
    assert a["dirt_level"] is None and a["round_trip_ms"] is not None
    img = client.get(a["image_url"])
    assert img.status_code == 200 and img.content[:2] == b"\xff\xd8"
    assert client.store.resolve(client.app.state.repo.image_path(a["id"]))        # está em arquivo, não no banco
    assert client.get(f"/api/analyses/{a['id']}").json()["id"] == a["id"]


def test_pump_only_severe_and_cooldown(client):
    assert post(client, make_jpeg(GREEN), headers=KEY).json()["analise"]["cleaning_activated"] is False        # MODERADO nunca
    sev = post(client, make_jpeg(BLUE, noise_seed=1), headers=KEY).json()["analise"]
    assert sev["classification"] == "SEVERO" and sev["cleaning_activated"] and sev["pump_duration_ms"] == 3000
    again = post(client, make_jpeg(BLUE, noise_seed=2), headers=KEY).json()["analise"]
    assert not again["cleaning_activated"] and "intervalo" in again["pump_reason"]                              # cooldown no "firmware"
    assert client.get("/api/stats").json()["limpezas_acionadas"] == 1


def test_pump_blocked_without_admin_key_and_with_flag_off(client):
    j = post(client, make_jpeg(BLUE)).json()
    assert j["bomba_bloqueada_por_falta_de_chave"] and not j["analise"]["cleaning_activated"]
    j = post(client, make_jpeg(BLUE, noise_seed=3), headers=KEY, pump="false").json()
    assert not j["analise"]["cleaning_activated"] and "pump=0" in j["analise"]["pump_reason"]


def test_stored_image_keeps_proportion_and_is_capped(client):
    a = post(client, make_jpeg(BLUE, size=(200, 120)), headers=KEY, pump="false").json()["analise"]
    assert (a["width"], a["height"]) == (200, 120)                       # guardada normalizada; o ESP32 recebeu a versão 32×32
    big = post(client, make_jpeg(BLUE, size=(1600, 800), noise_seed=5), headers=KEY, pump="false").json()["analise"]
    assert (big["width"], big["height"]) == (512, 256)                    # reduzida sem esticar até UPLOAD_MAX_SIDE
    png = post(client, make_jpeg(RED, size=(50, 50), fmt="PNG"), name="x.png", headers=KEY, pump="false")
    assert png.status_code == 200


def test_bad_uploads(client):
    assert post(client, b"isto nao e imagem").status_code == 422
    assert post(client, b"").status_code == 400
    assert post(client, b"0" * (1024 * 1024 + 5)).status_code == 413
    assert client.get("/api/stats").json()["total"] == 0                  # nada gravado


def test_list_filter_relabel_delete(client):
    ids = [post(client, make_jpeg(c, noise_seed=i), headers=KEY, pump="false").json()["analise"]["id"]
           for i, c in enumerate([RED, GREEN, BLUE])]
    assert client.get("/api/analyses", params={"labels": "SEVERO"}).json()["total"] == 1
    assert client.get("/api/analyses", params={"labels": "XX"}).status_code == 422
    assert client.patch(f"/api/analyses/{ids[0]}/label", json={"label": "SEVERO"}).status_code == 401
    a = client.patch(f"/api/analyses/{ids[0]}/label", json={"label": "SEVERO"}, headers=KEY).json()
    assert a["final_label"] == "SEVERO" and a["classification"] == "LIMPO"                   # o que o ESP32 disse fica intacto
    assert client.get("/api/stats").json()["por_rotulo"]["SEVERO"] == 2
    rel = client.app.state.repo.image_path(ids[1])
    assert client.delete(f"/api/analyses/{ids[1]}").status_code == 401
    assert client.delete(f"/api/analyses/{ids[1]}", headers=KEY).status_code == 204
    assert client.get(f"/api/analyses/{ids[1]}").status_code == 404 and client.store.resolve(rel) is None
    total = client.get("/api/analyses", params={"limit": 2, "offset": 1}).json()
    assert total["total"] == 2 and len(total["itens"]) == 1


def test_assistant_fallback(client):
    post(client, make_jpeg(BLUE), headers=KEY, pump="false")
    j = client.post("/api/assistant/ask", json={"question": "análises sujas de hoje"}).json()
    assert j["fonte"] == "regras" and j["total"] == 1 and j["analises"][0]["final_label"] == "SEVERO"
    assert "IA" in client.post("/api/assistant/explain", json={"question": "o que é soiling?"}).json()["texto"]


def _app(repo, settings, handler):
    esp = Esp32Client("http://esp.local", "k", transport=httpx.MockTransport(handler))
    return create_app(settings, repo=repo, esp32=esp, assistant=Assistant(None), store=ImageStore(settings.storage_dir))


@pytest.mark.parametrize("handler,code", [
    (lambda r: (_ for _ in ()).throw(httpx.ConnectError("x")), 504),                                  # ESP32 fora do ar
    (lambda r: httpx.Response(500, text="boom"), 502),
    (lambda r: httpx.Response(200, json={"classification": "XYZ", "confidence": 0.9}), 502),          # classe inventada
    (lambda r: httpx.Response(200, json={"classification": "SEVERO", "confidence": 0.9, "pump_duration_ms": 999999}), 502),
])
def test_esp32_failures_store_nothing(repo, settings, handler, code):
    with TestClient(_app(repo, settings, handler)) as c:
        r = post(c, make_jpeg(BLUE), headers=KEY)
        assert r.status_code == code
        assert c.get("/api/stats").json()["total"] == 0
        assert not any(c.app.state.store.root.rglob("*.jpg"))                                         # sem arquivo órfão
        assert c.get("/api/devices/status").json()["online"] in (False, True)


def test_esp32_not_configured(repo, settings):
    app = create_app(settings, repo=repo, esp32=Esp32Client(""), assistant=Assistant(None), store=ImageStore(settings.storage_dir))
    with TestClient(app) as c:
        assert post(c, make_jpeg(RED)).status_code == 503
        assert c.get("/api/devices/status").json() == {"configured": False, "online": False, "error": "ESP32_URL não definido"}


def test_path_traversal_blocked(tmp_path):
    s = ImageStore(tmp_path / "a")
    (tmp_path / "secret.txt").write_text("x")
    assert s.resolve("../secret.txt") is None


def test_sqlite_file_dir_is_created(tmp_path):
    from app.database.repository import Repository
    r = Repository(f"sqlite:///{tmp_path}/novo/dir/app.db")
    r.create_schema()
    assert r.ping()
    r.dispose()
