"""Fluxo de uma análise, em um de dois modos (`engine`):

  esp32   a foto vira JPEG do tamanho do modelo do ESP32 -> o ESP32 classifica e decide a bomba (como sempre).
  server  a foto é classificada aqui, pelo modelo grande (ONNX), no tamanho que ele espera. NÃO aciona a bomba.

Nos dois casos o arquivo guardado é a foto normalizada (orientação corrigida, no máximo `max_side` px de lado):
é ela que serve para retreinar qualquer um dos modelos. O tamanho de entrada de cada modelo é configuração
(ESP32_INPUT_SIZE e SERVER_INPUT_SIZE/model_card), não está fixo no código.
"""
from __future__ import annotations

import time
from dataclasses import dataclass
from io import BytesIO

from PIL import Image, ImageOps

from app.database.repository import Repository
from app.services.esp32 import Esp32Client
from app.services.server_model import ServerModel, ServerModelUnavailable
from app.services.storage import ImageStore

MAX_PIXELS = 50_000_000
SERVER_PUMP_REASON = "análise do modelo do servidor: ele não aciona a bomba"


class InvalidImage(ValueError):
    pass


@dataclass(frozen=True)
class Normalized:
    jpeg: bytes
    image: Image.Image
    width: int
    height: int


def normalize_image(data: bytes, max_side: int, quality: int = 85) -> Normalized:
    """Valida, corrige a orientação, converte para RGB e reduz (sem esticar) até `max_side`. Nunca amplia."""
    Image.MAX_IMAGE_PIXELS = MAX_PIXELS
    try:
        probe = Image.open(BytesIO(data))
        fmt = probe.format
        probe.verify()
        img = Image.open(BytesIO(data))
        if img.width * img.height > MAX_PIXELS:
            raise InvalidImage("imagem grande demais")
        if fmt not in {"JPEG", "PNG", "WEBP"}:
            raise InvalidImage(f"formato {fmt} não suportado; envie JPEG, PNG ou WEBP")
        untouched = fmt == "JPEG" and max(img.size) <= max_side and not img.getexif().get(274)
        img = ImageOps.exif_transpose(img).convert("RGB")
        if max(img.size) > max_side:
            img.thumbnail((max_side, max_side), Image.LANCZOS)
            untouched = False
        img.load()
    except InvalidImage:
        raise
    except Exception as exc:
        raise InvalidImage(f"arquivo não é uma imagem válida ({type(exc).__name__})") from exc
    if untouched:
        return Normalized(data, img, img.width, img.height)       # já vem do tamanho certo: não recodifica
    buf = BytesIO()
    img.save(buf, "JPEG", quality=quality)
    return Normalized(buf.getvalue(), img, img.width, img.height)


def esp32_jpeg(img: Image.Image, size: int, quality: int = 85) -> bytes:
    """JPEG size×size (estica, igual ao treino) para o ESP32."""
    buf = BytesIO()
    img.resize((size, size), Image.BILINEAR).save(buf, "JPEG", quality=quality)
    return buf.getvalue()


def analyze(data: bytes, filename: str, *, engine: str = "esp32", size: int, max_side: int, quality: int, low_conf: float,
            pump: bool, esp32: Esp32Client, server_model: ServerModel | None, server_error: str | None = None,
            store: ImageStore, repo: Repository) -> dict:
    norm = normalize_image(data, max_side, quality)
    if engine == "server":
        if server_model is None:
            raise ServerModelUnavailable(f"modelo do servidor indisponível: {server_error or 'não configurado'}")
        t0 = time.perf_counter()
        pred = server_model.predict(norm.image)
        total_ms = int((time.perf_counter() - t0) * 1000)
        fields = dict(classification=pred.label.value, confidence=pred.confidence, probs=pred.probs,
                      low_confidence=pred.confidence < low_conf, cleaning_activated=False, pump_duration_ms=0,
                      pump_reason=SERVER_PUMP_REASON, dirt_level=None, model_version=pred.model_version,
                      inference_ms=int(pred.latency_ms), round_trip_ms=total_ms)
    else:
        result, round_trip_ms = esp32.upload(esp32_jpeg(norm.image, size, quality), pump)       # falhou? nada é gravado
        fields = dict(classification=result.classification.value, confidence=result.confidence, probs=result.probs,
                      low_confidence=result.confidence < low_conf, cleaning_activated=result.cleaning_activated,
                      pump_duration_ms=result.pump_duration_ms, pump_reason=result.reason, dirt_level=result.dirt_level,
                      model_version=result.model_version, inference_ms=result.inference_ms, round_trip_ms=round_trip_ms)
    rel = store.save(norm.jpeg)
    try:
        row = repo.add(image_path=rel, original_filename=(filename or "foto")[:255], engine=engine,
                       width=norm.width, height=norm.height, **fields)
    except Exception:
        store.delete(rel)                                       # sem arquivo órfão
        raise
    return row
