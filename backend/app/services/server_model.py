"""Modelo grande opcional (ex.: ResNet) rodando NO SERVIDOR com ONNX Runtime (sem PyTorch/TensorFlow).

Serve para análise mais robusta e para o time treinar/trocar o modelo sem mexer no firmware. Ele NUNCA aciona a bomba:
só o firmware do ESP32 decide isso.

Contrato do modelo (docs/12_MODELO_NO_SERVIDOR.md): uma pasta (SERVER_MODEL_DIR) com
    model.onnx        entrada (N,3,H,W) float32 NCHW; saída (N,K) com logits (ou probabilidades se o card disser "output":"probs")
    labels.json       as classes na ordem das saídas, ex.: ["LIMPO","MODERADO","SEVERO"] (o número de classes vem daqui)
    model_card.json   version, input_size, mean, std, output (opcional)
O lado da entrada pode ser trocado sem editar código: SERVER_INPUT_SIZE (ou "input_size" no card).
O pré-processamento vem do card para treino e inferência não divergirem.
"""
from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from PIL import Image

from app.labels import Label, UnknownClassError, parse_classes

DEFAULT_MEAN = (0.485, 0.456, 0.406)       # ImageNet
DEFAULT_STD = (0.229, 0.224, 0.225)
DEFAULT_SIZE = 224


class ServerModelUnavailable(RuntimeError):
    status = 503


@dataclass(frozen=True)
class ServerPrediction:
    label: Label
    confidence: float
    probs: dict[str, float]
    latency_ms: float
    model_version: str


def softmax(x: np.ndarray) -> np.ndarray:
    z = x - x.max(axis=-1, keepdims=True)
    e = np.exp(z)
    return e / e.sum(axis=-1, keepdims=True)


class ServerModel:
    def __init__(self, session, card: dict, labels: tuple[Label, ...], input_size: int = 0) -> None:
        self.session, self.card, self.labels = session, card, labels
        self.version = str(card.get("version", "desconhecida"))
        self.size = int(input_size or card.get("input_size") or DEFAULT_SIZE)
        self.mean = np.asarray(card.get("mean", DEFAULT_MEAN), dtype=np.float32)
        self.std = np.asarray(card.get("std", DEFAULT_STD), dtype=np.float32)
        self.outputs_probs = card.get("output") == "probs"
        self.input_name = session.get_inputs()[0].name

    @classmethod
    def load(cls, model_dir: str | Path, input_size: int = 0) -> "ServerModel":
        d = Path(model_dir)
        missing = [n for n in ("model.onnx", "labels.json", "model_card.json") if not (d / n).is_file()]
        if missing:
            raise ServerModelUnavailable(f"faltam em {d}: {', '.join(missing)}")
        try:
            import onnxruntime as ort
        except ImportError as exc:
            raise ServerModelUnavailable("onnxruntime não está instalado (pip install onnxruntime)") from exc
        try:
            labels = parse_classes(json.loads((d / "labels.json").read_text(encoding="utf-8")))
            card = json.loads((d / "model_card.json").read_text(encoding="utf-8"))
        except (UnknownClassError, ValueError, TypeError) as exc:
            raise ServerModelUnavailable(f"labels.json ou model_card.json inválido: {exc}") from exc
        try:
            session = ort.InferenceSession(str(d / "model.onnx"), providers=["CPUExecutionProvider"])
        except Exception as exc:
            raise ServerModelUnavailable(f"não consegui abrir o ONNX: {type(exc).__name__}: {exc}") from exc
        out_dim = session.get_outputs()[0].shape[-1]
        if isinstance(out_dim, int) and out_dim != len(labels):
            raise ServerModelUnavailable(f"o modelo tem {out_dim} saídas mas labels.json tem {len(labels)} classes")
        return cls(session, card, labels, input_size)

    def predict(self, img: Image.Image) -> ServerPrediction:
        t0 = time.perf_counter()
        arr = np.asarray(img.convert("RGB").resize((self.size, self.size), Image.BILINEAR), dtype=np.float32) / 255.0
        x = ((arr - self.mean) / self.std).transpose(2, 0, 1)[None].astype(np.float32)
        out = np.asarray(self.session.run(None, {self.input_name: x})[0], dtype=np.float32)
        p = (out if self.outputs_probs else softmax(out))[0]
        i = int(p.argmax())
        return ServerPrediction(self.labels[i], float(p[i]), {l.value: float(p[k]) for k, l in enumerate(self.labels)},
                                (time.perf_counter() - t0) * 1000, self.version)

    def info(self) -> dict:
        return {"version": self.version, "input_size": self.size, "classes": [l.value for l in self.labels]}


def try_load(model_dir: str, input_size: int = 0) -> tuple[ServerModel | None, str | None]:
    """Carrega se existir; devolve (modelo, motivo_da_indisponibilidade). Nunca levanta: o servidor sobe sem o modelo grande."""
    try:
        return ServerModel.load(model_dir, input_size), None
    except ServerModelUnavailable as exc:
        return None, str(exc)
