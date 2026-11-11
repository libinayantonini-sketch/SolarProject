"""Treina o classificador (Keras), avalia no teste e exporta TFLite int8 para o ESP32.

    python training/train.py --manifest data/manifest.csv --size 96 --epochs 40 --out models/run1
    cp -r models/run1 models/current        # a pasta "current" é o que o simulador e o firmware usam

Decisões (todas ligadas ao ESP32 esp32dev, SEM PSRAM, ~320 KB de RAM utilizável):
- rede pequena (depthwise-separable, ~25 mil parâmetros), entrada 96x96: cabe em ~100 KB de modelo int8;
- normalização DENTRO do modelo (Rescaling): o firmware só entrega pixels RGB 0-255 e quantiza com a escala do tensor;
- as imagens de treino passam por redimensionamento + JPEG na mesma qualidade do backend, para não haver surpresa na implantação;
- seleção do melhor modelo por F1 macro na validação; o teste só é lido no fim.
Nenhum número de acurácia é prometido aqui: ele sai de metrics.json depois do treino com os SEUS dados.
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
import shutil
from io import BytesIO
from pathlib import Path

import numpy as np
from PIL import Image

from labels import LABELS
from metrics import selective, summarize

SEED = 42


# ---------------------------------------------------------------- dados
def load_split(manifest: Path, split: str, size: int, jpeg_quality: int) -> tuple[np.ndarray, np.ndarray]:
    xs, ys = [], []
    with manifest.open(encoding="utf-8") as f:
        for r in csv.DictReader(f):
            if r["split"] != split:
                continue
            img = Image.open(r["path"]).convert("RGB").resize((size, size), Image.BILINEAR)
            buf = BytesIO()
            img.save(buf, "JPEG", quality=jpeg_quality)             # mesmo caminho do backend: JPEG size x size
            xs.append(np.asarray(Image.open(BytesIO(buf.getvalue())).convert("RGB"), dtype=np.uint8))
            ys.append(LABELS.index(r["label"]))
    if not xs:
        raise SystemExit(f"partição '{split}' vazia em {manifest}. Rode prepare_data.py (use --resplit se preciso).")
    return np.stack(xs), np.asarray(ys, dtype=np.int64)


# ---------------------------------------------------------------- modelo
def build_model(size: int, arch: str = "tiny_cnn"):
    import keras
    from keras import layers

    inp = keras.Input((size, size, 3), name="input")                 # RGB 0..255
    x = layers.Rescaling(1 / 127.5, offset=-1.0)(inp)                 # -> [-1, 1]
    if arch == "tiny_cnn":
        x = layers.Conv2D(8, 3, strides=2, padding="same", use_bias=False)(x)
        x = layers.BatchNormalization(momentum=0.9)(x); x = layers.ReLU(6.0)(x)
        for filters, stride in [(16, 2), (24, 2), (32, 2), (48, 1), (64, 2)]:
            x = layers.DepthwiseConv2D(3, strides=stride, padding="same", use_bias=False)(x)
            x = layers.BatchNormalization(momentum=0.9)(x); x = layers.ReLU(6.0)(x)
            x = layers.Conv2D(filters, 1, use_bias=False)(x)
            x = layers.BatchNormalization(momentum=0.9)(x); x = layers.ReLU(6.0)(x)
        x = layers.GlobalAveragePooling2D()(x)
    else:
        raise SystemExit(f"arquitetura desconhecida: {arch}. Disponível: tiny_cnn")
    x = layers.Dropout(0.2)(x)
    out = layers.Dense(len(LABELS), activation="softmax", name="probs")(x)
    return keras.Model(inp, out, name=arch)


def augmenter():
    import keras
    from keras import layers
    return keras.Sequential([
        layers.RandomFlip("horizontal_and_vertical"),
        layers.RandomRotation(0.04, fill_mode="reflect"),
        layers.RandomTranslation(0.05, 0.05, fill_mode="reflect"),
        layers.RandomBrightness(0.2, value_range=(0, 255)),
        layers.RandomContrast(0.2),
    ], name="aug")


def class_weights(y: np.ndarray) -> dict[int, float]:
    n = np.bincount(y, minlength=len(LABELS)).astype(float)
    n[n == 0] = 1
    return {i: float(len(y) / (len(LABELS) * n[i])) for i in range(len(LABELS))}


class BestF1:
    """Guarda os melhores pesos pelo F1 macro na validação."""
    def __init__(self, model, xv, yv, patience: int):
        import keras
        self.cb = keras.callbacks.LambdaCallback(on_epoch_end=self.on_epoch_end)
        self.model, self.xv, self.yv, self.patience = model, xv, yv, patience
        self.best, self.best_w, self.wait, self.history = -1.0, None, 0, []

    def on_epoch_end(self, epoch, logs=None):
        p = self.model.predict(self.xv.astype("float32"), verbose=0).argmax(1)
        f1 = summarize(self.yv, p)["f1_macro"]
        self.history.append({"epoca": epoch + 1, "val_f1_macro": f1, "loss": float(logs["loss"])})
        print(f"  época {epoch + 1}: val F1 macro = {f1:.3f}")
        if f1 > self.best:
            self.best, self.best_w, self.wait = f1, self.model.get_weights(), 0
        else:
            self.wait += 1
            if self.wait >= self.patience:
                self.model.stop_training = True


# ---------------------------------------------------------------- exportação
def to_tflite_int8(model, x_rep: np.ndarray) -> bytes:
    import tensorflow as tf
    conv = tf.lite.TFLiteConverter.from_keras_model(model)
    conv.optimizations = [tf.lite.Optimize.DEFAULT]
    rep = x_rep[np.random.default_rng(SEED).permutation(len(x_rep))[:200]].astype("float32")
    conv.representative_dataset = lambda: ([r[None]] for r in rep)
    conv.target_spec.supported_ops = [tf.lite.OpsSet.TFLITE_BUILTINS_INT8]
    conv.inference_input_type = tf.int8
    conv.inference_output_type = tf.int8
    return conv.convert()


def tflite_info(blob: bytes) -> dict:
    import tensorflow as tf
    it = tf.lite.Interpreter(model_content=blob)
    it.allocate_tensors()
    i, o = it.get_input_details()[0], it.get_output_details()[0]
    try:
        ops = sorted({d["op_name"] for d in it._get_ops_details()} - {"DELEGATE"})      # API interna; só informativa
    except Exception:
        ops = []
    return {"input": {"shape": [int(v) for v in i["shape"]], "dtype": "int8", "scale": float(i["quantization"][0]), "zero_point": int(i["quantization"][1])},
            "output": {"shape": [int(v) for v in o["shape"]], "dtype": "int8", "scale": float(o["quantization"][0]), "zero_point": int(o["quantization"][1])},
            "ops": ops}


def tflite_predict(blob: bytes, x: np.ndarray) -> np.ndarray:
    """Roda o TFLite int8 exatamente como o firmware: quantiza a entrada, lê a saída e desquantiza."""
    import tensorflow as tf
    it = tf.lite.Interpreter(model_content=blob)
    it.allocate_tensors()
    i, o = it.get_input_details()[0], it.get_output_details()[0]
    si, zi = i["quantization"]
    so, zo = o["quantization"]
    out = []
    for img in x:
        q = np.clip(np.round(img.astype("float32") / si + zi), -128, 127).astype(np.int8)[None]
        it.set_tensor(i["index"], q)
        it.invoke()
        out.append((it.get_tensor(o["index"])[0].astype("float32") - zo) * so)
    return np.asarray(out)


def evaluate(probs: np.ndarray, y: np.ndarray, threshold: float) -> dict:
    pred = probs.argmax(1)
    m = summarize(y, pred)
    m["selecao_por_confianca"] = selective(probs.max(1), pred == y, threshold)
    return m


# ---------------------------------------------------------------- main
def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--manifest", type=Path, default=Path("data/manifest.csv"))
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--size", type=int, default=96)
    ap.add_argument("--arch", default="tiny_cnn")
    ap.add_argument("--epochs", type=int, default=40)
    ap.add_argument("--batch", type=int, default=32)
    ap.add_argument("--lr", type=float, default=2e-3)
    ap.add_argument("--patience", type=int, default=8)
    ap.add_argument("--jpeg-quality", type=int, default=85, help="igual a JPEG_QUALITY do backend")
    ap.add_argument("--threshold", type=float, default=0.60, help="confiança mínima; abaixo disso o firmware não aciona a bomba")
    a = ap.parse_args()

    import keras
    import tensorflow as tf
    keras.utils.set_random_seed(SEED)

    xt, yt = load_split(a.manifest, "train", a.size, a.jpeg_quality)
    xv, yv = load_split(a.manifest, "val", a.size, a.jpeg_quality)
    xs, ys = load_split(a.manifest, "test", a.size, a.jpeg_quality)
    print(f"treino {len(xt)} | validação {len(xv)} | teste {len(xs)}  classes treino: {np.bincount(yt, minlength=3).tolist()}")

    model = build_model(a.size, a.arch)
    print(f"parâmetros: {model.count_params():,}")
    aug = augmenter()
    ds = (tf.data.Dataset.from_tensor_slices((xt.astype("float32"), yt)).shuffle(len(xt), seed=SEED)
          .batch(a.batch).map(lambda x, y: (aug(x, training=True), y), num_parallel_calls=tf.data.AUTOTUNE).prefetch(2))
    steps = max(1, a.epochs * int(np.ceil(len(xt) / a.batch)))
    lr = keras.optimizers.schedules.CosineDecay(a.lr, steps)
    model.compile(keras.optimizers.Adam(lr), "sparse_categorical_crossentropy", metrics=["accuracy"])
    best = BestF1(model, xv, yv, a.patience)
    model.fit(ds, epochs=a.epochs, class_weight=class_weights(yt), callbacks=[best.cb], verbose=0)
    model.set_weights(best.best_w)

    a.out.mkdir(parents=True, exist_ok=True)
    model.save(a.out / "model.keras")
    blob = to_tflite_int8(model, xt)
    (a.out / "model.tflite").write_bytes(blob)
    info = tflite_info(blob)

    keras_metrics = evaluate(model.predict(xs.astype("float32"), verbose=0), ys, a.threshold)
    tfl_metrics = evaluate(tflite_predict(blob, xs), ys, a.threshold)
    version = f"{a.arch}-{a.size}-{dt.date.today():%Y%m%d}"
    (a.out / "labels.json").write_text(json.dumps(list(LABELS)), encoding="utf-8")
    (a.out / "metrics.json").write_text(json.dumps({"teste_keras_float": keras_metrics, "teste_tflite_int8": tfl_metrics,
                                                    "validacao_f1_por_epoca": best.history}, indent=2, ensure_ascii=False), encoding="utf-8")
    (a.out / "model_card.json").write_text(json.dumps({
        "version": version, "arch": a.arch, "input_size": a.size, "labels": list(LABELS), "jpeg_quality": a.jpeg_quality,
        "low_confidence_threshold": a.threshold, "parameters": int(model.count_params()), "tflite_bytes": len(blob),
        "tflite": info, "trained_on": {"train": len(xt), "val": len(xv), "test": len(xs)},
        "test_accuracy_int8": tfl_metrics["acuracia"], "test_f1_macro_int8": tfl_metrics["f1_macro"],
        "nota": "A RAM real (tensor arena) só se mede no ESP32. Veja docs/04_FIRMWARE_ESP32.md.",
    }, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"\nTESTE  float: acc {keras_metrics['acuracia']:.3f}  F1 macro {keras_metrics['f1_macro']:.3f}")
    print(f"TESTE  int8 : acc {tfl_metrics['acuracia']:.3f}  F1 macro {tfl_metrics['f1_macro']:.3f}   (é este que roda no ESP32)")
    print("matriz de confusão (linhas=real, colunas=previsto; ordem", list(LABELS), "):")
    for row in tfl_metrics["matriz_confusao"]:
        print("  ", row)
    print(f"modelo TFLite: {len(blob) / 1024:.1f} KB | ops: {', '.join(info['ops']) or 'n/d'}")
    print(f"salvo em {a.out}")


if __name__ == "__main__":
    main()
