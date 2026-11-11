"""Modelo ONNX minúsculo SÓ PARA TESTES. Não é um classificador de painéis.

Calcula a média de cada canal de cor e a transforma em 3 logits: canal R -> LIMPO, G -> MODERADO, B -> SEVERO.
Serve para testar o caminho completo (upload -> inferência -> banco -> API -> front) sem treinar nada.
Nunca use fora de testes; o front mostra a versão "teste-sintetico" para ninguém confundir.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import onnx
from onnx import TensorProto, helper, numpy_helper

LABELS = ("LIMPO", "MODERADO", "SEVERO")


def build_tiny_model(dir_: str | Path, version: str = "teste-sintetico", size: int = 32, threshold: float = 0.6) -> Path:
    d = Path(dir_)
    d.mkdir(parents=True, exist_ok=True)
    w = numpy_helper.from_array((np.eye(3, dtype=np.float32) * 8.0), name="W")
    b = numpy_helper.from_array(np.zeros(3, dtype=np.float32), name="B")
    nodes = [
        helper.make_node("GlobalAveragePool", ["input"], ["pooled"]),
        helper.make_node("Flatten", ["pooled"], ["flat"], axis=1),
        helper.make_node("Gemm", ["flat", "W", "B"], ["logits"]),
    ]
    graph = helper.make_graph(
        nodes, "tiny",
        [helper.make_tensor_value_info("input", TensorProto.FLOAT, ["batch", 3, size, size])],
        [helper.make_tensor_value_info("logits", TensorProto.FLOAT, ["batch", 3])],
        initializer=[w, b],
    )
    model = helper.make_model(graph, opset_imports=[helper.make_opsetid("", 17)])
    model.ir_version = 9
    onnx.checker.check_model(model)
    onnx.save(model, d / "model.onnx")
    (d / "labels.json").write_text(json.dumps(list(LABELS)), encoding="utf-8")
    (d / "model_card.json").write_text(json.dumps({
        "version": version, "arch": "tiny-test", "input_size": size,
        "mean": [0.0, 0.0, 0.0], "std": [1.0, 1.0, 1.0], "low_confidence_threshold": threshold,
    }), encoding="utf-8")
    return d
