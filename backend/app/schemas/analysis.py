"""Contratos de entrada/saída. O formato da resposta do ESP32 é o contrato central (docs/05_PROTOCOLO_ESP32.md)."""
from __future__ import annotations

from pydantic import BaseModel, Field

from app.labels import Label


class Esp32Result(BaseModel):
    """Resposta de POST /upload do ESP32. Qualquer coisa fora disto é tratada como falha do dispositivo."""
    classification: Label
    confidence: float = Field(ge=0, le=1)
    probs: dict[str, float] | None = None
    cleaning_activated: bool = False
    pump_duration_ms: int = Field(default=0, ge=0, le=60_000)     # teto de segurança também no servidor
    reason: str | None = Field(default=None, max_length=200)
    inference_ms: int | None = Field(default=None, ge=0)
    model_version: str | None = Field(default=None, max_length=80)
    dirt_level: float | None = None                                # só se o modelo realmente medir (o nosso não mede)


class RelabelIn(BaseModel):
    label: Label | None = None                                     # null remove a correção humana


class AskIn(BaseModel):
    question: str = Field(min_length=2, max_length=300)
