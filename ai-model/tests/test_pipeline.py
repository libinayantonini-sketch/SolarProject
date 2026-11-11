"""Testes das partes puras do pipeline de dados (sem TensorFlow)."""
import csv
import subprocess
import sys
from pathlib import Path

import pytest
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "training"))
from labels import parse_class_map, to_label  # noqa: E402
from metrics import summarize  # noqa: E402
import prepare_data  # noqa: E402


def test_class_map():
    m = parse_class_map("Dusty=SEVERO")
    assert to_label("Clean", m) == "LIMPO" and to_label("dusty", m) == "SEVERO"
    with pytest.raises(ValueError):
        to_label("Banana", m)
    with pytest.raises(ValueError):
        parse_class_map("X=OUTRO")


def mk(p: Path, color):
    p.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (16, 16), color).save(p)


def test_folder_and_csv_and_dedupe(tmp_path):
    root = tmp_path / "rf"
    for s, split in enumerate(("train", "valid", "test")):
        for i, cls in enumerate(("Clean", "Dusty", "Soiled")):
            mk(root / split / cls / "a.jpg", (i * 80, 10 + s * 30, i))
    mk(root / "train" / "Clean" / "dup.jpg", (0, 10, 0))                  # duplicata exata do a.jpg de treino
    rows = prepare_data.collect_roboflow(root, parse_class_map(""))
    man = prepare_data.build(rows, 1, False)
    assert len(man) == 9 and {m["split"] for m in man} == {"train", "val", "test"}

    csv_root = tmp_path / "csv"
    mk(csv_root / "train" / "x.jpg", (1, 2, 3))
    mk(csv_root / "train" / "y.jpg", (9, 2, 3))
    with (csv_root / "train" / "_classes.csv").open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["filename", " Clean", " Dusty", " Soiled"])
        w.writerow(["x.jpg", 1, 0, 0])
        w.writerow(["y.jpg", 0, 1, 1])                                    # ambíguo: ignorado
    rows = prepare_data.collect_roboflow(csv_root, parse_class_map(""))
    assert [(p.name, l) for p, l, _ in rows] == [("x.jpg", "LIMPO")]


def test_resplit_is_stratified_and_deterministic(tmp_path):
    items = [(tmp_path / f"{c}{i}.jpg", c) for c in ("LIMPO", "SEVERO") for i in range(20)]
    a, b = prepare_data.stratified_split(items, 7), prepare_data.stratified_split(items, 7)
    assert a == b
    for c in ("LIMPO", "SEVERO"):
        assert sum(v == "test" for p, v in a.items() if p.name.startswith(c)) in (3,)


def test_metrics():
    m = summarize([0, 1, 2, 2], [0, 1, 2, 1])
    assert m["acuracia"] == 0.75 and m["matriz_confusao"][2] == [0, 1, 1]


def test_detection_export_is_rejected(tmp_path):
    (tmp_path / "train" / "images").mkdir(parents=True)
    with pytest.raises(SystemExit):
        prepare_data.collect_roboflow(tmp_path, parse_class_map(""))
