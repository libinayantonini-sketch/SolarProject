"""Motor TFLite int8 do simulador: quantiza e desquantiza como o firmware faz, para que o simulador se comporte
como o dispositivo real (a menos de diferenças de arredondamento entre as bibliotecas).

Usa `ai_edge_litert` ou `tflite_runtime` se existirem (leves); senão `tensorflow.lite`.
"""
from __future__ import annotations

import json
import time
from pathlib import Path

import numpy as np
from PIL import Image

from esp32_simulator.classifier import LABELS, Prediction


def _interpreter(path: str):
    for mod, attr in (("ai_edge_litert.interpreter", "Interpreter"), ("tflite_runtime.interpreter", "Interpreter")):
        try:
            return getattr(__import__(mod, fromlist=[attr]), attr)(model_path=path)
        except ImportError:
            continue
    import tensorflow as tf
    return tf.lite.Interpreter(model_path=path)


class TFLiteEngine:
    def __init__(self, interp, card: dict) -> None:
        self.it = interp
        self.it.allocate_tensors()
        self.i = self.it.get_input_details()[0]
        self.o = self.it.get_output_details()[0]
        self.card = card
        self.version = str(card.get("version", "desconhecida"))
        self.size = int(card.get("input_size", self.i["shape"][1]))
        self.threshold = float(card.get("low_confidence_threshold", 0.6))

    @classmethod
    def load(cls, model_dir: str | Path) -> "TFLiteEngine":
        d = Path(model_dir)
        labels = json.loads((d / "labels.json").read_text(encoding="utf-8"))
        if labels != list(LABELS):
            raise ValueError(f"labels.json {labels} difere de {list(LABELS)}")
        card = json.loads((d / "model_card.json").read_text(encoding="utf-8"))
        return cls(_interpreter(str(d / "model.tflite")), card)

    def predict_image(self, img: Image.Image) -> Prediction:
        t0 = time.perf_counter()
        rgb = np.asarray(img.convert("RGB").resize((self.size, self.size), Image.BILINEAR), dtype=np.float32)
        si, zi = self.i["quantization"]
        q = np.clip(np.round(rgb / si + zi), -128, 127).astype(np.int8)[None]
        self.it.set_tensor(self.i["index"], q)
        self.it.invoke()
        so, zo = self.o["quantization"]
        p = (self.it.get_tensor(self.o["index"])[0].astype(np.float32) - zo) * so
        idx = int(p.argmax())
        return Prediction(label=LABELS[idx], confidence=float(p[idx]), probs={l: float(p[i]) for i, l in enumerate(LABELS)},
                          low_confidence=float(p[idx]) < self.threshold, latency_ms=(time.perf_counter() - t0) * 1000,
                          model_version=self.version)
