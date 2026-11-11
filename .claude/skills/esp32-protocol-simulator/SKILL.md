---
name: esp32-protocol-simulator
description: Protocolo HTTP backend↔ESP32 e o simulador do ESP32 para testar sem hardware. Use ao alterar o contrato, depurar integração ou ensaiar a apresentação.
---
# Protocolo e simulador

Contrato: `docs/05_PROTOCOLO_ESP32.md`. `GET /` (vivo) e `POST /upload?pump=0|1` (JPEG `INPUT_SIZE`², ≤ 32 KB, `X-Device-Key` opcional) → JSON com
`classification, confidence, probs, cleaning_activated, pump_duration_ms, reason, inference_ms, model_version`.

**Quatro implementações que andam juntas:** `firmware/esp32/src/main.cpp`, `tools/esp32_simulator/server.py`,
`backend/app/services/esp32.py` + `backend/app/schemas/analysis.py`. Mudou o contrato ⇒ mude os quatro e `docs/05_*`.

Simulador:
```bash
PYTHONPATH=tools .venv/bin/python -m esp32_simulator.server --demo-model --port 8081       # modelo sintético (cor dominante!)
PYTHONPATH=tools .venv/bin/python -m esp32_simulator.server --model-dir ai-model/models/current --port 8081 --key SEGREDO
```
Ele aplica a mesma política da bomba (`--pump-ms`, `--cooldown-s`) e carrega `model.tflite` (ai-edge-litert ou TensorFlow) ou `model.onnx`.
Limites: não prova que o modelo cabe no ESP32 nem reproduz o tempo de inferência. O `--demo-model` NÃO classifica sujeira.
Backend aponta para ele com `ESP32_URL=http://127.0.0.1:8081`. Os testes do backend já sobem um simulador real em thread.
