# Soiling Detection

Protótipo que **classifica o nível de sujeira de um painel solar a partir de uma foto** (`LIMPO`, `MODERADO` ou `SEVERO`)
e, se for `SEVERO` com confiança suficiente, **aciona uma pequena bomba de água** para limpar.

A rede neural roda **no ESP32**. O backend só recebe a foto do front, encaminha ao ESP32 pelo Wi‑Fi local e registra o resultado.

```
Celular/PC (React)  ──foto──▶  Backend (FastAPI)  ──JPEG 96×96──▶  ESP32 (TFLite int8)
      ▲                         │  grava arquivo + linha                │  decide a bomba
      └──── resultado ──────────┴──── PostgreSQL ◀── resultado ─────────┘
                                         ▲
                      Gemini (opcional): resumos e busca em português
```

| Pasta | O que tem |
| --- | --- |
| `frontend/` | React + TypeScript + Tailwind + Recharts: analisar, histórico, painel, assistente |
| `backend/` | FastAPI, PostgreSQL (SQLite nos testes), cliente do ESP32, modelo grande opcional (ONNX), assistente Gemini |
| `firmware/esp32/` | PlatformIO: servidor HTTP, decodificação JPEG, TFLite Micro, bomba com política de segurança |
| `ai-model/` | Preparo do dataset Roboflow, treino Keras, exportação TFLite int8 |
| `backend/app/services/weather.py` | Recomendação de chuva (Open‑Meteo): só informa, nunca aciona a bomba |
| `tools/esp32_simulator/` | **ESP32 de mentira** com o mesmo protocolo: permite testar e ensaiar sem hardware |
| `infra/terraform/` | Implantação opcional na AWS (dashboard/histórico; ver limite abaixo) |
| `docs/` | Documentação (comece por `docs/00_VISAO_GERAL.md`) |
| `.claude/skills/` | Skills para Claude Code e Codex (`AGENTS.md` é o contexto principal) |
| `historico/` | Registro do que foi feito antes da mudança de rumo (só documentação) |

## Rodar agora, sem hardware

```bash
scripts/setup.sh          # Windows: scripts\setup.ps1  (cria .venv, instala, compila o front)
scripts/dev.sh            # simulador do ESP32 + API com SQLite  ->  http://localhost:8000
```
Ou com Docker (PostgreSQL incluso): `cp .env.example .env`, edite, `docker compose --profile sim up -d --build`.

O simulador usa, por padrão, um **modelo sintético que decide pela cor dominante, não pela sujeira**. Só depois de treinar
(`docs/02_DATASET_E_TREINO.md`) o resultado passa a significar algo.

## O que está validado e o que não está (leia antes da apresentação)

| Parte | Estado |
| --- | --- |
| Backend, banco (SQLite **e** PostgreSQL 16), protocolo com ESP32 simulado | testado automaticamente: 41 testes em SQLite. PostgreSQL 16 passou antes do modo servidor (10/11) e **não foi reexecutado** depois |
| Modo servidor (modelo grande ONNX) | testado com um ONNX **sintético** (carga, os dois modos, bomba nunca acionada, modelo ausente, exportação, navegador). Acurácia e latência de uma ResNet real: **não medidas** |
| Front no navegador (fluxo completo, mobile, tema escuro) | testado com Playwright contra o stack real, usando o simulador |
| Pipeline de treino → TFLite int8 → simulador | testado de ponta a ponta com imagens **sintéticas** (prova o encanamento, não a acurácia) |
| Política de segurança da bomba (C++) | testada no computador |
| **Acurácia com fotos reais** | **não medida**: falta treinar com o dataset Roboflow e suas fotos |
| **Firmware no ESP32, memória do modelo, bomba real** | **não testado em hardware**: código escrito, não compilado aqui |
| Gemini real | **não testado** contra a API (sem rede no ambiente de construção); testado com cliente falso |
| Docker, Terraform | **não executados** (sem Docker/Terraform aqui); Terraform só teve a sintaxe verificada |

Detalhes e checklist: `docs/09_TESTES_E_VALIDACAO.md`. Perguntas em aberto: `docs/11_PENDENCIAS.md`.
