---
name: presentation-demo
description: Preparar e conduzir a demonstração ao vivo (checklist, roteiro, plano B). Use na véspera e durante a apresentação.
---
# Apresentação

Roteiro completo e tabela de falhas: `docs/10_ROTEIRO_APRESENTACAO.md`. Resumo:
1. Ensaiar **na rede real**; `curl http://IP-ESP32/` do computador; indicador do topo em "ESP32 online".
2. Modelo **treinado** gravado (não o sintético); fotos de reserva (suja, moderada, limpa) no celular.
3. Fluxo: foto suja → resultado + bomba; foto limpa → bomba não aciona; SEVERO repetido → intervalo mínimo; histórico + correção; painel; assistente.
4. Plano B: simulador (`--profile sim`), "Reanalisar" foto do histórico se a câmera falhar, plano B por regras se o Gemini falhar.
Seja claro com a banca sobre o que é protótipo: acurácia medida em quais fotos, limites de memória do ESP32, ausência de TLS/login.
