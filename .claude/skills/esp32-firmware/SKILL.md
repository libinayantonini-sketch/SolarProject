---
name: esp32-firmware
description: Firmware do ESP32 (PlatformIO, TFLite Micro, JPEGDEC, bomba) e checklist de bancada. Use ao compilar, gravar, depurar memória ou mexer na segurança da bomba.
---
# Firmware (firmware/esp32/)

**Não foi compilado nem testado em hardware.** Espere ajustes de API das bibliotecas na primeira compilação. Só `src/pump_policy.h` foi testado (g++).

Passos: `secrets.h` (copie do exemplo) → treinar → `tflite_to_header.py` gera `model_data.h` → `pio run -t upload` → `pio device monitor` (115200): lê o IP e `arena usada`.

Regras de segurança (não enfraqueça): pino da bomba **desligado na 1ª instrução do `setup`**; só SEVERO; confiança ≥ `CONF_THRESHOLD`; duração ≤ 60 s; cooldown; bomba ocupada recusa; desligamento por relógio em `pumpTick()` (fora do HTTP); sem Wi‑Fi → desliga; `pump=0` nunca aciona.
Qualquer mudança na política vai **primeiro** em `pump_policy.h` + `test/test_pump_policy.cpp` (`g++ -std=c++17 -I src test/test_pump_policy.cpp`), depois no simulador (`tools/esp32_simulator/server.py`).

Memória (esp32dev, sem PSRAM): buffer JPEG 32 KB + frame 18 KB + arena (96 KB) + Wi‑Fi. Se `AllocateTensors` falhar: aumente `TENSOR_ARENA_BYTES` ou reduza a rede. Troque `AllOpsResolver` por `MicroMutableOpResolver` com os operadores do `model_card.json` para economizar flash.
Consistência: `INPUT_SIZE`, `CONF_THRESHOLD` e `MODEL_VERSION` em `config.h` devem bater com `model_card.json`.
Circuito: nunca bomba direto no GPIO; MOSFET/relé + diodo + fonte separada com GND comum. Valide com LED (`PUMP_PIN=2`) antes. Detalhes e checklist: `docs/04_FIRMWARE_ESP32.md`.
