// Teste nativo da política da bomba: g++ -std=c++17 -I src test/test_pump_policy.cpp && ./a.out   (ou: pio test -e native)
#include <cassert>
#include <cstdio>
#include "pump_policy.h"

int main() {
  PumpPolicy p{0.60f, 5000, 60000, 60000};
  assert(!p.decide(Label::LIMPO, 0.99f, true, 1000).activate);
  assert(!p.decide(Label::MODERADO, 0.99f, true, 1000).activate);
  assert(!p.decide(Label::SEVERO, 0.59f, true, 1000).activate);          // baixa confiança
  assert(!p.decide(Label::SEVERO, 0.99f, false, 1000).activate);         // pump=0
  auto d = p.decide(Label::SEVERO, 0.90f, true, 1000);                   // logo após o boot: deve acionar
  assert(d.activate && d.duration_ms == 5000);
  p.started();
  assert(!p.decide(Label::SEVERO, 0.99f, true, 2000).activate);          // ocupada
  p.finished(6000);
  assert(!p.decide(Label::SEVERO, 0.99f, true, 30000).activate);         // cooldown
  assert(p.decide(Label::SEVERO, 0.99f, true, 66001).activate);          // passou o intervalo
  PumpPolicy big{0.6f, 999999, 60000, 1000};
  assert(big.decide(Label::SEVERO, 0.9f, true, 0).duration_ms == 60000); // teto de segurança
  PumpPolicy wrap{0.6f, 5000, 60000, 60000};
  wrap.finished(0xFFFFFF00u);                                            // virada do millis() (~49 dias)
  assert(!wrap.decide(Label::SEVERO, 0.9f, true, 0xFFFFFF00u + 1000).activate);
  assert(wrap.decide(Label::SEVERO, 0.9f, true, 0xFFFFFF00u + 61000).activate);
  std::puts("pump_policy: ok");
  return 0;
}
