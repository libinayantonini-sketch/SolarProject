"""Cliente HTTP do ESP32 (que age como servidor na rede local). Protocolo: docs/05_PROTOCOLO_ESP32.md.

    GET  /                  -> {"status":"ok", ...}                      (o dispositivo está vivo?)
    POST /upload?pump=0|1   -> corpo = bytes JPEG; resposta = Esp32Result (classificação + decisão da bomba)
"""
from __future__ import annotations

import time

import httpx
from pydantic import ValidationError

from app.schemas.analysis import Esp32Result


class Esp32Error(RuntimeError):
    """Falha ao falar com o ESP32. `status` é o código HTTP que a API devolve ao front."""
    status = 502


class Esp32NotConfigured(Esp32Error):
    status = 503


class Esp32Unreachable(Esp32Error):
    status = 504


class Esp32BadResponse(Esp32Error):
    status = 502


class Esp32Client:
    def __init__(self, base_url: str, key: str = "", timeout: float = 30.0, transport: httpx.BaseTransport | None = None,
                 classes: tuple[str, ...] | None = None) -> None:
        self.classes = tuple(classes) if classes else None       # classes que o modelo do ESP32 tem (ESP32_CLASSES); None = qualquer
        self.base_url = base_url.rstrip("/")
        self.configured = bool(self.base_url)
        headers = {"X-Device-Key": key} if key else {}
        self._http = httpx.Client(timeout=timeout, transport=transport, headers=headers)

    def _require(self) -> None:
        if not self.configured:
            raise Esp32NotConfigured("ESP32_URL não está definido. Veja docs/05_PROTOCOLO_ESP32.md (ou use o simulador).")

    def status(self, timeout: float = 2.5) -> dict:
        """Nunca levanta: devolve {online: False, error} se não responder. Usado pelo indicador do front."""
        if not self.configured:
            return {"configured": False, "online": False, "error": "ESP32_URL não definido"}
        t0 = time.perf_counter()
        try:
            r = self._http.get(self.base_url + "/", timeout=timeout)
            r.raise_for_status()
            info = r.json() if r.headers.get("content-type", "").startswith("application/json") else {}
            return {"configured": True, "online": True, "latency_ms": int((time.perf_counter() - t0) * 1000),
                    "info": info if isinstance(info, dict) else {}}
        except (httpx.HTTPError, ValueError) as exc:
            return {"configured": True, "online": False, "error": f"{type(exc).__name__}"}

    def upload(self, jpeg: bytes, pump: bool) -> tuple[Esp32Result, int]:
        """Envia a imagem; devolve (resultado validado, tempo total em ms)."""
        self._require()
        t0 = time.perf_counter()
        try:
            r = self._http.post(self.base_url + "/upload", params={"pump": int(pump)}, content=jpeg,
                                headers={"Content-Type": "image/jpeg"})
        except httpx.HTTPError as exc:
            raise Esp32Unreachable(f"ESP32 não respondeu ({type(exc).__name__}). Confira Wi-Fi, IP e isolamento de clientes.") from exc
        ms = int((time.perf_counter() - t0) * 1000)
        if r.status_code != 200:
            raise Esp32BadResponse(f"ESP32 respondeu HTTP {r.status_code}: {r.text[:160]}")
        try:
            result = Esp32Result.model_validate(r.json())
        except (ValueError, ValidationError) as exc:
            raise Esp32BadResponse("resposta do ESP32 fora do formato esperado") from exc
        if self.classes and result.classification.value not in self.classes:
            raise Esp32BadResponse(f"o ESP32 devolveu a classe {result.classification.value}, que não está em ESP32_CLASSES "
                                   f"({','.join(self.classes)}). O modelo do ESP32 e a configuração do backend precisam coincidir.")
        return result, ms
