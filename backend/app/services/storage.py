"""Armazenamento das imagens em arquivos. O banco guarda só o caminho RELATIVO (portável entre máquinas e contêineres)."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from pathlib import Path


class ImageStore:
    def __init__(self, root: str | Path) -> None:
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def save(self, data: bytes, ext: str = ".jpg") -> str:
        now = datetime.now(timezone.utc)
        rel = f"{now:%Y/%m}/{uuid.uuid4().hex}{ext}"
        dest = self.root / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        tmp = dest.with_suffix(dest.suffix + ".part")
        tmp.write_bytes(data)
        tmp.replace(dest)                                   # gravação atômica: nunca fica arquivo pela metade
        return rel

    def resolve(self, rel: str) -> Path | None:
        """Caminho absoluto seguro, ou None se escapar da pasta ou não existir (bloqueia path traversal)."""
        p = (self.root / rel).resolve()
        if self.root not in p.parents or not p.is_file():
            return None
        return p

    def delete(self, rel: str) -> None:
        p = self.resolve(rel)
        if p:
            p.unlink(missing_ok=True)
