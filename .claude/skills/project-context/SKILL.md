---
name: project-context
description: Contexto essencial do Soiling Detection (escopo, arquitetura, o que não existe). Use ao começar qualquer tarefa neste repositório ou quando houver dúvida sobre escopo.
---
# Soiling Detection — contexto

**Escopo:** foto de painel solar → `LIMPO` / `MODERADO` / `SEVERO`. SEVERO com confiança ≥ 0,60 aciona bomba de água. Só isso.

**Arquitetura:** front React → backend FastAPI → ESP32 (HTTP local). **A rede neural roda no ESP32** (TFLite int8, entrada 96×96). O backend
encaminha a foto, valida a resposta e grava arquivo + linha em `analyses` (PostgreSQL). Gemini (opcional) resume e busca.

**Não existe aqui (não reintroduzir):** perda de potência, R$, pvlib, PLD, regressão, inferência no servidor, imagem em bytea.

**Exceção:** Open‑Meteo existe só como *recomendação de chuva* na tela (`services/weather.py`, `WeatherCard.tsx`); nunca decide a bomba.

**Leia:** `AGENTS.md` (regras que não podem quebrar), `docs/00_VISAO_GERAL.md`, `docs/01_ARQUITETURA.md`.
**Honestidade:** o que está validado e o que não está fica em `README.md` e `docs/09_TESTES_E_VALIDACAO.md`. Firmware, acurácia real, Gemini real, Docker e Terraform **não** foram executados; nunca afirme o contrário.
