from datetime import datetime, timedelta, timezone

import httpx
from fastapi.testclient import TestClient

from app.api.routes import create_app
from app.services.assistant.service import Assistant
from app.services.esp32 import Esp32Client
from app.services.storage import ImageStore
from app.services.weather import WeatherClient, advice, parse

NOW = datetime(2026, 11, 9, 13, 20, tzinfo=timezone.utc)          # 10:20 em Londrina (UTC-3)
START = datetime(2026, 11, 8, 0, 0)                               # past_days=1 começa ontem 00:00 local


def payload(past=0.0, nxt=0.0, prob=10, missing=0, offset=-10800):
    times = [(START + timedelta(hours=i)).strftime("%Y-%m-%dT%H:%M") for i in range(72)]
    idx = 24 + 10                                                  # hoje 10:00 local
    prec = [0.0] * 72
    for i in range(idx - 23, idx + 1):
        prec[i] = past / 24
    for i in range(idx + 1, idx + 25):
        prec[i] = nxt / 24
    for i in range(missing):
        prec[idx + 1 + i] = None
    return {"utc_offset_seconds": offset, "hourly": {"time": times, "precipitation": prec, "precipitation_probability": [prob] * 72}}


def test_advice_levels():
    assert advice(0, 0.2, 10, 1, 10)["nivel"] == "limpar_agora"
    assert advice(0, 1.0, 10, 1, 10)["nivel"] == "avaliar"
    assert advice(0, 9.9, 10, 1, 10)["nivel"] == "avaliar"
    assert advice(0, 10.0, 10, 1, 10)["nivel"] == "adiar"
    a = advice(12, 0, 80, 1, 10)
    assert a["nivel"] == "limpar_agora" and len(a["observacoes"]) == 2     # probabilidade alta + choveu forte antes


def test_parse_sums_windows():
    r = parse(payload(past=6, nxt=3), NOW, 1, 10)
    assert r["chuva_24h_passadas_mm"] == 6.0 and r["chuva_24h_proximas_mm"] == 3.0 and r["nivel"] == "avaliar"
    assert parse(payload(nxt=15), NOW, 1, 10)["nivel"] == "adiar"


def test_parse_rejects_bad_data():
    assert parse({}, NOW, 1, 10) is None
    assert parse(payload(missing=7), NOW, 1, 10) is None
    assert parse(payload(missing=6), NOW, 1, 10) is not None              # tolera poucas lacunas
    assert parse(payload(), NOW + timedelta(days=5), 1, 10) is None        # hora atual fora da janela


def client_with(handler, clock):
    return WeatherClient(-23.3, -51.1, 1, 10, transport=httpx.MockTransport(handler), now_fn=lambda: clock[0])


def test_request_params_cache_and_stale_fallback():
    clock, calls = [NOW], []
    fail = [False]

    def handler(req: httpx.Request):
        calls.append(req)
        return httpx.Response(500) if fail[0] else httpx.Response(200, json=payload(nxt=15))

    w = client_with(handler, clock)
    r = w.get()
    q = dict(calls[0].url.params)
    assert q["hourly"] == "precipitation,precipitation_probability" and q["past_days"] == "1" and q["timezone"] == "America/Sao_Paulo"
    assert r["disponivel"] and r["nivel"] == "adiar" and "Open-Meteo" in r["fonte"]
    clock[0] = NOW + timedelta(minutes=10)
    w.get()
    assert len(calls) == 1                                                  # cache: não repete a chamada
    clock[0] = NOW + timedelta(minutes=40); fail[0] = True
    r = w.get()
    assert len(calls) == 2 and r["disponivel"] and r["desatualizado"]       # falhou: usa o último valor, marcado
    clock[0] = NOW + timedelta(hours=7)
    r = w.get()
    assert not r["disponivel"] and r["nivel"] == "indisponivel"             # velho demais: indisponível


def test_unavailable_when_offline():
    w = client_with(lambda r: (_ for _ in ()).throw(httpx.ConnectError("x")), [NOW])
    r = w.get()
    assert r["disponivel"] is False and "continua funcionando" in r["mensagem"]


def test_route_and_config(repo, settings):
    w = client_with(lambda r: httpx.Response(200, json=payload(nxt=3)), [NOW])
    app = create_app(settings, repo=repo, esp32=Esp32Client(""), assistant=Assistant(None),
                     store=ImageStore(settings.storage_dir), weather=w)
    with TestClient(app) as c:
        j = c.get("/api/weather/advice").json()
        assert j["nivel"] == "avaliar" and j["limiares"] == {"fraca_mm": 1, "forte_mm": 10} and "não aciona a bomba" in j["aviso"]
        assert c.get("/api/config").json()["weather"] is True
