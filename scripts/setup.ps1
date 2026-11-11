# Prepara o ambiente de desenvolvimento no Windows (PowerShell).
$ErrorActionPreference = "Stop"
Set-Location (Join-Path $PSScriptRoot "..")
python -m venv .venv
.\.venv\Scripts\python -m pip install -U pip
.\.venv\Scripts\pip install -r backend\requirements-dev.txt
Push-Location frontend; npm ci --no-audit --no-fund; npm run build; Pop-Location
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
Write-Host "Pronto. Testes: scripts\test.ps1 | Rodar: scripts\dev.ps1"
