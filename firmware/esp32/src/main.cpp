// Soiling Detection — firmware do ESP32 (esp32dev, sem PSRAM).
// Servidor HTTP simples: GET / (status) e POST /upload?pump=0|1 (JPEG 96x96 -> inferência -> decisão da bomba).
// Protocolo: docs/05_PROTOCOLO_ESP32.md. Decisões de segurança: docs/04_FIRMWARE_ESP32.md.
//
// ATENÇÃO: este código foi escrito e revisado, mas NÃO foi compilado nem executado em hardware no ambiente de
// construção. As APIs das bibliotecas (TensorFlowLite_ESP32, JPEGDEC) mudam entre versões: espere pequenos ajustes
// na primeira compilação. A política da bomba (pump_policy.h) foi testada no computador.
#include <Arduino.h>
#include <WiFi.h>
#include <JPEGDEC.h>
#include <TensorFlowLite_ESP32.h>
#include <tensorflow/lite/micro/all_ops_resolver.h>   // se faltar RAM/flash, troque por MicroMutableOpResolver (lista no model_card.json)
#include <tensorflow/lite/micro/micro_interpreter.h>
#include <tensorflow/lite/schema/schema_generated.h>

#include "config.h"
#include "model_data.h"   // gerado por ai-model/conversion/tflite_to_header.py
#include "pump_policy.h"
#include "secrets.h"      // copie de secrets.example.h

#ifndef PUMP_PIN
#define PUMP_PIN 2
#endif
#ifndef PUMP_ACTIVE_LEVEL
#define PUMP_ACTIVE_LEVEL HIGH
#endif
constexpr int PUMP_IDLE_LEVEL = (PUMP_ACTIVE_LEVEL == HIGH) ? LOW : HIGH;

static const char *LABEL_NAMES[3] = {"LIMPO", "MODERADO", "SEVERO"};

WiFiServer server(80);
static uint8_t body[MAX_BODY_BYTES];                    // JPEG recebido (buffer fixo: sem malloc no caminho quente)
static uint16_t frame565[INPUT_SIZE * INPUT_SIZE];      // imagem decodificada (RGB565)
alignas(16) static uint8_t tensor_arena[TENSOR_ARENA_BYTES];

JPEGDEC jpeg;
tflite::MicroInterpreter *interpreter = nullptr;
TfLiteTensor *input = nullptr, *output = nullptr;
PumpPolicy policy{CONF_THRESHOLD, PUMP_DURATION_MS, PUMP_MAX_MS, PUMP_COOLDOWN_MS};
uint32_t pump_off_at = 0;
bool pump_on = false;

// ---------------------------------------------------------------- bomba
void pumpOff() {
  digitalWrite(PUMP_PIN, PUMP_IDLE_LEVEL);
  if (pump_on) { pump_on = false; policy.finished(millis()); }
}

void pumpOn(uint32_t ms) {
  policy.started();
  pump_on = true;
  pump_off_at = millis() + ms;
  digitalWrite(PUMP_PIN, PUMP_ACTIVE_LEVEL);
}

// Chamada em todo loop(): o desligamento NÃO depende do fluxo HTTP.
void pumpTick() {
  if (pump_on && (int32_t)(millis() - pump_off_at) >= 0) pumpOff();
}

// ---------------------------------------------------------------- imagem
int drawCb(JPEGDRAW *d) {
  for (int y = 0; y < d->iHeight; y++) {
    int fy = d->y + y;
    if (fy >= INPUT_SIZE) break;
    for (int x = 0; x < d->iWidth; x++) {
      int fx = d->x + x;
      if (fx < INPUT_SIZE) frame565[fy * INPUT_SIZE + fx] = d->pPixels[y * d->iWidth + x];
    }
  }
  return 1;
}

// 0 = ok; senão código HTTP de erro e mensagem
int decodeJpeg(size_t len, const char **err) {
  if (!jpeg.openRAM(body, (int)len, drawCb)) { *err = "JPEG invalido"; return 422; }
  if (jpeg.getWidth() != INPUT_SIZE || jpeg.getHeight() != INPUT_SIZE) {
    *err = "imagem deve ter " "96x96 (INPUT_SIZE)"; jpeg.close(); return 422;
  }
  jpeg.setPixelType(RGB565_LITTLE_ENDIAN);
  int ok = jpeg.decode(0, 0, 0);
  jpeg.close();
  if (!ok) { *err = "falha ao decodificar"; return 422; }
  return 0;
}

// RGB565 -> int8 quantizado com a escala/zero-point lidos do próprio modelo.
void fillInput() {
  const float s = input->params.scale;
  const int zp = input->params.zero_point;
  int8_t *dst = input->data.int8;
  for (int i = 0; i < INPUT_SIZE * INPUT_SIZE; i++) {
    uint16_t p = frame565[i];
    uint8_t r = ((p >> 11) & 0x1F), g = ((p >> 5) & 0x3F), b = (p & 0x1F);
    float rgb[3] = {(float)((r << 3) | (r >> 2)), (float)((g << 2) | (g >> 4)), (float)((b << 3) | (b >> 2))};
    for (int c = 0; c < 3; c++) {
      int q = (int)lroundf(rgb[c] / s) + zp;
      dst[i * 3 + c] = (int8_t)(q < -128 ? -128 : q > 127 ? 127 : q);
    }
  }
}

// ---------------------------------------------------------------- HTTP
void sendJson(WiFiClient &c, int code, const char *json) {
  c.printf("HTTP/1.1 %d OK\r\nContent-Type: application/json\r\nContent-Length: %u\r\nConnection: close\r\n\r\n%s", code,
           (unsigned)strlen(json), json);
}

void sendError(WiFiClient &c, int code, const char *msg) {
  char buf[160];
  snprintf(buf, sizeof(buf), "{\"error\":\"%s\"}", msg);
  sendJson(c, code, buf);
}

void handleClient(WiFiClient &c) {
  c.setTimeout(3000);
  String reqLine = c.readStringUntil('\n');
  reqLine.trim();
  int contentLength = 0;
  String key = "";
  while (c.connected()) {                               // cabeçalhos
    String h = c.readStringUntil('\n');
    h.trim();
    if (h.length() == 0) break;
    String low = h; low.toLowerCase();
    if (low.startsWith("content-length:")) contentLength = h.substring(15).toInt();
    if (low.startsWith("x-device-key:")) { key = h.substring(13); key.trim(); }
  }

  if (reqLine.startsWith("GET / ")) {
    char buf[256];
    snprintf(buf, sizeof(buf),
             "{\"status\":\"ok\",\"device\":\"esp32\",\"model_version\":\"%s\",\"input_size\":%d,\"uptime_s\":%lu,"
             "\"pump_busy\":%s,\"free_heap\":%u,\"threshold\":%.2f}",
             MODEL_VERSION, INPUT_SIZE, (unsigned long)(millis() / 1000), pump_on ? "true" : "false", ESP.getFreeHeap(), CONF_THRESHOLD);
    sendJson(c, 200, buf);
    return;
  }
  if (!reqLine.startsWith("POST /upload")) { sendError(c, 404, "nao encontrado"); return; }
  if (strlen(DEVICE_KEY) > 0 && key != DEVICE_KEY) { sendError(c, 401, "X-Device-Key invalida"); return; }
  if (contentLength <= 0) { sendError(c, 400, "corpo vazio"); return; }
  if ((size_t)contentLength > MAX_BODY_BYTES) { sendError(c, 413, "corpo grande demais"); return; }
  bool allowPump = reqLine.indexOf("pump=1") >= 0 || reqLine.indexOf("pump=") < 0;

  size_t got = 0;                                       // lê exatamente Content-Length bytes
  uint32_t t0 = millis();
  while (got < (size_t)contentLength && millis() - t0 < 5000) {
    int n = c.read(body + got, contentLength - got);
    if (n > 0) got += n; else delay(1);
  }
  if (got != (size_t)contentLength) { sendError(c, 408, "corpo incompleto"); return; }

  const char *err = nullptr;
  int code = decodeJpeg(got, &err);
  if (code) { sendError(c, code, err); return; }

  fillInput();
  uint32_t i0 = millis();
  if (interpreter->Invoke() != kTfLiteOk) { sendError(c, 500, "falha na inferencia"); return; }
  uint32_t inf_ms = millis() - i0;

  float probs[3];
  int best = 0;
  for (int i = 0; i < 3; i++) {
    probs[i] = (output->data.int8[i] - output->params.zero_point) * output->params.scale;
    if (probs[i] > probs[best]) best = i;
  }
  PumpDecision d = policy.decide((Label)best, probs[best], allowPump, millis());
  if (d.activate) pumpOn(d.duration_ms);

  char buf[420];
  snprintf(buf, sizeof(buf),
           "{\"classification\":\"%s\",\"confidence\":%.4f,\"probs\":{\"LIMPO\":%.4f,\"MODERADO\":%.4f,\"SEVERO\":%.4f},"
           "\"cleaning_activated\":%s,\"pump_duration_ms\":%lu,\"reason\":\"%s\",\"inference_ms\":%lu,\"model_version\":\"%s\"}",
           LABEL_NAMES[best], probs[best], probs[0], probs[1], probs[2], d.activate ? "true" : "false",
           (unsigned long)(d.activate ? d.duration_ms : 0), d.reason, (unsigned long)inf_ms, MODEL_VERSION);
  sendJson(c, 200, buf);
  Serial.printf("[%s %.2f] bomba=%d inferencia=%lums\n", LABEL_NAMES[best], probs[best], d.activate, (unsigned long)inf_ms);
}

// ---------------------------------------------------------------- setup / loop
void setup() {
  pinMode(PUMP_PIN, OUTPUT);
  digitalWrite(PUMP_PIN, PUMP_IDLE_LEVEL);              // PRIMEIRA coisa: bomba desligada
  Serial.begin(115200);

  const tflite::Model *model = tflite::GetModel(g_model_data);
  if (model->version() != TFLITE_SCHEMA_VERSION) { Serial.println("modelo com versao de schema incompativel"); while (true) delay(1000); }
  static tflite::AllOpsResolver resolver;
  static tflite::MicroInterpreter static_interpreter(model, resolver, tensor_arena, TENSOR_ARENA_BYTES);
  interpreter = &static_interpreter;
  if (interpreter->AllocateTensors() != kTfLiteOk) { Serial.println("AllocateTensors falhou: aumente TENSOR_ARENA_BYTES"); while (true) delay(1000); }
  input = interpreter->input(0);
  output = interpreter->output(0);
  Serial.printf("modelo ok. arena usada: %u de %u bytes\n", (unsigned)interpreter->arena_used_bytes(), (unsigned)TENSOR_ARENA_BYTES);

  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASS);
  Serial.print("conectando ao Wi-Fi");
  while (WiFi.status() != WL_CONNECTED) { delay(400); Serial.print('.'); }
  Serial.printf("\nIP: %s  (coloque em ESP32_URL=http://%s no backend)\n", WiFi.localIP().toString().c_str(), WiFi.localIP().toString().c_str());
  server.begin();
}

void loop() {
  pumpTick();
  if (WiFi.status() != WL_CONNECTED) { pumpOff(); WiFi.reconnect(); delay(1000); return; }   // sem rede: bomba desligada
  WiFiClient c = server.available();
  if (c) { handleClient(c); c.stop(); }
}
