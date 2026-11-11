"""Recomendação de chuva (Open-Meteo). SÓ INFORMA: nunca decide nem aciona a bomba.

Fonte: https://open-meteo.com (dados CC BY 4.0; uso gratuito só não comercial; mostrar o crédito na tela).
Pedimos `precipitation` e `precipitation_probability` por hora, com 1 dia passado e 2 de previsão, e somamos
as 24 h passadas e as 24 h seguintes. Qualquer falha (sem internet, resposta estranha) vira "indisponível":
o resto do sistema não depende disto.

Os limiares (chuva fraca/forte) são PROVISÓRIOS: quantos mm lavam um painel depende de inclinação, poeira e região.
Calibre observando o painel de vocês.
"""
from __future__ import annotations

import threading
from datetime import datetime, timedelta, timezone

import httpx

URL = "https://api.open-meteo.com/v1/forecast"
CREDIT = "Dados meteorológicos: Open-Meteo.com (CC BY 4.0)"
AVISO = "Recomendação baseada em previsão e em limiares provisórios. Ela apenas informa: não aciona a bomba."
MAX_MISSING = 6            # horas sem dado (de 48) toleradas antes de declarar "indisponível"


def advice(past_mm: float, next_mm: float, prob_max: float | None, light: float, heavy: float) -> dict:
    """Regra pura (sem rede). `nivel`: limpar_agora | avaliar | adiar."""
    notes: list[str] = []
    if next_mm >= heavy:
        nivel, titulo = "adiar", "Chuva forte prevista: considere adiar a limpeza"
        msg = (f"Previsão de {next_mm:.1f} mm nas próximas 24 h. Chuva forte tende a lavar o painel; limpar agora pode gastar água à toa.")
    elif next_mm >= light:
        nivel, titulo = "avaliar", "Chuva fraca prevista: avalie esperar passar"
        msg = (f"Previsão de {next_mm:.1f} mm nas próximas 24 h. Chuva fraca pode molhar a poeira e deixar lama e marcas; "
               "se for limpar, o melhor costuma ser depois que a chuva passar.")
    else:
        nivel, titulo = "limpar_agora", "Sem chuva relevante prevista: limpar agora faz sentido"
        msg = f"Previsão de {next_mm:.1f} mm nas próximas 24 h."
        if prob_max is not None and prob_max >= 60:
            notes.append(f"Atenção: a probabilidade máxima de chuva é {prob_max:.0f}%, embora o volume previsto seja baixo.")
    if past_mm >= heavy:
        notes.append(f"Choveu {past_mm:.1f} mm nas últimas 24 h: o painel pode já ter sido lavado. Confira a foto antes de limpar.")
    elif past_mm >= light:
        notes.append(f"Choveu {past_mm:.1f} mm nas últimas 24 h: pode ter sujado (lama) ou limpado um pouco. Confira a foto.")
    return {"nivel": nivel, "titulo": titulo, "mensagem": msg, "observacoes": notes}


def parse(payload: dict, now_utc: datetime, light: float, heavy: float) -> dict | None:
    """Transforma a resposta da Open-Meteo na recomendação. None se os dados não servirem."""
    try:
        h = payload["hourly"]
        times, prec = h["time"], h["precipitation"]
        probs = h.get("precipitation_probability") or [None] * len(times)
        offset = int(payload.get("utc_offset_seconds", 0))
        local = (now_utc + timedelta(seconds=offset)).replace(tzinfo=None, minute=0, second=0, microsecond=0)
        idx = times.index(local.strftime("%Y-%m-%dT%H:%M"))
    except (KeyError, ValueError, TypeError):
        return None
    if idx < 23 or idx + 24 >= len(prec) or len(prec) != len(times):
        return None
    window = prec[idx - 23: idx + 25]
    if sum(v is None for v in window) > MAX_MISSING:
        return None
    clean = lambda xs: sum(v for v in xs if isinstance(v, (int, float)))
    past, nxt = clean(prec[idx - 23: idx + 1]), clean(prec[idx + 1: idx + 25])
    pm = [p for p in probs[idx + 1: idx + 25] if isinstance(p, (int, float))]
    pmax = max(pm) if pm else None
    out = advice(past, nxt, pmax, light, heavy)
    out.update(chuva_24h_passadas_mm=round(past, 1), chuva_24h_proximas_mm=round(nxt, 1),
               prob_max_24h=pmax)
    return out


class WeatherClient:
    def __init__(self, lat: float, lon: float, light: float, heavy: float, *, ttl_s: int = 1800, timeout: float = 4.0,
                 transport: httpx.BaseTransport | None = None, now_fn=None) -> None:
        self.lat, self.lon, self.light, self.heavy, self.ttl = lat, lon, light, heavy, ttl_s
        self._http = httpx.Client(timeout=timeout, transport=transport)
        self._now = now_fn or (lambda: datetime.now(timezone.utc))
        self._lock = threading.Lock()
        self._cache: tuple[datetime, dict] | None = None      # (quando buscou, recomendação)

    def _fetch(self) -> dict | None:
        try:
            r = self._http.get(URL, params={
                "latitude": self.lat, "longitude": self.lon, "hourly": "precipitation,precipitation_probability",
                "past_days": 1, "forecast_days": 2, "timezone": "America/Sao_Paulo"})
            r.raise_for_status()
            return parse(r.json(), self._now(), self.light, self.heavy)
        except (httpx.HTTPError, ValueError):
            return None

    def get(self) -> dict:
        base = {"fonte": CREDIT, "aviso": AVISO, "limiares": {"fraca_mm": self.light, "forte_mm": self.heavy},
                "local": {"lat": self.lat, "lon": self.lon}}
        with self._lock:                                       # uma busca por vez; várias abas não multiplicam chamadas
            now = self._now()
            if self._cache and (now - self._cache[0]).total_seconds() < self.ttl:
                return {**base, **self._cache[1], "disponivel": True, "desatualizado": False, "atualizado_em": self._cache[0]}
            fresh = self._fetch()
            if fresh:
                self._cache = (now, fresh)
                return {**base, **fresh, "disponivel": True, "desatualizado": False, "atualizado_em": now}
            if self._cache and (now - self._cache[0]).total_seconds() < 6 * 3600:
                return {**base, **self._cache[1], "disponivel": True, "desatualizado": True, "atualizado_em": self._cache[0]}
            return {**base, "disponivel": False, "nivel": "indisponivel", "titulo": "Sem dados de chuva agora",
                    "mensagem": "Não consegui consultar a previsão (sem internet?). O sistema continua funcionando normalmente.",
                    "observacoes": [], "atualizado_em": None, "desatualizado": False}


class DisabledWeather:
    def get(self) -> dict:
        return {"disponivel": False, "nivel": "desativado", "titulo": "Recomendação de chuva desativada",
                "mensagem": "WEATHER_ENABLED=0.", "observacoes": [], "fonte": CREDIT, "aviso": AVISO}
