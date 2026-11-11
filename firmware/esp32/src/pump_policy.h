#pragma once
// Política de segurança da bomba. C++ puro (sem Arduino) para poder ser testado no computador.
// Regras (docs/04_FIRMWARE_ESP32.md): só SEVERO, confiança >= limiar, sem bomba ocupada, respeita intervalo mínimo,
// duração limitada, e a requisição precisa permitir (pump=1). Qualquer dúvida => NÃO aciona.
#include <cstdint>
#include <cstring>

enum class Label : int { LIMPO = 0, MODERADO = 1, SEVERO = 2 };

struct PumpDecision {
  bool     activate;
  uint32_t duration_ms;
  const char *reason;
};

struct PumpPolicy {
  float    threshold;
  uint32_t duration_ms;
  uint32_t max_ms;
  uint32_t cooldown_ms;
  bool     ever_pumped = false;   // evita que "nunca bombeou" seja confundido com millis() pequeno após o boot
  uint32_t last_end_ms = 0;
  bool     busy = false;

  PumpDecision decide(Label label, float confidence, bool allow, uint32_t now_ms) const {
    if (!allow)                         return {false, 0, "bomba desativada nesta requisicao (pump=0)"};
    if (label != Label::SEVERO)         return {false, 0, "so SEVERO aciona a bomba"};
    if (confidence < threshold)         return {false, 0, "confianca baixa: sem acionamento, revisao humana"};
    if (busy)                           return {false, 0, "bomba ocupada"};
    if (ever_pumped && (uint32_t)(now_ms - last_end_ms) < cooldown_ms)
                                        return {false, 0, "intervalo minimo entre acionamentos"};
    uint32_t d = duration_ms > max_ms ? max_ms : duration_ms;
    if (d == 0)                         return {false, 0, "duracao zero"};
    return {true, d, "SEVERO com confianca suficiente"};
  }
  void started() { busy = true; }
  void finished(uint32_t now_ms) { busy = false; ever_pumped = true; last_end_ms = now_ms; }
};
