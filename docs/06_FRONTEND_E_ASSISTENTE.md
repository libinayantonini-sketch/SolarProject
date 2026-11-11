# 06 · Front-end e assistente (Gemini)

## Front
React 18 + TypeScript + Tailwind 3 + Recharts, Vite. Código em `frontend/src`; `api.ts` é a única porta para a API.
Desenvolvimento: `cd frontend && npm run dev` (http://localhost:5173, `/api` vai para `:8000`). Produção: `npm run build` → `frontend/dist`,
servido pelo FastAPI (e pelo Docker).

| Aba | Faz |
| --- | --- |
| Analisar | escolhe/tira foto, reduz no navegador para o tamanho do modelo, envia, mostra classe, probabilidades, bomba, tempos |
| Histórico | cards com filtros (classe, para revisar, bomba acionada), detalhe, **correção humana**, reanálise, apagar |
| Painel | totais, limpezas acionadas, tempo de bomba, para revisar, confiança média, gráfico por dia (atualiza a cada 10 s) |
| Assistente | busca em português nas análises ou dúvida geral sobre soiling |

Topo: indicador do ESP32 (consulta `/api/devices/status` a cada 5 s; mostra "simulador" quando for o simulador) e botão **Admin** (chave guardada só na aba).

**Câmera:** usamos `<input type="file" capture="environment">`, que abre o app de câmera do celular e **não exige HTTPS** (ao contrário de `getUserMedia`).
Testado só no Chromium desktop e emulação de celular; teste no aparelho que será usado na apresentação.

**Reanalisar** (no detalhe de uma análise) reenvia uma foto já guardada: é a "imagem de reserva" se a câmera falhar. Cria uma nova análise, com a bomba desativada.

## Recomendação de chuva (aba Analisar, no topo)
Antes de enviar a foto, a pessoa vê uma recomendação baseada na previsão da [Open‑Meteo](https://open-meteo.com/) para a posição do painel
(`PANEL_LAT`/`PANEL_LON`; padrão Londrina‑PR −23,3103 / −51,1628). **Só informa**: não aciona nem bloqueia a bomba; quem decide é a pessoa.
| Chuva prevista em 24 h | Recomendação |
| --- | --- |
| < `RAIN_LIGHT_MM` (1 mm) | limpar agora faz sentido (avisa se a probabilidade ≥ 60 %) |
| de 1 mm a < `RAIN_HEAVY_MM` (10 mm) | chuva fraca pode deixar lama e marcas: avaliar esperar passar |
| ≥ 10 mm | chuva forte tende a lavar: considerar adiar |
Também mostra a chuva das últimas 24 h (se já choveu forte, "confira a foto: o painel pode ter sido lavado").
- **Limiares provisórios**: quantos mm lavam um painel depende de inclinação, poeira e região. Calibrem observando o painel e ajustem no `.env`.
- Consulta `precipitation` e `precipitation_probability` por hora (`past_days=1`, `forecast_days=2`), cache de 30 min, timeout 4 s. Sem internet: cartão "Sem dados de chuva agora" e o resto funciona.
- Uso gratuito da Open‑Meteo é **só não comercial** (projeto acadêmico se enquadra); dados CC BY 4.0 ⇒ o crédito fica na tela. Limites gratuitos (600/min, 5 mil/h, 10 mil/dia) sobram.
- Só faz sentido com o painel ao ar livre. **Não testado contra o servidor real da Open‑Meteo** (o ambiente de construção bloqueia o site): testado com respostas simuladas no formato da documentação.

## Assistente
Rotas `POST /api/assistant/ask` (buscar) e `/explain` (dúvida geral). Fluxo de `ask`:
1. **Gemini** converte a pergunta em um filtro JSON (classes, período, revisão, bomba…). O JSON é **validado** (pydantic); inválido → regras em português.
2. **O banco** busca e conta. A IA nunca vê fotos nem escolhe análises.
3. A IA recebe só **contagens agregadas** e redige até 4 frases. **Todo número do texto precisa existir nos dados enviados**; senão descartamos e usamos um texto determinístico.
4. A resposta traz `fonte` (`gemini` ou `regras`) e o front mostra qual foi usada.
`explain` é conhecimento geral da IA, marcado como tal, sem números de estudos.

Configuração: `GEMINI_API_KEY` e `GEMINI_MODEL` (sem padrão: nomes mudam; veja a lista atual em <https://ai.google.dev/gemini-api/docs/models>).
Sem as duas, tudo funciona por regras. **Não testado contra a API real**: antes da apresentação, faça uma pergunta e confirme `fonte: gemini`.
Verifique limites e uso de dados do plano gratuito na documentação do Google (não conseguimos abrir a página de limites ao construir isto).
Precisa de internet; sem internet o plano B entra sozinho.
