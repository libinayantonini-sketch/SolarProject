#!/usr/bin/env bash
# Roda os testes. Para testar também no PostgreSQL: TEST_DATABASE_URL=postgresql+psycopg://user:senha@localhost:5432/teste scripts/test.sh
set -euo pipefail
cd "$(dirname "$0")/.."
PY="$PWD/.venv/bin/python"
(cd backend && "$PY" -m pytest -q)
(cd ai-model && "$PY" -m pytest -q tests)
(cd frontend && npm run typecheck)
g++ -std=c++17 -Wall -I firmware/esp32/src firmware/esp32/test/test_pump_policy.cpp -o /tmp/pump_policy_test && /tmp/pump_policy_test
