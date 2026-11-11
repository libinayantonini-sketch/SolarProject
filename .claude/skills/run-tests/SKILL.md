---
name: run-tests
description: Rodar e interpretar todos os testes do projeto (backend, ai-model, front, política da bomba) e saber o que eles não cobrem. Use antes de entregar qualquer mudança.
---
# Testes

`scripts/test.sh` (ou `.ps1`) roda: `backend` (pytest, 41 testes: API, banco, ESP32 simulado real, falhas, modo servidor, assistente; com `TEST_DATABASE_URL` os testes de banco rodam também no PostgreSQL), `ai-model/tests` (dados), `npm run typecheck` e a política da bomba em C++.
Postgres: `TEST_DATABASE_URL=postgresql+psycopg://u:s@host/teste scripts/test.sh` (apaga e recria as tabelas daquele banco; UTF8).
Verificação do front no navegador: suba `scripts/dev.sh` e use Playwright (claro, escuro, 390 px).

**Não cobrem:** acurácia com fotos reais, firmware em hardware, bomba, Gemini real, Docker, Terraform, celular real. Liste isso ao reportar resultados; nunca diga "testado" sem ter rodado.
Falha típica: `ModuleNotFoundError: app` ⇒ rodar de dentro de `backend/`; `esp32_simulator` ⇒ `PYTHONPATH=tools` (o `pytest.ini` já cuida disso).
Toda correção de bug ganha um teste.
