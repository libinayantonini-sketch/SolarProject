#!/usr/bin/env bash
# Prepara o ambiente de desenvolvimento (Linux/macOS). Windows: scripts/setup.ps1
set -euo pipefail
cd "$(dirname "$0")/.."
python3 -m venv .venv
.venv/bin/pip install -U pip
.venv/bin/pip install -r backend/requirements-dev.txt
(cd frontend && npm ci --no-audit --no-fund && npm run build)
[ -f .env ] || cp .env.example .env
echo "Pronto. Testes: scripts/test.sh | Rodar: scripts/dev.sh"
