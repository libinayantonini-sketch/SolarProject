# 04 · Firmware e hardware do ESP32

> **Estado:** o código em `firmware/esp32/` foi escrito e revisado, mas **não foi compilado nem rodado em hardware** neste projeto.
> Só a política da bomba (`pump_policy.h`) foi testada (no computador). As bibliotecas mudam de versão: espere ajustes na primeira compilação.

## Placa e limites
O projeto usa `esp32dev` no PlatformIO (normalmente ESP32‑WROOM‑32): ~520 KB de SRAM no total, **~320 KB utilizáveis** e **sem PSRAM**.
Não presuma que qualquer modelo caiba. Orçamento (a medir!): buffer do JPEG recebido 32 KB + imagem decodificada 18 KB (96×96 RGB565)
+ tensor arena (padrão 96 KB) + Wi‑Fi/pilha do sistema. O modelo em si (~30 KB) fica na flash.
**Como provar que cabe:** grave, abra o Monitor Serial (115200) e leia `modelo ok. arena usada: X de Y bytes`. Se `AllocateTensors` falhar, aumente `TENSOR_ARENA_BYTES` (`config.h`) ou reduza a rede.

## Passo a passo
1. `cp firmware/esp32/src/secrets.example.h firmware/esp32/src/secrets.h` e preencha Wi‑Fi (e `DEVICE_KEY`, igual a `ESP32_KEY` do backend).
2. Treine o modelo (`02_DATASET_E_TREINO.md`) e gere `model_data.h`:
   `python ai-model/conversion/tflite_to_header.py ai-model/models/current/model.tflite firmware/esp32/src/model_data.h`
3. Confira que `INPUT_SIZE` em `config.h` = `input_size` do `model_card.json`.
4. `cd firmware/esp32 && pio run -t upload && pio device monitor`. O Monitor mostra o IP: ponha em `ESP32_URL` do backend.
5. Teste do protocolo sem o front: `curl http://IP/` e `curl -X POST "http://IP/upload?pump=0" -H "Content-Type: image/jpeg" --data-binary @foto96.jpg`.

## Como o firmware funciona
`setup()`: **bomba desligada primeiro** → carrega o modelo → conecta ao Wi‑Fi → abre o servidor na porta 80.
`loop()`: `pumpTick()` (desliga a bomba pelo relógio, independente do HTTP) → atende um cliente. Em `POST /upload`: lê exatamente
`Content-Length` bytes (≤ 32 KB), decodifica o JPEG (JPEGDEC), exige 96×96, quantiza com a escala/zero‑point lidos do modelo,
`Invoke()`, calcula probabilidades, decide a bomba e responde JSON. O ESP32 fica ligado em espera; só calcula quando recebe foto.

## Segurança da bomba (inegociável)
| Regra | Onde |
| --- | --- |
| Estado inicial **desligado** (1ª instrução do `setup`) | `main.cpp` |
| Só `SEVERO` aciona; `MODERADO`/`LIMPO` nunca | `pump_policy.h` |
| Confiança < 0,60 → não aciona | `pump_policy.h` |
| Duração ≤ `PUMP_MAX_MS` (60 s), mesmo se o valor configurado for maior | `pump_policy.h` |
| Intervalo mínimo entre acionamentos (`PUMP_COOLDOWN_MS`, padrão 60 s; **aumente em uso real**) | `pump_policy.h` |
| Bomba ocupada → recusa novo acionamento | `pump_policy.h` |
| Desligamento garantido pelo tempo, fora do fluxo HTTP | `pumpTick()` |
| Sem Wi‑Fi → bomba desligada | `loop()` |
| Requisição com `pump=0` nunca aciona (usado pelo backend sem chave de admin) | `handleClient` |
Ainda **faltam** (decisão de hardware): sensor de nível/ausência de água (rodar a bomba a seco a danifica), botão físico de parada e watchdog de hardware.

## Circuito
**Nunca ligue a bomba direto ao GPIO.** O pino só comanda um estágio de potência:
```
GPIO (PUMP_PIN) ─ 1 kΩ ─┬─ Gate  MOSFET nível lógico (ex.: IRLZ44N)      Fonte externa (+)──┬── Bomba ──┐
                        └─ 100 kΩ ─ GND (pull-down: bomba off no boot)                    │           │
GND do ESP32 ───────────────────── Source ────────────────────────── GND da fonte ──┐     Diodo 1N5819 │
                                                          Drain ───────────────────────┴────(catodo ao +, anodo ao Drain)
```
Valores são exemplos: dimensione pela tensão/corrente da **sua** bomba. Módulo de relé compatível com 3,3 V também serve. Diodo em antiparalelo
na bomba (carga indutiva) é obrigatório. **Alimentação da bomba separada** da do ESP32, com GND comum. Água longe da eletrônica; use caixa vedada.

## Checklist de bancada (nesta ordem)
1. Compila e conecta; `GET /` responde do computador (**teste de isolamento de clientes**: alguns hotspots de celular impedem que dispositivos se falem).
2. `PUMP_PIN=2` (LED da placa): `SEVERO` acende o LED por 5 s e apaga; `LIMPO`/`MODERADO` não acendem; 2º `SEVERO` seguido é bloqueado.
3. Puxe o cabo Wi‑Fi/desligue o roteador com o LED aceso: deve apagar no tempo certo (pelo relógio).
4. Meça `arena_used_bytes`, tempo de inferência e `free_heap` com 20 fotos seguidas (sem queda contínua de heap).
5. Só então: MOSFET + bomba **sem água**, depois com água, com recipiente.
6. Compare a classificação do ESP32 com a do simulador para as mesmas fotos (devem coincidir, salvo arredondamento).

## Outra câmera?
Nesta versão a foto vem do celular/PC pelo backend. Uma ESP32‑CAM enviando fotos sozinha é outra arquitetura (o ESP32 seria cliente) e **não está implementada**.
