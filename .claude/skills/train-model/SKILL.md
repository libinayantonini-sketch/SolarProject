---
name: train-model
description: Preparar o dataset (Roboflow + fotos extras), treinar o classificador Keras e exportar TFLite int8 para o ESP32. Use ao treinar, avaliar, trocar a rede ou mudar o tamanho de entrada.
---
# Treino (ai-model/)

```bash
.venv/bin/pip install -r ai-model/requirements.txt
cd ai-model/training
python prepare_data.py --roboflow ../data/roboflow --extra ../data/minhas_fotos --out ../data/manifest.csv   # --class-map "Dusty=SEVERO" --resplit
python train.py --manifest ../data/manifest.csv --size 96 --epochs 40 --out ../models/run1
cp -r ../models/run1 ../models/current
python ../conversion/tflite_to_header.py ../models/current/model.tflite ../../firmware/esp32/src/model_data.h
```
- Dataset precisa de **um rótulo por imagem** (exporte do Roboflow como classificação). `Clean/Dusty/Soiled → LIMPO/MODERADO/SEVERO` é **suposição**: confira imagens.
- Duplicatas entre partições são removidas (SHA‑256). Mantenha um teste só com fotos do **seu** painel/câmera.
- O modelo normaliza **dentro** (Rescaling) e recebe RGB 0–255; o resize+JPEG do treino imita o backend. Mude `--size` ⇒ mude `INPUT_SIZE` no backend, no firmware e no `model_card.json`.
- Meça sempre o **int8** (`teste_tflite_int8` em `metrics.json`): é o que roda no ESP32. Olhe a matriz de confusão (SEVERO×LIMPO são os erros caros).
- BatchNorm com `momentum=0.9` de propósito (com poucos passos o padrão 0,99 dá modelo que treina bem e falha na inferência).
- Não prometa acurácia sem ter treinado com dados reais. O único treino rodado até hoje foi sintético.
- Tamanho: `model_card.json` mostra bytes e operadores; a RAM real só se mede no ESP32 (`arena_used_bytes`).
