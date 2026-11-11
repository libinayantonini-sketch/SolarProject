# 09 · Testes e validação

## Rodar
`scripts/test.sh` (ou `.ps1`): backend (pytest), pipeline de dados do `ai-model`, typecheck do front e política da bomba em C++.
Postgres: `TEST_DATABASE_URL=postgresql+psycopg://u:s@host/db_de_teste scripts/test.sh` (o banco será **apagado e recriado**; use UTF8).

## O que foi verificado (05/11/2026)
| Verificação | Resultado |
| --- | --- |
| `backend/tests` (41 testes): API, banco, fluxo com ESP32 simulado **real via HTTP**, falhas do ESP32, modo servidor (ONNX sintético), classes e tamanhos configuráveis, exportação, migração de banco antigo, assistente, simulador | passou em SQLite. PostgreSQL 16 passou antes do modo servidor e **não foi reexecutado** depois |
| Falhas do ESP32 (offline, 500, classe inventada, bomba > 60 s, não configurado) não gravam nada nem deixam arquivo órfão | testado |
| Anti path traversal no armazenamento | testado |
| `ai-model/tests`: parse de classes, formatos Roboflow (pasta e CSV), duplicatas, partição estratificada, recusa de detecção | passou |
| Treino Keras → TFLite int8 → simulador (TFLite) com dataset **sintético** | funcionou (acurácia 100% num dataset trivial; **não significa nada** para fotos reais) |
| Front no Chromium (Playwright) contra o stack real (PostgreSQL + API + simulador): analisar, bomba, cooldown, histórico, filtro, correção, painel, assistente, erro, mobile escuro, sem scroll horizontal, sem erros de console | passou |
| Política da bomba em C++ (incluindo virada do `millis()`) | passou |
| Sintaxe do Terraform (python-hcl2) | ok |

| Recomendação de chuva: regra, janelas de 24 h, dados faltando, cache, plano B, rota; cartão no navegador (desktop e mobile escuro) | passou, com resposta **simulada** no formato da documentação |

## O que NÃO foi verificado (faça antes de apresentar)
1. **Acurácia real**: treinar com o dataset + suas fotos e ler `metrics.json`. Meça com fotos do **seu** painel.
2. **Firmware**: compilar, gravar, checar `arena_used_bytes`, tempo de inferência, estabilidade do heap (`04_FIRMWARE_ESP32.md`, checklist).
3. **Paridade ESP32 × simulador** nas mesmas fotos.
4. **Bomba**: LED primeiro; depois MOSFET sem água; depois com água.
5. **Gemini real** (chave + `GEMINI_MODEL`): pergunta de teste com `fonte: gemini`; confira limites do plano gratuito.
6. **Open‑Meteo real**: abra `/api/weather/advice` com internet e compare com um app de previsão. **Docker** (`docker compose up --build`) e **Terraform** (`plan`/`apply`).
7. **Celular real**: câmera (`capture`), acesso pelo IP da rede, desempenho.
8. Auditoria de acessibilidade completa (verificado só por inspeção: textos junto com cores, alvos ≥ 44 px, rótulos, `aria-live`).

## Limitações conhecidas
- Sem migrações de banco, sem TLS, sem login de usuários, sem limitação de taxa.
- O ESP32 atende uma foto por vez; o backend espera a resposta (timeout 30 s).
- Bundle do front ~550 KB (160 KB gzip): ok em rede local.
- Fuso do painel fixo em America/Sao_Paulo.
