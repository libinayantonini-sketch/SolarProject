#!/usr/bin/env bash
# Sobe o simulador do ESP32 (modelo sintético) e a API com SQLite, sem Docker e sem hardware. http://localhost:8000
set -euo pipefail
cd "$(dirname "$0")/.."
ROOT="$PWD"
export PYTHONPATH=tools
"$ROOT/.venv/bin/python" -m esp32_simulator.server --demo-model --port 8081 --host 127.0.0.1 &
SIM=$!; trap 'kill $SIM' EXIT
cd backend
ESP32_URL=http://127.0.0.1:8081 ESP32_INPUT_SIZE=96 "$ROOT/.venv/bin/python" -m uvicorn main:app --port 8000
