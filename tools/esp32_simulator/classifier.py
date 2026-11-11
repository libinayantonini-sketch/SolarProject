"""Inferência com ONNX Runtime: leve, sem PyTorch, roda no contêiner da API.

Um "modelo" é uma pasta (padrão models/current/) com três arquivos gerados pelo treino:
    model.onnx        entrada "input" (N,3,H,W) float32; saída "logits" (N,3)
    labels.json       ["LIMPO","MODERADO","SEVERO"], na ordem das saídas
    model_card.json   versão, arquitetura, tamanho de entrada, média/desvio, métricas, limiar de confiança

O pré-processamento lê tudo do model_card.json, para treino e inferência nunca divergirem.
"""
from __future__ import annotations

import json
import time
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path

import numpy as np
from PIL import Image, ImageOps

LABELS = ("LIMPO", "MODERADO", "SEVERO")      # ordem das saídas do modelo (igual a backend/app/labels.py)

DEFAULT_MEAN = (0.485, 0.456, 0.406)
DEFAULT_STD = (0.229, 0.224, 0.225)
DEFAULT_THRESHOLD = 0.60
MAX_PIXELS = 50_000_000          # recusa imagens gigantes (bomba de descompressão)


class ModelNotLoaded(RuntimeError):
    """Não há modelo em MODEL_DIR. Treine (docs/02_DATASET_E_TREINO.md) ou copie os três arquivos."""


class InvalidImage(ValueError):
    pass


@dataclass(frozen=True)
class Prediction:
    label: str
    confidence: float
    probs: dict[str, float]
    low_confidence: bool
    latency_ms: float
    model_version: str


def open_image(data: bytes) -> Image.Image:
    """Abre e valida bytes de imagem. Corrige a orientação do EXIF (fotos de celular) e converte para RGB."""
    Image.MAX_IMAGE_PIXELS = MAX_PIXELS
    try:
        probe = Image.open(BytesIO(data))
        probe.verify()                                  # detecta arquivo truncado/corrompido
        img = Image.open(BytesIO(data))
        if img.width * img.height > MAX_PIXELS:
            raise InvalidImage("imagem grande demais")
        img = ImageOps.exif_transpose(img)
        return img.convert("RGB")
    except InvalidImage:
        raise
    except Exception as exc:                            # PIL levanta vários tipos
        raise InvalidImage(f"arquivo não é uma imagem válida ({type(exc).__name__})") from exc


def preprocess(img: Image.Image, size: int, mean=DEFAULT_MEAN, std=DEFAULT_STD) -> np.ndarray:
    """Igual ao eval do treino: Resize((size,size)) bilinear, escala 0-1, normaliza, NCHW."""
    arr = np.asarray(img.convert("RGB").resize((size, size), Image.BILINEAR), dtype=np.float32) / 255.0
    arr = (arr - np.asarray(mean, dtype=np.float32)) / np.asarray(std, dtype=np.float32)
    return arr.transpose(2, 0, 1)[None].astype(np.float32)


def softmax(logits: np.ndarray) -> np.ndarray:
    z = logits - logits.max(axis=-1, keepdims=True)
    e = np.exp(z)
    return e / e.sum(axis=-1, keepdims=True)


class Classifier:
    def __init__(self, session, card: dict, model_dir: str = "") -> None:
        self.session = session
        self.card = card
        self.model_dir = model_dir
        self.version: str = str(card.get("version", "desconhecida"))
        self.size: int = int(card.get("input_size", 224))
        self.mean = tuple(card.get("mean", DEFAULT_MEAN))
        self.std = tuple(card.get("std", DEFAULT_STD))
        self.threshold: float = float(card.get("low_confidence_threshold", DEFAULT_THRESHOLD))
        self.input_name = session.get_inputs()[0].name

    @classmethod
    def load(cls, model_dir: str | Path) -> "Classifier":
        import onnxruntime as ort

        d = Path(model_dir)
        onnx_path, card_path, labels_path = d / "model.onnx", d / "model_card.json", d / "labels.json"
        missing = [p.name for p in (onnx_path, card_path, labels_path) if not p.is_file()]
        if missing:
            raise ModelNotLoaded(f"faltam em {d}: {', '.join(missing)}")
        labels = json.loads(labels_path.read_text(encoding="utf-8"))
        if labels != list(LABELS):
            raise ValueError(f"labels.json {labels} difere da ordem esperada {list(LABELS)}")
        card = json.loads(card_path.read_text(encoding="utf-8"))
        session = ort.InferenceSession(str(onnx_path), providers=["CPUExecutionProvider"])
        out_dim = session.get_outputs()[0].shape[-1]
        if out_dim != len(LABELS):
            raise ValueError(f"o modelo tem {out_dim} saídas; esperado {len(LABELS)} (LIMPO, MODERADO, SEVERO)")
        return cls(session, card, str(d))

    def predict_image(self, img: Image.Image) -> Prediction:
        t0 = time.perf_counter()
        x = preprocess(img, self.size, self.mean, self.std)
        logits = self.session.run(None, {self.input_name: x})[0]
        p = softmax(logits)[0]
        idx = int(p.argmax())
        conf = float(p[idx])
        return Prediction(
            label=LABELS[idx],
            confidence=conf,
            probs={l: float(p[i]) for i, l in enumerate(LABELS)},
            low_confidence=conf < self.threshold,
            latency_ms=(time.perf_counter() - t0) * 1000,
            model_version=self.version,
        )

    def predict_bytes(self, data: bytes) -> Prediction:
        return self.predict_image(open_image(data))
