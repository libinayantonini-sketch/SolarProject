#pragma once
// Parâmetros do firmware. Mantenha em sincronia com ai-model/models/current/model_card.json e docs/05_PROTOCOLO_ESP32.md.

constexpr int      INPUT_SIZE          = 96;       // lado da imagem que o modelo espera (model_card.json: input_size)
constexpr size_t   MAX_BODY_BYTES      = 32 * 1024; // buffer fixo na RAM para o JPEG recebido; acima disso: HTTP 413
constexpr size_t   TENSOR_ARENA_BYTES  = 96 * 1024; // ajuste após medir: o firmware imprime arena_used_bytes() no boot
constexpr float    CONF_THRESHOLD      = 0.60f;     // abaixo disso nunca aciona a bomba (model_card.json: low_confidence_threshold)

// Bomba (valores de segurança; o backend também limita a 60 s)
constexpr uint32_t PUMP_DURATION_MS    = 5000;      // quanto tempo a bomba fica ligada em cada acionamento
constexpr uint32_t PUMP_MAX_MS         = 60000;     // teto absoluto, mesmo que o valor acima seja alterado por engano
constexpr uint32_t PUMP_COOLDOWN_MS    = 60000;     // intervalo mínimo entre acionamentos (aumente para uso real)

#define MODEL_VERSION "tiny_cnn-96"                 // texto livre devolvido ao backend; ideal: igual a model_card.json
