# 05 · Protocolo backend ↔ ESP32

O ESP32 é **servidor HTTP** na rede local. O backend é o cliente. Implementações: firmware (`main.cpp`), simulador (`tools/esp32_simulator/server.py`),
cliente (`backend/app/services/esp32.py`) e contrato de validação (`backend/app/schemas/analysis.py`). **Mudou um, mude todos.**

## `GET /` — o dispositivo está vivo?
Resposta 200 JSON (campos além de `status` são informativos):
```json
{"status":"ok","device":"esp32","model_version":"tiny_cnn-96","input_size":96,"uptime_s":123,"pump_busy":false,"free_heap":180000,"threshold":0.60}
```

## `POST /upload?pump=0|1` — classificar uma foto
Cabeçalhos: `Content-Type: image/jpeg`, `Content-Length` (obrigatório), `X-Device-Key` (se `DEVICE_KEY` estiver definido no firmware).
Corpo: JPEG **exatamente `INPUT_SIZE×INPUT_SIZE`**, ≤ 32 KB. `pump=0` proíbe acionar a bomba nesta requisição.

Resposta 200:
```json
{"classification":"SEVERO","confidence":0.9412,
 "probs":{"LIMPO":0.01,"MODERADO":0.05,"SEVERO":0.94},
 "cleaning_activated":true,"pump_duration_ms":5000,"reason":"SEVERO com confianca suficiente",
 "inference_ms":812,"model_version":"tiny_cnn-96-20261105"}
```
| Campo | Obrigatório | Regra (o backend valida; fora disto vira 502) |
| --- | --- | --- |
| `classification` | sim | `LIMPO`, `MODERADO` ou `SEVERO` |
| `confidence` | sim | 0 a 1 |
| `probs` | não | por classe |
| `cleaning_activated` | não (padrão false) | a bomba foi ligada |
| `pump_duration_ms` | não (padrão 0) | 0 a 60 000 |
| `reason`, `inference_ms`, `model_version` | não | texto ≤ 200, inteiro ≥ 0, texto ≤ 80 |

Erros do dispositivo (JSON `{"error": "..."}`): 400 corpo vazio · 401 chave errada · 404 rota · 408 corpo incompleto · 413 grande demais · 415 não é JPEG (simulador) · 422 JPEG inválido ou tamanho errado · 500 falha na inferência.

## Pré-processamento (tem de bater com o treino)
O front/backend entregam JPEG `S×S` (esticado, sem recorte, qualidade 85). O firmware decodifica para RGB, e para cada canal faz
`q = round(pixel / scale) + zero_point` com `scale`/`zero_point` do tensor de entrada (int8). A normalização para [−1, 1] já está dentro do modelo.
A saída é int8; `prob = (q − zero_point) × scale`.

## Testando à mão
```bash
PYTHONPATH=tools python -m esp32_simulator.server --demo-model --port 8081      # ESP32 simulado
curl http://localhost:8081/
curl -X POST "http://localhost:8081/upload?pump=0" -H "Content-Type: image/jpeg" --data-binary @foto96.jpg
```
O simulador aplica a mesma política da bomba (cooldown em segundos via `--cooldown-s`, duração via `--pump-ms`).
Ele **não prova** que o modelo cabe no ESP32 nem reproduz o tempo de inferência real.
