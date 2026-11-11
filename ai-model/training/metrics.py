"""Métricas de classificação em numpy puro (sem torch, sem sklearn): rodam em qualquer ambiente e nos testes."""
from __future__ import annotations

from typing import Sequence

import numpy as np

from labels import LABELS


def confusion_matrix(y_true: Sequence[int], y_pred: Sequence[int], n: int = len(LABELS)) -> np.ndarray:
    cm = np.zeros((n, n), dtype=int)
    for t, p in zip(y_true, y_pred):
        cm[int(t), int(p)] += 1
    return cm


def per_class(cm: np.ndarray) -> list[dict]:
    out = []
    for i, label in enumerate(LABELS[: cm.shape[0]]):
        tp = int(cm[i, i])
        fp = int(cm[:, i].sum() - tp)
        fn = int(cm[i, :].sum() - tp)
        precision = tp / (tp + fp) if tp + fp else 0.0
        recall = tp / (tp + fn) if tp + fn else 0.0
        f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
        out.append({"classe": label, "precisao": precision, "recall": recall, "f1": f1, "suporte": int(cm[i, :].sum())})
    return out


def summarize(y_true: Sequence[int], y_pred: Sequence[int]) -> dict:
    cm = confusion_matrix(y_true, y_pred)
    classes = per_class(cm)
    total = int(cm.sum())
    return {
        "n": total,
        "acuracia": float(np.trace(cm) / total) if total else 0.0,
        "f1_macro": float(np.mean([c["f1"] for c in classes])) if classes else 0.0,
        "por_classe": classes,
        "matriz_confusao": cm.tolist(),
        "ordem_classes": list(LABELS),
    }


def selective(probs_max: Sequence[float], correct: Sequence[bool], threshold: float) -> dict:
    """Se a rede só responde quando a confiança passa do limiar: quanto ela cobre e quanto acerta nisso."""
    pm, ok = np.asarray(probs_max, dtype=float), np.asarray(correct, dtype=bool)
    covered = pm >= threshold
    n = len(pm)
    return {
        "limiar": threshold,
        "cobertura": float(covered.mean()) if n else 0.0,
        "acuracia_nos_cobertos": float(ok[covered].mean()) if covered.any() else 0.0,
        "enviados_para_revisao": int((~covered).sum()),
    }
