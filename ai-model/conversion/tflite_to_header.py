"""Converte model.tflite em um array C (model_data.h) para o firmware, e confere o tamanho.

    python conversion/tflite_to_header.py models/current/model.tflite ../firmware/esp32/src/model_data.h
Equivale a `xxd -i`, sem depender dele (Windows).
"""
import sys
from pathlib import Path


def main(src: str, dst: str) -> None:
    data = Path(src).read_bytes()
    lines = [", ".join(f"0x{b:02x}" for b in data[i:i + 16]) for i in range(0, len(data), 16)]
    body = ",\n  ".join(lines)
    Path(dst).write_text(
        "// GERADO por ai-model/conversion/tflite_to_header.py. Não edite à mão.\n"
        "#pragma once\n#include <cstddef>\n"
        f"alignas(16) const unsigned char g_model_data[] = {{\n  {body}\n}};\n"
        f"const size_t g_model_data_len = {len(data)};\n", encoding="utf-8")
    print(f"{src}: {len(data)} bytes ({len(data) / 1024:.1f} KB) -> {dst}")
    if len(data) > 400 * 1024:
        print("AVISO: modelo grande para um ESP32 sem PSRAM. Reduza a rede ou a entrada.")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    main(sys.argv[1], sys.argv[2])
