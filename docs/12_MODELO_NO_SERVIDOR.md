# 12 · Modelo grande no servidor (ONNX)

Além do modelo pequeno do ESP32, o backend pode rodar um **modelo grande** (ex.: ResNet) para uma análise mais robusta.
São **dois modos**, escolhidos no front para cada foto. Não existe modo "comparar".

| | `esp32` | `server` |
| --- | --- | --- |
| Onde roda | no ESP32 (Wi‑Fi local) | no backend (localhost), ONNX Runtime na CPU |
| Aciona a bomba | sim, pela política do firmware | **nunca** |
| Classes | `ESP32_CLASSES` (padrão 3; pode ser `LIMPO,SEVERO`) | as do `labels.json` (3: LIMPO, MODERADO, SEVERO) |
| Tamanho de entrada | `ESP32_INPUT_SIZE` (padrão 96) | `SERVER_INPUT_SIZE`, ou o `input_size` do `model_card.json` |

O dataset **não** faz parte do repositório: só o modelo já treinado (pesos) entra, e as fotos novas voltam pelo sistema (exportação abaixo).

## O que a equipe entrega: uma pasta com 3 arquivos
Coloque em `models/server/` (ou aponte `SERVER_MODEL_DIR`). Em Docker, essa pasta é montada em `/models/server`.

| Arquivo | Conteúdo |
| --- | --- |
| `model.onnx` | entrada `(N, 3, H, W)` float32 (NCHW, RGB); saída `(N, K)` com **logits** (ou probabilidades, se o card disser `"output": "probs"`) |
| `labels.json` | classes na ordem das saídas, ex.: `["LIMPO","MODERADO","SEVERO"]`. Precisa incluir LIMPO e SEVERO; K tem que ser igual ao número de classes |
| `model_card.json` | `{"version": "resnet18-v1", "input_size": 224, "mean": [0.485,0.456,0.406], "std": [0.229,0.224,0.225], "output": "logits"}` |

- `version` aparece em cada análise (rastreabilidade). `mean`/`std` e o tamanho vêm do card para treino e inferência não divergirem
  (se faltarem, usa-se ImageNet e 224).
- Trocar de modelo = trocar os 3 arquivos e reiniciar o backend. Nenhum código muda.
- Sem a pasta (ou com arquivo inválido) o backend **sobe normalmente**: o modo servidor aparece como indisponível, com o motivo, e o modo ESP32 segue.
- Exportar de PyTorch (exemplo): `torch.onnx.export(model.eval(), torch.randn(1,3,224,224), "model.onnx", input_names=["input"], output_names=["logits"], dynamic_axes={"input": {0: "batch"}, "logits": {0: "batch"}})`.

## Variáveis (ver `.env.example`)
| Variável | Padrão | Para quê |
| --- | --- | --- |
| `ESP32_INPUT_SIZE` | 96 | lado da foto enviada ao ESP32 (igual ao treino/firmware). `INPUT_SIZE` ainda é aceito |
| `ESP32_CLASSES` | `LIMPO,MODERADO,SEVERO` | classes do modelo do ESP32. Se o ESP32 devolver outra, a API responde 502 e não grava |
| `SERVER_MODEL_DIR` | `models/server` | pasta do modelo grande |
| `SERVER_INPUT_SIZE` | 0 | lado da entrada do modelo grande; 0 = usar o card |
| `UPLOAD_MAX_SIDE` | 512 | maior lado da foto que o front envia e que fica guardada |

O front envia uma foto de até `UPLOAD_MAX_SIDE` px. O backend guarda essa foto e gera, a partir dela, a versão de cada modelo
(estica para quadrado, como no treino). Por isso os tamanhos de entrada podem mudar sem mexer no front.

## Retreino com as fotos novas
No Histórico, corrija o rótulo das fotos (precisa da chave de administrador, se configurada) e use **Exportar fotos revisadas**
(`GET /api/export/training.zip`). O zip tem uma pasta por classe e um `labels.csv`, no formato que
`ai-model/training/prepare_data.py --extra <pasta>` já lê. As fotos saem no tamanho guardado; cada treino as redimensiona.
Se o ESP32 usar só 2 classes, ignore ou mapeie a pasta `MODERADO` ao treinar o modelo dele.

## Se o ESP32 passar a ter 2 classes
Já feito: `ESP32_CLASSES=LIMPO,SEVERO` no backend (validação e `/api/config`).
**Ainda assumem 3 classes** (ajustar quando a decisão for tomada, junto com o retreino):
`ai-model/training/labels.py` e `train.py` (saída da rede, pesos de classe), `prepare_data.py`, `tools/esp32_simulator/classifier.py`
e `tflite_engine.py` (`LABELS` fixo), o firmware (`firmware/esp32/src`, vetor de rótulos e política da bomba) e o `labels.json` do modelo do ESP32.

## O que foi e o que não foi testado
Testado automaticamente: carga do ONNX, os dois modos, bomba nunca acionada no modo servidor, modelo ausente/inválido, classes do ESP32,
tamanho configurável, exportação, migração de banco antigo, e o fluxo no navegador. O modelo usado nos testes é **sintético** (média de cor),
não uma ResNet. **Não medidos:** acurácia e latência de uma ResNet real, e a comparação com o modelo do ESP32.
