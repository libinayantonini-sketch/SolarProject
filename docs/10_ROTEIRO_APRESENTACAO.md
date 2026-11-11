# 10 · Roteiro da apresentação

## Véspera
- [ ] Ensaio completo **na rede que será usada**. `curl http://IP-DO-ESP32/` funciona do computador?
- [ ] IP do ESP32 reservado no roteador; `ESP32_URL` correto; indicador do topo mostra "ESP32 online".
- [ ] Modelo **treinado** gravado (não o sintético); `model_version` no resultado confere.
- [ ] Bomba testada com água em recipiente; cooldown ajustado; **intervalo e duração** conhecidos pela equipe.
- [ ] Uma foto de painel sujo, uma limpa e uma moderada **salvas no celular e no computador** (reserva).
- [ ] Gemini testado (ou aceitar o plano B).
- [ ] Chave de administrador anotada; navegador do celular com a aba já aberta.
- [ ] Plano B pronto: `docker compose --profile sim ...` (simulador) se o ESP32 falhar.

## Roteiro (≈5 min)
1. ESP32 ligado e online; abrir o sistema no celular. Mostrar o indicador **ESP32 online**.
2. Tirar foto do painel sujo → **Analisar** → mostrar o indicador de processamento.
3. Resultado: classe, confiança, probabilidades. Se `SEVERO`: mostrar a **bomba acionando** e o texto "Bomba acionada por X s".
4. Repetir com painel limpo: "Bomba não acionada: só SEVERO aciona".
5. Enviar `SEVERO` de novo logo depois: mostrar o **intervalo mínimo** (segurança).
6. Aba **Histórico**: o registro, abrir detalhe, corrigir um rótulo (revisão humana).
7. Aba **Painel**: totais e gráfico.
8. Aba **Assistente**: "fotos sujas de hoje" (mostra se foi Gemini ou regras).

## Se algo falhar
| Sintoma | Ação |
| --- | --- |
| Indicador "ESP32 offline" | ver IP/Wi‑Fi/isolamento de clientes; reiniciar o ESP32; mudar para o simulador |
| Câmera não abre | escolher arquivo da galeria; ou "Reanalisar" uma foto do histórico |
| Erro 504 | ESP32 não respondeu: confira energia e Wi‑Fi |
| Erro 502 | firmware/protocolo incompatível: veja o Monitor Serial |
| Bomba não aciona | normal se não for SEVERO, confiança baixa, cooldown, ou sem chave de admin (o front avisa) |
| Gemini fora | o resumo sai por regras sozinho (`fonte: regras`); seguir |
