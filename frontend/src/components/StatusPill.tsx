import { useEffect, useState } from "react";
import { api } from "../api";
import type { DeviceStatus } from "../types";

export function StatusPill() {
  const [s, setS] = useState<DeviceStatus | null>(null);
  const [lost, setLost] = useState(false);

  useEffect(() => {
    let alive = true;
    const tick = () =>
      api.deviceStatus().then((v) => { if (alive) { setS(v); setLost(false); } }).catch(() => alive && setLost(true));
    tick();
    const t = setInterval(tick, 5000);
    return () => { alive = false; clearInterval(t); };
  }, []);

  let text = "verificando…";
  let dot = "bg-stone-400";
  if (lost) { text = "servidor fora do ar"; dot = "bg-red-500"; }
  else if (s && !s.configured) { text = "ESP32 não configurado"; dot = "bg-amber-500"; }
  else if (s?.online) { text = `ESP32 online · ${s.latency_ms} ms`; dot = "bg-green-500"; }
  else if (s) { text = "ESP32 offline"; dot = "bg-red-500"; }

  return (
    <span role="status" aria-live="polite" className="inline-flex items-center gap-2 rounded-full border border-stone-300 px-3 py-1 text-sm dark:border-stone-700">
      <span className={`h-2.5 w-2.5 rounded-full ${dot}`} aria-hidden />
      <span data-testid="esp-status">{text}</span>
      {s?.info?.device?.includes("simulator") && <span className="rounded bg-amber-200 px-1.5 text-xs font-semibold text-amber-900">simulador</span>}
    </span>
  );
}
