"""Filtro de busca de análises e interpretador de português simples (plano B sem IA).

A IA (Gemini) só TRADUZ a frase do usuário para este filtro; quem busca é o banco. Assim ela não inventa análise nem número.
"""
from __future__ import annotations

import re
import unicodedata
from datetime import datetime, timedelta
from typing import Literal
from zoneinfo import ZoneInfo

from pydantic import BaseModel, Field

from app.labels import Label

TZ = ZoneInfo("America/Sao_Paulo")


class SearchFilter(BaseModel):
    labels: list[Label] | None = None
    since: datetime | None = None
    until: datetime | None = None
    needs_review: bool | None = None           # baixa confiança ainda sem revisão
    min_confidence: float | None = Field(default=None, ge=0, le=1)
    max_confidence: float | None = Field(default=None, ge=0, le=1)
    cleaning_activated: bool | None = None    # a bomba foi acionada?
    text: str | None = Field(default=None, max_length=80)    # trecho do nome do arquivo
    engine: Literal["esp32", "server"] | None = None          # quem classificou (filtro da API; o assistente não usa)


def _plain(text: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", text.lower()) if unicodedata.category(c) != "Mn")


def start_of_day(now: datetime) -> datetime:
    return now.astimezone(TZ).replace(hour=0, minute=0, second=0, microsecond=0)


def rule_based_filter(question: str, now: datetime | None = None) -> SearchFilter:
    """Entende o essencial de perguntas em português sem IA: classe, período, revisão, bomba."""
    now = (now or datetime.now(TZ)).astimezone(TZ)
    q = _plain(question)
    f = SearchFilter()
    labels = []
    if re.search(r"\b(limp[oa]s?)\b", q):
        labels.append(Label.LIMPO)
    if re.search(r"\b(moderad[oa]s?|poeira|empoeirad[oa]s?)\b", q):
        labels.append(Label.MODERADO)
    if re.search(r"\b(sever[oa]s?|suj[oa]s?|critic[oa]s?|urgente|pior(es)?)\b", q):
        labels.append(Label.SEVERO)
    f.labels = labels or None

    if re.search(r"\bhoje\b", q):
        f.since = start_of_day(now)
    elif re.search(r"\bontem\b", q):
        f.since, f.until = start_of_day(now) - timedelta(days=1), start_of_day(now)
    elif re.search(r"7\s*dias|\bsemana\b", q):
        f.since = start_of_day(now) - timedelta(days=6)
    elif re.search(r"\bmes\b|30\s*dias", q):
        f.since = start_of_day(now) - timedelta(days=29)

    if re.search(r"revis|duvid|incert|baixa confianca|conferir", q):
        f.needs_review = True
    if re.search(r"bomba|limpeza acionada|acionou|acionad[oa]|lavou|lavagem", q):
        f.cleaning_activated = not re.search(r"\bnao\b|sem ", q)
    return f


def describe_filter(f: SearchFilter) -> str:
    parts = []
    if f.labels:
        parts.append("rótulo " + "/".join(l.value for l in f.labels))
    if f.since:
        parts.append(f"desde {f.since.astimezone(TZ):%d/%m %H:%M}")
    if f.until:
        parts.append(f"até {f.until.astimezone(TZ):%d/%m %H:%M}")
    if f.needs_review:
        parts.append("precisam de revisão")
    if f.min_confidence is not None:
        parts.append(f"confiança ≥ {f.min_confidence:.0%}")
    if f.max_confidence is not None:
        parts.append(f"confiança ≤ {f.max_confidence:.0%}")
    if f.cleaning_activated is not None:
        parts.append("bomba acionada" if f.cleaning_activated else "bomba não acionada")
    if f.text:
        parts.append(f"nome contém “{f.text}”")
    if f.engine:
        parts.append("classificadas no " + ("ESP32" if f.engine == "esp32" else "servidor"))
    return ", ".join(parts) or "todas as análises"
