# Firmware do ESP32

Passo a passo completo, riscos e checklist de bancada: [`docs/04_FIRMWARE_ESP32.md`](../../docs/04_FIRMWARE_ESP32.md).

Resumo:

```bash
cp src/secrets.example.h src/secrets.h                 # preencha Wi-Fi (e DEVICE_KEY, se usar)
python ../../ai-model/conversion/tflite_to_header.py ../../ai-model/models/current/model.tflite src/model_data.h
pio run -t upload && pio device monitor                # o Monitor Serial mostra o IP e a RAM usada pelo modelo
g++ -std=c++17 -I src test/test_pump_policy.cpp -o /tmp/pp && /tmp/pp     # teste da política da bomba (no computador)
```

Por padrão `PUMP_PIN=2` (LED da placa): valide TODA a lógica com o LED antes de ligar a bomba.
