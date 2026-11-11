# 07 · API (resumo; a versão interativa está em `/docs` com o backend no ar)

| Método | Rota | Auth | Descrição |
| --- | --- | --- | --- |
| GET | `/api/health` | — | banco, ESP32 configurado, modelo do servidor carregado, Gemini, admin protegido |
| GET | `/api/config` | — | `engines.esp32` e `engines.server` (`disponivel`, `classes`, `input_size`, `aciona_bomba`, `motivo`), `upload_max_side`, `jpeg_quality`, `max_upload_mb`, limiar, flags (o front usa para preparar a foto e montar o seletor) |
| GET | `/api/weather/advice` | — | recomendação de chuva (Open‑Meteo): `nivel` (`limpar_agora`/`avaliar`/`adiar`/`indisponivel`), mm passados e próximos 24 h, limiares, crédito. Sempre 200; só informa |
| GET | `/api/devices/status` | — | ESP32 online? (`online`, `latency_ms`, `info`) — nunca dá erro, devolve `online:false` |
| POST | `/api/analyze` | `X-API-Key` só para a bomba | multipart: `file`, `engine` (`esp32` padrão ou `server`; qualquer outro valor dá 422), `pump` (padrão true; ignorado no `server`). Devolve `{analise, bomba_bloqueada_por_falta_de_chave}` |
| GET | `/api/analyses` | — | filtros: `labels` (repetível), `engine`, `needs_review`, `cleaning_activated`, `since`, `until`, `text`, `limit` (≤200), `offset` |
| GET | `/api/analyses/{id}` | — | uma análise |
| GET | `/api/analyses/{id}/image` | — | o JPEG |
| PATCH | `/api/analyses/{id}/label` | admin | `{"label": "SEVERO"}` ou `null` para remover a correção |
| DELETE | `/api/analyses/{id}` | admin | apaga linha e arquivo |
| GET | `/api/export/training.zip` | admin | fotos em pastas por classe + `labels.csv` para retreinar; `only_reviewed` (padrão true), `engine`. 404 se não houver fotos |
| GET | `/api/stats` | — | totais, por rótulo, por motor (`por_motor`), revisão, limpezas, série diária (14 dias, fuso America/Sao_Paulo) |
| POST | `/api/assistant/ask` | — | `{"question": "..."}` → filtro, resultados e resumo |
| POST | `/api/assistant/explain` | — | dúvida geral (IA) |

Códigos de erro de `/api/analyze`: 400 vazio · 413 grande · 422 não é imagem · 502 ESP32 respondeu errado · 503 ESP32 não configurado ou modelo do servidor indisponível · 504 ESP32 não respondeu.
`final_label` = `human_label` se existir, senão `classification`. Filtros e estatísticas usam `final_label`.
Quem admin: sem `ADMIN_API_KEY` configurada **tudo é aberto** (só para teste local).
