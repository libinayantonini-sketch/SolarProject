# Soiling Detection — contexto para agentes (Claude Code, Codex e outros)

Leia este arquivo inteiro antes de mexer. Detalhes por assunto: `docs/` e `.claude/skills/*/SKILL.md`
(são markdown comum: Codex e outros agentes podem lê-los diretamente).

## O que é
Classificação de sujeira em painel solar a partir de foto: **LIMPO / MODERADO / SEVERO**. Se SEVERO e confiança ≥ 0,60,
o ESP32 aciona uma bomba de água. Há **dois modos** de análise, escolhidos no front (não existe modo "comparar"):
- **ESP32** (`engine=esp32`): a inferência roda no ESP32, que também decide a bomba. O backend redimensiona a foto para o tamanho do
  modelo do ESP32, encaminha (`POST /upload`), valida a resposta e grava arquivo + linha no banco.
- **Servidor** (`engine=server`): um modelo grande opcional (ex.: ResNet, ONNX) roda no backend via ONNX Runtime. **Nunca aciona a bomba.**
  Tamanho de entrada e classes são configuração (`ESP32_INPUT_SIZE`, `ESP32_CLASSES`, `SERVER_INPUT_SIZE`, `labels.json`). Veja `docs/12_MODELO_NO_SERVIDOR.md`.

## O que NÃO existe neste projeto (não reintroduza)
Perda de potência (%), valor em R$, pvlib, PLD, motor de decisão por custo, regressão, SQLite em produção.
Exceção decidida em 9/11: **Open‑Meteo só como recomendação de chuva na tela** (`backend/app/services/weather.py`). Ele informa; nunca aciona nem bloqueia a bomba.
`historico/HISTORICO_ATE_AGORA.md` conta o que existiu antes; é só documentação, não código para reaproveitar.

## Mapa
- `backend/` FastAPI. `app/api/routes.py` (rotas finas) · `app/services/` (esp32, analysis, storage, assistant) · `app/database/` (models, repository) · `tests/`
- `frontend/` Vite + React 18 + TS + Tailwind 3 + Recharts. `src/api.ts` é o único lugar que fala com a API.
- `firmware/esp32/` PlatformIO (esp32dev, SEM PSRAM). `src/pump_policy.h` é C++ puro e testado.
- `ai-model/training/` `prepare_data.py` → `train.py` (Keras → TFLite int8) · `conversion/tflite_to_header.py`
- `tools/esp32_simulator/` ESP32 de mentira (mesmo protocolo e mesma política). Use para testar sem hardware.
- `infra/terraform/` AWS opcional · `scripts/` setup/test/dev (sh e ps1)

## Comandos
```bash
scripts/setup.sh                                   # venv + dependências + build do front
scripts/test.sh                                    # backend, ai-model, typecheck do front, política da bomba (C++)
TEST_DATABASE_URL=postgresql+psycopg://u:s@host/db scripts/test.sh   # também no PostgreSQL
scripts/dev.sh                                     # simulador + API em http://localhost:8000
cd frontend && npm run dev                         # front com hot reload (proxy /api -> :8000)
```
Python 3.13; use SEMPRE o `.venv` na raiz (`.venv/bin/python`, `.venv\Scripts\python` no Windows).

## Regras que não podem quebrar
1. **Ordem das classes** `LIMPO, MODERADO, SEVERO` é a ordem das saídas do modelo. Está em `backend/app/labels.py`,
   `ai-model/training/labels.py` e `tools/esp32_simulator/classifier.py`. Mude nos três ou em nenhum — e retreine.
2. **Contrato de pré-processamento**: imagem esticada (sem recorte) para `INPUT_SIZE×INPUT_SIZE` (padrão 96), JPEG; a
   normalização vive DENTRO do modelo. `INPUT_SIZE` aparece em `backend/app/config.py`, `firmware/esp32/src/config.h`,
   `model_card.json`. Se mudar um, mude todos.
3. **Segurança da bomba** é imposta no FIRMWARE (`pump_policy.h`) e espelhada no simulador: só SEVERO, confiança ≥ limiar,
   intervalo mínimo, duração ≤ 60 s, desligada ao boot e sem Wi‑Fi. O backend valida `pump_duration_ms ≤ 60000`, mas
   NUNCA decide ligar. Sem `X-API-Key` (quando `ADMIN_API_KEY` existe) o backend envia `pump=0`.
4. **Imagem em arquivo, caminho no banco** (`analyses.image_path`, relativo a `STORAGE_DIR`). Nunca bytea.
5. `confidence` é confiança do classificador, **não** percentual de sujeira. `dirt_level` fica NULL (o modelo não mede).
6. A correção humana vai em `human_label`; `classification` (o que o ESP32 disse) nunca é sobrescrita.
7. A IA (Gemini) só traduz pergunta→filtro e redige resumo com números que o banco forneceu. Sem chave ou em falha, há plano B
   por regras. Nunca envie fotos à IA. `GEMINI_MODEL` não tem padrão de propósito.
8. **Chuva (Open‑Meteo) é só aviso**: falha/indisponível ⇒ o sistema segue normal; limiares (`RAIN_LIGHT_MM`, `RAIN_HEAVY_MM`) são provisórios; o crédito "Open‑Meteo.com" fica visível; uso gratuito é só não comercial.
9. Segredos só em `.env` / SSM. Nunca em código, log ou commit.
10. Nunca diga que algo foi testado sem ter rodado. O que NÃO está validado está listado em `README.md` e `docs/09_TESTES_E_VALIDACAO.md`.

## Antes de entregar uma mudança
Rode `scripts/test.sh`. Mudou API? Atualize `docs/07_API_REFERENCIA.md` e `frontend/src/types.ts`. Mudou o protocolo do ESP32?
Atualize `docs/05_PROTOCOLO_ESP32.md`, `backend/app/schemas/analysis.py`, `tools/esp32_simulator/server.py` e `firmware/esp32/src/main.cpp`.
