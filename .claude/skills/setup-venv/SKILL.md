---
name: setup-venv
description: Criar e usar o ambiente virtual Python (.venv) e instalar dependências do backend, simulador e testes. Use antes de rodar qualquer código Python do projeto.
---
# Ambiente Python

Python 3.13. Um único `.venv` na raiz do repositório.

```bash
python3 -m venv .venv                               # Windows: python -m venv .venv
.venv/bin/pip install -U pip                        # Windows: .venv\Scripts\pip
.venv/bin/pip install -r backend/requirements-dev.txt     # backend + simulador + pytest
.venv/bin/pip install -r ai-model/requirements.txt        # só se for treinar (TensorFlow CPU, pesado)
```
Atalho: `scripts/setup.sh` (ou `scripts/setup.ps1`), que também compila o front.

- Sempre chame `.venv/bin/python`, nunca o `python` do sistema. No Windows: `.venv\Scripts\python`.
- Ao rodar fora do pytest, o backend precisa estar no diretório `backend/` (importa `app.*`) e o simulador precisa de `PYTHONPATH=tools`.
- `.env` (copie de `.env.example`) guarda configuração; nunca faça commit dele.
- O backend **não** usa PyTorch nem TensorFlow. TensorFlow só existe em `ai-model/`.
