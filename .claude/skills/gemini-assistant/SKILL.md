---
name: gemini-assistant
description: Assistente com Gemini (busca em português, resumo, dúvida geral) e seu plano B por regras. Use ao ajustar prompts, filtros, validação ou configuração da IA.
---
# Assistente (backend/app/services/assistant/)

- `gemini.py`: cliente REST mínimo (`generateContent`, header `x-goog-api-key`). **Nunca foi chamado contra a API real**; testado com `httpx.MockTransport`.
- `service.py`: `interpret` (pergunta → `SearchFilter`, validado por pydantic; falha → regras), `summarize` (resumo só com contagens do banco; **todo número do texto deve existir nos dados**, senão texto determinístico), `explain` (conhecimento geral, marcado como IA).
- `search.py`: `SearchFilter` + `rule_based_filter` (plano B em português).
- Config: `GEMINI_API_KEY` e `GEMINI_MODEL`. **Sem padrão de modelo, de propósito.** Sem as duas, tudo roda por regras.

Regras: nunca enviar fotos nem dados pessoais; só agregados. A IA não escolhe análises nem calcula: o banco busca e conta. Resposta sempre informa `fonte`.
Ao mudar o `SearchFilter`: atualize o prompt `SYSTEM_FILTER`, `describe_filter`, `rule_based_filter`, `Repository._apply` e os testes.
Antes da apresentação: faça uma pergunta real e confirme `fonte: gemini`; confira limites e termos do plano gratuito na documentação do Google.
