---
name: database
description: Esquema, repositório e operação do PostgreSQL/SQLite (tabela analyses, imagens em arquivo). Use ao mexer em colunas, consultas, estatísticas ou testes de banco.
---
# Banco (backend/app/database/)

- Tabela única `analyses` (`models.py`). **Imagem em arquivo** (`STORAGE_DIR`), coluna `image_path` relativa. Nunca bytea.
- Todo acesso passa por `repository.py` (`Repository`). Rotas não escrevem SQL.
- Funciona em SQLite (testes) e PostgreSQL 16. Evite SQL específico de um dos dois. Datas em UTC (`timestamptz`); o painel agrupa por dia em America/Sao_Paulo.
- `classification` (o que o ESP32 disse) nunca é sobrescrita; correção humana vai em `human_label`. Filtros/estatísticas usam `COALESCE(human_label, classification)`.
- `dirt_level` é NULL: o modelo não mede sujeira. `confidence` não é percentual de sujeira.
- Não há Alembic. Mudou coluna? Documente em `docs/03_BANCO_DE_DADOS.md` e avise que o volume de teste precisa ser recriado (ou introduza Alembic).
- Postgres nos testes: `TEST_DATABASE_URL=postgresql+psycopg://u:s@host/teste` — o banco será **apagado**; precisa ser UTF8 (SQL_ASCII quebra o psycopg).
- Backup: `pg_dump` **e** o volume de imagens, juntos.
