"""Exporta as fotos (já revisadas por pessoas, em geral) para retreinar os modelos.

O zip tem uma pasta por classe (LIMPO/, MODERADO/, SEVERO/) com `<id>.jpg` e um `labels.csv`. Esse formato é o que
`ai-model/training/prepare_data.py --extra <pasta>` já lê. As fotos ficam no tamanho em que foram guardadas
(até UPLOAD_MAX_SIDE px); cada treino as redimensiona para o seu tamanho de entrada. O dataset original NÃO faz parte do zip.

Se o modelo do ESP32 usar só LIMPO e SEVERO, ignore (ou mapeie) a pasta MODERADO ao treinar esse modelo.
"""
from __future__ import annotations

import csv
import io
import zipfile

from app.services.storage import ImageStore

COLUMNS = ["id", "arquivo", "rotulo", "revisada_por_pessoa", "motor", "classificacao_do_motor", "confianca", "modelo", "criada_em"]


def build_training_zip(rows: list[dict], store: ImageStore) -> bytes:
    buf = io.BytesIO()
    table = io.StringIO()
    w = csv.writer(table)
    w.writerow(COLUMNS)
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_STORED) as z:           # JPEG já é comprimido
        for r in rows:
            path = store.resolve(r["image_path"])
            if path is None:
                continue                                                # arquivo sumiu: não quebra a exportação
            name = f"{r['label']}/{r['id']}.jpg"
            z.write(path, name)
            w.writerow([r["id"], name, r["label"], int(r["reviewed"]), r["engine"], r["classification"],
                        f"{r['confidence']:.4f}", r["model_version"] or "", r["created_at"].isoformat() if r["created_at"] else ""])
        z.writestr("labels.csv", table.getvalue())
    return buf.getvalue()
