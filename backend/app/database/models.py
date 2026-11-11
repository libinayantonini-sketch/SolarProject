"""Tabela `analyses` (docs/03_BANCO_DE_DADOS.md). SQLite nos testes, PostgreSQL em uso real.

A imagem NÃO fica no banco: fica em arquivo (STORAGE_DIR) e a coluna image_path guarda o caminho relativo.
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import JSON, Boolean, DateTime, Float, Integer, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class Analysis(Base):
    __tablename__ = "analyses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    image_path: Mapped[str] = mapped_column(String(300))                      # relativo a STORAGE_DIR
    original_filename: Mapped[str] = mapped_column(String(255), default="")
    classification: Mapped[str] = mapped_column(String(10), index=True)       # LIMPO | MODERADO | SEVERO (o que o motor disse)
    confidence: Mapped[float] = mapped_column(Float)                          # 0..1; NÃO é percentual de sujeira
    probs: Mapped[dict | None] = mapped_column(JSON)
    low_confidence: Mapped[bool] = mapped_column(Boolean, default=False)
    cleaning_activated: Mapped[bool] = mapped_column(Boolean, default=False)
    pump_duration_ms: Mapped[int] = mapped_column(Integer, default=0)
    pump_reason: Mapped[str | None] = mapped_column(String(200))              # por que acionou ou não (vem do firmware)
    dirt_level: Mapped[float | None] = mapped_column(Float)                   # só se o modelo medir de verdade; nosso modelo não mede => NULL
    engine: Mapped[str] = mapped_column(String(10), default="esp32", server_default="esp32", index=True)   # quem classificou: esp32 | server
    model_version: Mapped[str | None] = mapped_column(String(80))
    inference_ms: Mapped[int | None] = mapped_column(Integer)
    round_trip_ms: Mapped[int | None] = mapped_column(Integer)                # tempo total backend <-> ESP32
    width: Mapped[int] = mapped_column(Integer)
    height: Mapped[int] = mapped_column(Integer)
    human_label: Mapped[str | None] = mapped_column(String(10))               # correção do operador; guardada à parte
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
