"""Monta data/manifest.csv (caminho,rótulo,partição) a partir do export do Roboflow e das fotos extras da equipe.

Formatos aceitos (exporte do Roboflow como CLASSIFICAÇÃO):
  folder   <raiz>/{train,valid,test}/<Classe>/*.jpg          ("Folder Structure")
  csv      <raiz>/{train,valid,test}/_classes.csv + imagens  ("Multi-label CSV", uma coluna por classe, 1 = pertence)
Formatos de detecção (YOLO/COCO, caixas) NÃO são aceitos: não há rótulo por imagem. O script avisa.

Fotos extras: --extra pasta/ com subpastas LIMPO/ MODERADO/ SEVERO/ (ou os nomes do dataset). Vão para treino/val/teste
por sorteio estratificado, com semente fixa.

Regras de higiene: remove duplicatas exatas (SHA-256) — a mesma foto em partições diferentes vazaria o teste para o treino —,
descarta imagens ilegíveis e imprime a contagem final por partição e classe.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import random
import sys
from collections import Counter
from pathlib import Path

from PIL import Image

from labels import LABELS, parse_class_map, to_label

EXT = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}
SPLITS = {"train": "train", "training": "train", "valid": "val", "val": "val", "validation": "val", "test": "test"}


def images_in(d: Path):
    return sorted(p for p in d.rglob("*") if p.suffix.lower() in EXT)


def collect_roboflow(root: Path, cmap: dict[str, str]) -> list[tuple[Path, str, str | None]]:
    rows: list[tuple[Path, str, str | None]] = []
    for sdir in sorted(p for p in root.iterdir() if p.is_dir() and p.name.lower() in SPLITS):
        split = SPLITS[sdir.name.lower()]
        csv_path = sdir / "_classes.csv"
        if csv_path.is_file():
            with csv_path.open(newline="", encoding="utf-8") as f:
                rd = csv.DictReader(f, skipinitialspace=True)
                cols = [c for c in rd.fieldnames or [] if c.strip().lower() != "filename"]
                for r in rd:
                    marked = [c for c in cols if str(r[c]).strip() == "1"]
                    if len(marked) != 1:
                        continue                                   # sem rótulo ou ambíguo: não adivinhamos
                    rows.append((sdir / r["filename"].strip(), to_label(marked[0], cmap), split))
        else:
            for cdir in sorted(p for p in sdir.iterdir() if p.is_dir()):
                for img in images_in(cdir):
                    rows.append((img, to_label(cdir.name, cmap), split))
    if not rows:
        sys.exit(f"Nada encontrado em {root}. Esperado: train/valid/test com pastas por classe ou _classes.csv.\n"
                 "Se você baixou YOLO/COCO (detecção), exporte de novo como classificação.")
    return rows


def collect_extra(root: Path, cmap: dict[str, str]) -> list[tuple[Path, str, str | None]]:
    rows = []
    for cdir in sorted(p for p in root.iterdir() if p.is_dir()):
        for img in images_in(cdir):
            rows.append((img, to_label(cdir.name, cmap), None))
    return rows


def stratified_split(items: list[tuple[Path, str]], seed: int, frac=(0.7, 0.15, 0.15)) -> dict[Path, str]:
    rng, out = random.Random(seed), {}
    by: dict[str, list[Path]] = {}
    for p, lab in items:
        by.setdefault(lab, []).append(p)
    for lab, ps in by.items():
        ps.sort()
        rng.shuffle(ps)
        n_tr, n_va = round(len(ps) * frac[0]), round(len(ps) * frac[1])
        for i, p in enumerate(ps):
            out[p] = "train" if i < n_tr else "val" if i < n_tr + n_va else "test"
    return out


def build(rows, seed: int, resplit: bool) -> list[dict]:
    seen: dict[str, Path] = {}
    clean: list[tuple[Path, str, str | None]] = []
    dup = bad = 0
    for p, lab, split in rows:
        try:
            with Image.open(p) as im:
                im.verify()
            sha = hashlib.sha256(p.read_bytes()).hexdigest()
        except Exception:
            bad += 1
            continue
        if sha in seen:
            dup += 1
            continue
        seen[sha] = p
        clean.append((p, lab, split))
    print(f"descartadas: {dup} duplicatas exatas, {bad} ilegíveis")
    need = [(p, l) for p, l, s in clean if s is None or resplit]
    assigned = stratified_split(need, seed) if need else {}
    return [{"path": str(p), "label": lab, "split": assigned.get(p, s)} for p, lab, s in clean]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--roboflow", type=Path, help="pasta do export de classificação do Roboflow")
    ap.add_argument("--extra", type=Path, action="append", default=[], help="pasta com fotos extras (subpastas por classe)")
    ap.add_argument("--class-map", default="", help='ex.: "Dusty=SEVERO"')
    ap.add_argument("--resplit", action="store_true", help="ignora as partições do Roboflow e sorteia 70/15/15 estratificado")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--out", type=Path, default=Path("data/manifest.csv"))
    a = ap.parse_args()
    if not a.roboflow and not a.extra:
        ap.error("informe --roboflow e/ou --extra")
    cmap = parse_class_map(a.class_map)
    rows = []
    if a.roboflow:
        rows += collect_roboflow(a.roboflow, cmap)
    for e in a.extra:
        rows += collect_extra(e, cmap)
    man = build(rows, a.seed, a.resplit)
    a.out.parent.mkdir(parents=True, exist_ok=True)
    with a.out.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, ["path", "label", "split"])
        w.writeheader()
        w.writerows(man)
    cnt = Counter((m["split"], m["label"]) for m in man)
    print(f"{len(man)} imagens -> {a.out}")
    for split in ("train", "val", "test"):
        print(f"  {split:5s}", {l: cnt.get((split, l), 0) for l in LABELS})
    for l in LABELS:
        if not any(m["label"] == l for m in man):
            print(f"AVISO: nenhuma imagem da classe {l}")


if __name__ == "__main__":
    main()
