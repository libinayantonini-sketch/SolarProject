---
name: backend-api
description: Trabalhar no backend FastAPI (rotas, serviços, cliente do ESP32, validação). Use ao criar ou alterar endpoints, regras de análise ou tratamento de erros.
---
# Backend (backend/)

Estrutura: `app/api/routes.py` (rotas **finas**) · `app/services/analysis.py` (fluxo) · `esp32.py` (cliente) · `storage.py` (arquivos) ·
`app/database/` · `app/schemas/analysis.py` (contrato do ESP32) · `app/config.py` (env) · `main.py` (`uvicorn main:app`).

Fluxo de `/api/analyze`: valida upload → `prepare_image` (estica para `INPUT_SIZE`², JPEG) → `Esp32Client.upload` (valida resposta com `Esp32Result`) →
salva arquivo → `repo.add`. **Se o ESP32 falhar nada é gravado.** Se o banco falhar, o arquivo é removido.

Chuva: `services/weather.py` (`advice` pura, `parse`, `WeatherClient` com cache de 30 min e plano B) → `GET /api/weather/advice`. Só informa; falha ⇒ `disponivel:false`, nunca erro; nunca influencia `pump`.

Regras:
- O backend **nunca** roda o modelo nem decide ligar a bomba. Só repassa `pump=0|1`; sem `X-API-Key` (quando existe `ADMIN_API_KEY`) envia `pump=0`.
- Resposta do ESP32 fora do contrato (classe inventada, `pump_duration_ms` > 60000) → 502.
- Rotas novas: dependências via `Annotated[..., Depends]`; **não** use `from __future__ import annotations` em `routes.py` (quebra os aliases locais do FastAPI).
- Mudou rota/campo? Atualize `docs/07_API_REFERENCIA.md` e `frontend/src/types.ts`. Mudou o contrato do ESP32? Veja a skill `esp32-protocol-simulator`.
- Erros para o usuário em português, sem vazar detalhes internos.
- Teste com `cd backend && ../.venv/bin/python -m pytest -q` (os testes sobem um simulador de ESP32 real via HTTP).
