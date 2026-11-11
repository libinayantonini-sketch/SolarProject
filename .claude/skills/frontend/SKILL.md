---
name: frontend
description: Trabalhar no front React + TypeScript + Tailwind + Recharts (abas Analisar, Histórico, Painel, Assistente). Use ao criar telas, componentes ou ajustar o fluxo de upload.
---
# Front (frontend/)

Vite + React 18 + TS estrito + Tailwind 3 + Recharts. `src/api.ts` é o único lugar que chama a API; tipos em `src/types.ts`.
Comandos: `npm run dev` (proxy `/api` → :8000) · `npm run typecheck` · `npm run build` (gera `dist/`, servido pelo FastAPI).

Regras de UX (apresentação ao vivo, celular):
- Classe sempre com **texto + símbolo**, nunca só cor (`LabelBadge`). Cores em `lib/format.ts`; tema escuro por `prefers-color-scheme`.
- Alvos de toque ≥ 44 px; sem scroll horizontal em 390 px; `aria-live` em resultados; rótulos em todo input.
- A foto é reduzida **no navegador** para `config.input_size` (esticada, JPEG) em `lib/image.ts`; o tamanho vem de `/api/config`. Não duplique o valor no código.
- Câmera: `<input type=file capture=environment>` (não exige HTTPS). Não use `getUserMedia` sem tratar o requisito de HTTPS.
- A bomba só é pedida (`pump=true`) se o usuário deixar marcado; sem chave de admin o backend a bloqueia e a tela explica.
- Mostrar o estado real: ESP32 offline, erro 504/502, "simulador". Nunca fingir sucesso.
- Teste visual: suba o stack (`scripts/dev.sh`) e use Playwright; confira claro, escuro e 390 px.
