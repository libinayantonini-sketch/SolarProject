"""Acesso ao banco. A API não escreve SQL; tudo passa por aqui. Datas em UTC."""
from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from sqlalchemy import and_, create_engine, func, inspect, select, text
from sqlalchemy.schema import CreateColumn
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.database.models import Analysis, Base, utcnow
from app.labels import LABELS, Label
from app.services.assistant.search import SearchFilter

LOCAL_TZ = ZoneInfo("America/Sao_Paulo")


def normalize_url(url: str) -> str:
    if url.startswith("postgres://"):
        url = "postgresql://" + url[len("postgres://"):]
    if url.startswith("postgresql://"):
        url = "postgresql+psycopg://" + url[len("postgresql://"):]
    return url


def to_utc(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt.astimezone(timezone.utc)


def to_dict(a: Analysis) -> dict:
    label = a.human_label or a.classification
    return {
        "id": a.id, "image_url": f"/api/analyses/{a.id}/image", "original_filename": a.original_filename,
        "classification": a.classification, "final_label": label, "human_label": a.human_label,
        "confidence": a.confidence, "probs": a.probs, "low_confidence": a.low_confidence,
        "needs_review": bool(a.low_confidence) and a.human_label is None,
        "engine": a.engine or "esp32",
        "cleaning_activated": a.cleaning_activated, "pump_duration_ms": a.pump_duration_ms, "pump_reason": a.pump_reason,
        "dirt_level": a.dirt_level, "model_version": a.model_version, "inference_ms": a.inference_ms,
        "round_trip_ms": a.round_trip_ms, "width": a.width, "height": a.height,
        "reviewed_at": to_utc(a.reviewed_at), "created_at": to_utc(a.created_at),
    }


class Repository:
    def __init__(self, url: str = "sqlite:///./data/app.db") -> None:
        url = normalize_url(url)
        self.url = url
        if url.startswith("sqlite:///") and ":memory:" not in url:
            Path(url[len("sqlite:///"):]).parent.mkdir(parents=True, exist_ok=True)   # ./data/ pode não existir ainda
        if url.startswith("sqlite"):
            kw: dict = {"connect_args": {"check_same_thread": False}}
            if ":memory:" in url or url in ("sqlite://", "sqlite:///"):
                kw["poolclass"] = StaticPool
            self.engine: Engine = create_engine(url, **kw)
        else:
            self.engine = create_engine(url, pool_pre_ping=True, pool_size=5, max_overflow=5)
        self._Session = sessionmaker(self.engine, expire_on_commit=False)

    def create_schema(self) -> None:
        Base.metadata.create_all(self.engine)
        self._add_missing_columns()

    def _add_missing_columns(self) -> None:
        """Migração leve: bancos criados por versões antigas ganham as colunas novas (todas opcionais ou com padrão).
        Não remove nem altera nada existente. Para mudanças maiores, adote Alembic (docs/03_BANCO_DE_DADOS.md)."""
        insp = inspect(self.engine)
        with self.engine.begin() as conn:
            for table in Base.metadata.sorted_tables:
                if not insp.has_table(table.name):
                    continue
                have = {c["name"] for c in insp.get_columns(table.name)}
                for col in table.columns:
                    if col.name in have:
                        continue
                    if not col.nullable and col.server_default is None:
                        raise RuntimeError(f"coluna nova obrigatória sem padrão: {table.name}.{col.name}; use uma migração")
                    ddl = CreateColumn(col).compile(dialect=self.engine.dialect)
                    conn.execute(text(f"ALTER TABLE {table.name} ADD COLUMN {ddl}"))

    def reset_schema(self) -> None:
        Base.metadata.drop_all(self.engine)
        Base.metadata.create_all(self.engine)

    def dispose(self) -> None:
        self.engine.dispose()

    def ping(self) -> bool:
        with self.engine.connect() as c:
            c.execute(text("SELECT 1"))
        return True

    def session(self) -> Session:
        return self._Session()

    # ---------- escrita ----------
    def add(self, **fields) -> dict:
        with self.session() as s:
            a = Analysis(**fields)
            s.add(a)
            s.commit()
            return to_dict(a)

    def relabel(self, analysis_id: int, label: Label | None, now: datetime | None = None) -> dict | None:
        with self.session() as s:
            a = s.get(Analysis, analysis_id)
            if a is None:
                return None
            a.human_label = label.value if label else None
            a.reviewed_at = to_utc(now or utcnow()) if label else None
            s.commit()
            return to_dict(a)

    def delete(self, analysis_id: int) -> str | None:
        """Apaga a linha e devolve o image_path para o chamador remover o arquivo."""
        with self.session() as s:
            a = s.get(Analysis, analysis_id)
            if a is None:
                return None
            path = a.image_path
            s.delete(a)
            s.commit()
            return path

    def export_rows(self, only_reviewed: bool = True) -> list[dict]:
        """Linhas para montar o conjunto de retreino (foto + rótulo final), de qualquer motor."""
        with self.session() as s:
            q = select(Analysis).order_by(Analysis.id)
            if only_reviewed:
                q = q.where(Analysis.human_label.is_not(None))
            return [{"id": a.id, "image_path": a.image_path, "label": a.human_label or a.classification,
                     "reviewed": a.human_label is not None, "engine": a.engine or "esp32",
                     "classification": a.classification, "confidence": a.confidence, "model_version": a.model_version,
                     "created_at": to_utc(a.created_at)} for a in s.scalars(q)]

    # ---------- leitura ----------
    def get(self, analysis_id: int) -> dict | None:
        with self.session() as s:
            a = s.get(Analysis, analysis_id)
            return to_dict(a) if a else None

    def image_path(self, analysis_id: int) -> str | None:
        with self.session() as s:
            return s.scalar(select(Analysis.image_path).where(Analysis.id == analysis_id))

    @staticmethod
    def _apply(stmt, f: SearchFilter):
        label = func.coalesce(Analysis.human_label, Analysis.classification)
        if f.labels:
            stmt = stmt.where(label.in_([l.value for l in f.labels]))
        if f.since:
            stmt = stmt.where(Analysis.created_at >= to_utc(f.since))
        if f.until:
            stmt = stmt.where(Analysis.created_at < to_utc(f.until))
        if f.needs_review:
            stmt = stmt.where(and_(Analysis.low_confidence.is_(True), Analysis.human_label.is_(None)))
        if f.engine:
            stmt = stmt.where(Analysis.engine == f.engine)
        if f.min_confidence is not None:
            stmt = stmt.where(Analysis.confidence >= f.min_confidence)
        if f.max_confidence is not None:
            stmt = stmt.where(Analysis.confidence <= f.max_confidence)
        if f.cleaning_activated is not None:
            stmt = stmt.where(Analysis.cleaning_activated.is_(f.cleaning_activated))
        if f.text:
            stmt = stmt.where(Analysis.original_filename.ilike(f"%{f.text}%"))
        return stmt

    def list(self, f: SearchFilter | None = None, limit: int = 24, offset: int = 0) -> tuple[int, list[dict]]:
        f = f or SearchFilter()
        limit = max(1, min(limit, 200))
        with self.session() as s:
            base = self._apply(select(Analysis), f)
            total = s.scalar(select(func.count()).select_from(base.order_by(None).subquery())) or 0
            rows = s.scalars(base.order_by(Analysis.created_at.desc(), Analysis.id.desc()).limit(limit).offset(max(0, offset))).all()
            return int(total), [to_dict(a) for a in rows]

    def stats(self, now: datetime | None = None, days: int = 14) -> dict:
        now = to_utc(now or utcnow())
        label = func.coalesce(Analysis.human_label, Analysis.classification)
        with self.session() as s:
            by = {l.value: 0 for l in LABELS}
            for lab, n in s.execute(select(label, func.count()).group_by(label)):
                if lab in by:
                    by[lab] = int(n)
            total = int(s.scalar(select(func.count()).select_from(Analysis)) or 0)
            review = int(s.scalar(select(func.count()).select_from(Analysis).where(
                and_(Analysis.low_confidence.is_(True), Analysis.human_label.is_(None)))) or 0)
            by_engine = {k: int(n) for k, n in s.execute(select(Analysis.engine, func.count()).group_by(Analysis.engine))}
            reviewed = int(s.scalar(select(func.count()).select_from(Analysis).where(Analysis.human_label.is_not(None))) or 0)
            cleanings = int(s.scalar(select(func.count()).select_from(Analysis).where(Analysis.cleaning_activated.is_(True))) or 0)
            pump_ms = int(s.scalar(select(func.coalesce(func.sum(Analysis.pump_duration_ms), 0))) or 0)
            avg_conf = s.scalar(select(func.avg(Analysis.confidence)))
            avg_inf = s.scalar(select(func.avg(Analysis.inference_ms)))
            last = to_utc(s.scalar(select(func.max(Analysis.created_at))))
            rows = s.execute(select(Analysis.created_at, label).where(Analysis.created_at >= now - timedelta(days=days))).all()
        daily: dict[str, Counter] = defaultdict(Counter)
        for created, lab in rows:
            daily[to_utc(created).astimezone(LOCAL_TZ).date().isoformat()][lab] += 1
        today = now.astimezone(LOCAL_TZ).date()
        series = []
        for i in range(days - 1, -1, -1):
            d = (today - timedelta(days=i)).isoformat()
            c = daily.get(d, Counter())
            series.append({"dia": d, **{l.value: int(c.get(l.value, 0)) for l in LABELS}})
        return {
            "total": total, "por_rotulo": by, "para_revisao": review, "revisadas": reviewed,
            "por_motor": {"esp32": by_engine.get("esp32", 0), "server": by_engine.get("server", 0)},
            "limpezas_acionadas": cleanings, "tempo_total_bomba_ms": pump_ms,
            "confianca_media": float(avg_conf) if avg_conf is not None else None,
            "inferencia_media_ms": float(avg_inf) if avg_inf is not None else None,
            "ultima_analise": last, "serie_diaria": series,
        }
