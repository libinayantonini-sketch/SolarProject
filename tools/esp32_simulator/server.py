"""Simulador do ESP32: fala o MESMO protocolo do firmware (GET /, POST /upload) e aplica a MESMA política de bomba.

Serve para: testar backend e front sem hardware, ensaiar a apresentação, e ser a "imagem de reserva" se o ESP32 falhar.
NÃO prova que o modelo cabe no ESP32. Isso só se prova no hardware (docs/04_FIRMWARE_ESP32.md).

    python -m esp32_simulator.server --model-dir ai-model/models/current --port 8081
    python -m esp32_simulator.server --demo-model            # modelo sintético de teste (cor dominante), NÃO classifica sujeira
"""
from __future__ import annotations

import argparse
import hmac
import json
import tempfile
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from io import BytesIO
from urllib.parse import parse_qs, urlparse

from PIL import Image

MAX_BODY = 32 * 1024           # igual a MAX_BODY_BYTES do firmware (buffer fixo na RAM)
MAX_PUMP_MS = 60_000


class Device:
    """Estado e política do 'firmware'. Regras iguais às de firmware/esp32 (docs/04_FIRMWARE_ESP32.md, seção Segurança)."""

    def __init__(self, engine, *, key: str = "", pump_ms: int = 5000, cooldown_s: float = 60.0, threshold: float | None = None):
        self.engine, self.key = engine, key
        self.pump_ms = max(1, min(pump_ms, MAX_PUMP_MS))
        self.cooldown_s = max(1.0, cooldown_s)
        self.threshold = threshold if threshold is not None else engine.threshold
        self.last_pump = None          # monotonic
        self.started = time.monotonic()
        self.lock = threading.Lock()   # um upload por vez, como no ESP32 (um buffer só)

    def status(self) -> dict:
        return {"status": "ok", "device": "esp32-simulator", "model_version": self.engine.version, "input_size": self.engine.size,
                "uptime_s": int(time.monotonic() - self.started), "pump_busy": False, "pump_ms": self.pump_ms,
                "cooldown_s": self.cooldown_s, "threshold": self.threshold}

    def decide(self, label: str, conf: float, allow: bool) -> tuple[bool, int, str]:
        now = time.monotonic()
        if not allow:
            return False, 0, "bomba desativada nesta requisição (pump=0)"
        if label != "SEVERO":
            return False, 0, "só SEVERO aciona a bomba"
        if conf < self.threshold:
            return False, 0, "confiança baixa: sem acionamento, revisão humana"
        if self.last_pump is not None and now - self.last_pump < self.cooldown_s:
            return False, 0, f"intervalo mínimo: faltam {int(self.cooldown_s - (now - self.last_pump)) + 1} s"
        self.last_pump = now
        return True, self.pump_ms, "SEVERO com confiança suficiente"

    def upload(self, body: bytes, allow_pump: bool) -> tuple[int, dict]:
        try:
            img = Image.open(BytesIO(body))
            if img.format != "JPEG":
                return 415, {"error": "envie JPEG"}
            img.load()
        except Exception:
            return 422, {"error": "JPEG inválido"}
        if img.size != (self.engine.size, self.engine.size):
            return 422, {"error": f"imagem deve ter {self.engine.size}x{self.engine.size}, recebi {img.width}x{img.height}"}
        with self.lock:
            t0 = time.perf_counter()
            pred = self.engine.predict_image(img.convert("RGB"))
            inf_ms = int((time.perf_counter() - t0) * 1000)
            on, ms, why = self.decide(pred.label, pred.confidence, allow_pump)
        return 200, {"classification": pred.label, "confidence": round(pred.confidence, 4), "probs": pred.probs,
                     "cleaning_activated": on, "pump_duration_ms": ms, "reason": why, "inference_ms": inf_ms,
                     "model_version": self.engine.version}


def make_handler(dev: Device):
    class H(BaseHTTPRequestHandler):
        def log_message(self, *a):  # silencioso nos testes
            pass

        def _send(self, code: int, obj: dict):
            data = json.dumps(obj).encode()
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def _auth(self) -> bool:
            if dev.key and not hmac.compare_digest(self.headers.get("X-Device-Key", ""), dev.key):
                self._send(401, {"error": "X-Device-Key inválida"})
                return False
            return True

        def do_GET(self):
            if urlparse(self.path).path == "/":
                self._send(200, dev.status())
            else:
                self._send(404, {"error": "não encontrado"})

        def do_POST(self):
            u = urlparse(self.path)
            if u.path != "/upload":
                return self._send(404, {"error": "não encontrado"})
            if not self._auth():
                return
            n = int(self.headers.get("Content-Length") or 0)
            if n <= 0:
                return self._send(400, {"error": "corpo vazio"})
            if n > MAX_BODY:
                return self._send(413, {"error": f"máximo {MAX_BODY} bytes"})
            body = self.rfile.read(n)
            allow = parse_qs(u.query).get("pump", ["1"])[0] == "1"
            code, obj = dev.upload(body, allow)
            self._send(code, obj)

    return H


def serve(dev: Device, host: str = "127.0.0.1", port: int = 0) -> ThreadingHTTPServer:
    srv = ThreadingHTTPServer((host, port), make_handler(dev))
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv


def load_engine(model_dir: str):
    from pathlib import Path
    d = Path(model_dir)
    if (d / "model.tflite").is_file():
        from esp32_simulator.tflite_engine import TFLiteEngine
        return TFLiteEngine.load(d)
    from esp32_simulator.classifier import Classifier
    return Classifier.load(d)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--model-dir", default="ai-model/models/current")
    ap.add_argument("--demo-model", action="store_true", help="usa modelo sintético (NÃO classifica sujeira)")
    ap.add_argument("--demo-size", type=int, default=96)
    ap.add_argument("--host", default="0.0.0.0")
    ap.add_argument("--port", type=int, default=8081)
    ap.add_argument("--key", default="", help="X-Device-Key exigida (igual a ESP32_KEY do backend)")
    ap.add_argument("--pump-ms", type=int, default=5000)
    ap.add_argument("--cooldown-s", type=float, default=60.0)
    a = ap.parse_args()
    model_dir = a.model_dir
    if a.demo_model:
        from esp32_simulator.tiny_model import build_tiny_model
        model_dir = str(build_tiny_model(tempfile.mkdtemp(), size=a.demo_size))
        print("AVISO: modelo sintético de teste. Ele decide pela cor dominante, não pela sujeira.")
    dev = Device(load_engine(model_dir), key=a.key, pump_ms=a.pump_ms, cooldown_s=a.cooldown_s)
    srv = ThreadingHTTPServer((a.host, a.port), make_handler(dev))
    print(f"Simulador do ESP32 em http://{a.host}:{a.port}  (modelo {dev.engine.version}, entrada {dev.engine.size}px)")
    srv.serve_forever()


if __name__ == "__main__":
    main()
