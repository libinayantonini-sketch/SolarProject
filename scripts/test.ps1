$ErrorActionPreference = "Stop"
Set-Location (Join-Path $PSScriptRoot "..")
Push-Location backend; ..\.venv\Scripts\python -m pytest -q; Pop-Location
Push-Location ai-model; ..\.venv\Scripts\python -m pytest -q tests; Pop-Location
Push-Location frontend; npm run typecheck; Pop-Location
Write-Host "Teste da política da bomba em C++: rode scripts/test.sh (precisa de g++) ou no WSL."
