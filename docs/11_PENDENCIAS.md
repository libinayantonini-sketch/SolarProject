# 11 · Pendências e decisões em aberto

| # | Item | Estado / recomendação |
| --- | --- | --- |
| 1 | **Mapeamento das classes** do Roboflow (Clean/Dusty/Soiled → LIMPO/MODERADO/SEVERO) | suposição; conferir imagens e ajustar `--class-map` |
| 2 | **Tipo do projeto Roboflow** (classificação ou detecção?) e formato de export | não confirmado; precisa ser classificação |
| 3 | **Treino com dados reais** e acurácia | pendente |
| 4 | **Modelo cabe no ESP32?** (arena, velocidade, heap) | pendente de teste em hardware; ver `04_` |
| 5 | **Câmera**: foto vem do celular/PC (arquitetura atual) ou ESP32‑CAM? | decidido: celular/PC; ESP32‑CAM seria outra arquitetura |
| 6 | **Bomba**: modelo, tensão, vazão; sensor de nível de água; botão de parada | pendente; definir antes de ligar |
| 7 | **Parâmetros da bomba** (duração, cooldown) | padrão 5 s / 60 s; ajustar com a bomba real |
| 8 | **Gemini**: modelo, limites e termos do plano gratuito | pendente; sem padrão de propósito |
| 9 | **Nuvem**: AWS por padrão; realmente precisa? | local é o recomendado; Terraform é opcional (limite do ESP32 na LAN) |
| 10 | Migrações (Alembic), TLS, login | fora do escopo do protótipo |
| 11 | Limiar de confiança 0,60 | ponto de partida; calibrar com `metrics.json` |
| 13 | Recomendação de chuva: posição real do painel e limiares (1 mm / 10 mm são provisórios) | calibrar observando; testar com a API real |
| 12 | Mais de um ESP32 | não suportado nesta versão (um `ESP32_URL`) |
| 14 | **Modelo grande do servidor**: qual ResNet, arquivo ONNX, tamanho de entrada, normalização, saída (logits ou probabilidades), ordem das classes | pendente da equipe; o backend lê tudo da pasta `models/server` (`12_MODELO_NO_SERVIDOR.md`) |
| 15 | **ESP32 com 2 classes (LIMPO/SEVERO)?** | o backend já aceita (`ESP32_CLASSES=LIMPO,SEVERO`); treino, simulador e firmware ainda assumem 3 classes (lista em `12_`) |
| 16 | **Tamanho de entrada** dos dois modelos | configurável (`ESP32_INPUT_SIZE`, `SERVER_INPUT_SIZE`); definir quando o treino fechar |
| 17 | Latência do modelo grande no servidor local | não medida; depende da variante da ResNet e da CPU |
