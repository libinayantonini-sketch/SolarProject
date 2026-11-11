"""O simulador precisa obedecer ao mesmo protocolo e às mesmas regras de segurança do firmware."""
import httpx

from tests.conftest import BLUE, GREEN, RED, make_jpeg


def url(simulator):
    return simulator[1]


def up(simulator, body, pump=1, key="chave-esp"):
    return httpx.post(url(simulator) + f"/upload?pump={pump}", content=body, headers={"X-Device-Key": key})


def test_status(simulator):
    j = httpx.get(url(simulator) + "/").json()
    assert j["status"] == "ok" and j["input_size"] == 32


def test_key_required(simulator):
    assert up(simulator, make_jpeg(BLUE), key="errada").status_code == 401


def test_rejects_wrong_size_non_jpeg_and_huge(simulator):
    assert up(simulator, make_jpeg(BLUE, size=(64, 64))).status_code == 422
    assert up(simulator, b"lixo").status_code == 422
    assert up(simulator, b"0" * (32 * 1024 + 1)).status_code == 413
    assert httpx.post(url(simulator) + "/upload", content=b"", headers={"X-Device-Key": "chave-esp"}).status_code == 400


def test_policy(simulator):
    assert up(simulator, make_jpeg(RED)).json()["cleaning_activated"] is False
    assert up(simulator, make_jpeg(GREEN)).json()["cleaning_activated"] is False
    assert up(simulator, make_jpeg(BLUE, noise_seed=1), pump=0).json()["cleaning_activated"] is False
    first = up(simulator, make_jpeg(BLUE, noise_seed=2)).json()
    assert first["cleaning_activated"] and first["pump_duration_ms"] == 3000
    assert up(simulator, make_jpeg(BLUE, noise_seed=3)).json()["cleaning_activated"] is False      # cooldown
