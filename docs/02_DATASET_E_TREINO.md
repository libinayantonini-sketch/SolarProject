# 02 · Dataset e treino

## Dataset
Roboflow Universe: <https://universe.roboflow.com/amr-fph1m/solar-panel-dust-and-soiling> (≈2,3 mil imagens, classes `Clean`,
`Dusty`, `Soiled`, licença CC BY 4.0 — **cite a fonte** no trabalho). Não conseguimos confirmar o **tipo do projeto** (classificação
ou detecção). O treino precisa de **um rótulo por imagem**:
- Exporte como **classificação**: "Folder Structure" ou "Multi-label CSV". Exports de detecção (YOLO/COCO) são recusados por `prepare_data.py`.
- Baixar exige conta/chave do Roboflow (`pip install roboflow`; veja o botão "Download Dataset" do projeto). Não executamos o download.

**Confira o mapeamento** olhando ~20 imagens de cada classe. Se `Dusty` for na prática sujeira pesada, use `--class-map "Dusty=SEVERO"`.

## Suas fotos extras
Pastas `LIMPO/`, `MODERADO/`, `SEVERO/`, fotografadas **do jeito que o ESP32/celular vai ver** (mesma câmera, distância e luz). Isso pesa
mais que quantidade: o dataset público tem outra câmera, outro ângulo e outro tipo de sujeira. Recomendação: separe um conjunto
**só seu** para o teste final.

## Passo a passo
```bash
python -m venv .venv && .venv/bin/pip install -r ai-model/requirements.txt      # TensorFlow CPU
cd ai-model/training
python prepare_data.py --roboflow ../data/roboflow --extra ../data/minhas_fotos --out ../data/manifest.csv
#   --class-map "Dusty=SEVERO"   --resplit (ignora as partições do Roboflow, sorteia 70/15/15 estratificado)
python train.py --manifest ../data/manifest.csv --size 96 --epochs 40 --out ../models/run1
cp -r ../models/run1 ../models/current
python ../conversion/tflite_to_header.py ../models/current/model.tflite ../../firmware/esp32/src/model_data.h
```
`prepare_data.py` remove duplicatas exatas (SHA‑256) entre partições — a mesma foto em treino e teste inflaria a acurácia — e imprime a contagem por partição/classe.

## O que o treino faz
Rede depthwise‑separable pequena, entrada 96×96 RGB, normalização `Rescaling` dentro do modelo, aumento de dados (giros, deslocamento,
brilho, contraste), pesos de classe, Adam com cosseno, seleção do melhor epoch por **F1 macro na validação**. As imagens passam pelo mesmo
resize + JPEG que o backend usa em produção. Ao final exporta **TFLite int8** e mede o teste **no modelo int8** (o que roda no ESP32).

Saídas em `models/<run>/`: `model.tflite`, `model.keras`, `labels.json`, `model_card.json` (versão, tamanho, quantização, operadores),
`metrics.json` (matriz de confusão, F1 por classe, cobertura por confiança).

## Como ler o resultado
- Olhe a **matriz de confusão**, não só a acurácia. O erro mais caro aqui é `SEVERO` previsto como `LIMPO` (não limpa) e `LIMPO` previsto como `SEVERO` (gasta água à toa).
- Se a acurácia int8 cair muito frente à float, a quantização está ruim: aumente os dados de calibração.
- O limiar de 0,60 é um ponto de partida; ajuste com `selecao_por_confianca` de `metrics.json`.
- **Nenhum número de acurácia foi medido ainda com fotos reais.** O único treino rodado usou imagens sintéticas para testar o pipeline.

## Se o modelo não couber no ESP32
`model_card.json` mostra `tflite_bytes` e a lista de operadores. A RAM real (tensor arena) só se mede no dispositivo: o firmware imprime
`arena_used_bytes()` no boot. Reduza filtros em `build_model` (`train.py`) ou a entrada (`--size 64`, alterando também `INPUT_SIZE` no backend e no firmware).
