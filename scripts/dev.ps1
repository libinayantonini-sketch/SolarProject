Set-Location (Join-Path $PSScriptRoot "..")
$env:PYTHONPATH = "tools"
$sim = Start-Process -PassThru -NoNewWindow .\.venv\Scripts\python -ArgumentList "-m","esp32_simulator.server","--demo-model","--port","8081","--host","127.0.0.1"
try {
  Set-Location backend
  $env:ESP32_URL = "http://127.0.0.1:8081"; $env:INPUT_SIZE = "96"
  ..\.venv\Scripts\python -m uvicorn main:app --port 8000
} finally { Stop-Process -Id $sim.Id -ErrorAction SilentlyContinue }
