# 03 · Banco de dados

PostgreSQL 16 em uso real; SQLite só em testes/desenvolvimento rápido. Mesmo código (SQLAlchemy 2). O esquema é criado no boot (`create_all`).
**Não há Alembic.** Existe só uma migração leve no boot: colunas **novas e opcionais** (ou com padrão) são adicionadas a tabelas antigas
(`ALTER TABLE ... ADD COLUMN`), sem tocar nos dados. Mudar ou remover coluna ainda exige apagar o volume na demo ou adotar Alembic.

## Tabela `analyses`
| Coluna | Tipo | Descrição |
| --- | --- | --- |
| `id` | int, PK | identificador |
| `image_path` | texto | caminho **relativo** a `STORAGE_DIR` (`2026/11/<uuid>.jpg`). A imagem não está no banco |
| `original_filename` | texto | nome do arquivo enviado |
| `engine` | `esp32` / `server` | quem classificou. Linhas antigas valem `esp32` |
| `classification` | `LIMPO/MODERADO/SEVERO` | o que o motor respondeu (nunca é sobrescrito) |
| `confidence` | float 0–1 | confiança do classificador (**não** é % de sujeira) |
| `probs` | JSON | probabilidade por classe |
| `low_confidence` | bool | `confidence < LOW_CONFIDENCE_THRESHOLD` (padrão 0,60) |
| `cleaning_activated` | bool | a bomba foi acionada? |
| `pump_duration_ms` | int | duração informada pelo firmware (≤ 60 000) |
| `pump_reason` | texto | por que acionou ou não |
| `dirt_level` | float, NULL | só se o modelo medir de verdade; o nosso **não mede** → NULL |
| `model_version`, `inference_ms`, `round_trip_ms` | | rastreabilidade e desempenho |
| `width`, `height` | int | dimensões da imagem guardada (normalizada, até `UPLOAD_MAX_SIDE` px; fotos antigas podem ser 96×96) |
| `human_label`, `reviewed_at` | | correção feita por pessoa; vale para estatísticas e filtros (`final_label`) |
| `created_at` | timestamptz (UTC) | índice para listagens |

## Imagens em arquivo
Escolha da arquitetura da equipe: arquivos no disco do backend, caminho no banco. Em Docker, o volume `images` guarda os arquivos —
**faça backup do volume junto com o banco**, senão as linhas ficam sem imagem. A API serve a imagem por `/api/analyses/{id}/image` e
bloqueia caminhos fora de `STORAGE_DIR`.

## Operação
- Conexão: `DATABASE_URL=postgresql+psycopg://usuario:senha@host:5432/soiling` (`postgres://` e `postgresql://` também são aceitos).
- Backup: `docker compose exec db pg_dump -U soiling soiling > backup.sql`.
- Testar no Postgres: `TEST_DATABASE_URL=... scripts/test.sh`. O banco de teste deve ser **UTF8** (um banco `SQL_ASCII` quebra o driver).
- Os testes apagam e recriam as tabelas do banco indicado em `TEST_DATABASE_URL`: **nunca aponte para um banco com dados**.
