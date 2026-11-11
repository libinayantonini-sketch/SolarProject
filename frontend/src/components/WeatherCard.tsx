import { useCallback, useEffect, useState } from "react";
import { api } from "../api";
import type { WeatherAdvice } from "../types";

const STYLE: Record<string, { box: string; icon: string }> = {
  limpar_agora: { box: "border-green-300 bg-limpo-soft dark:border-green-900 dark:bg-limpo-darksoft", icon: "☀️" },
  avaliar: { box: "border-amber-300 bg-moderado-soft dark:border-amber-900 dark:bg-moderado-darksoft", icon: "🌦️" },
  adiar: { box: "border-sky-300 bg-sky-100 dark:border-sky-900 dark:bg-sky-950", icon: "🌧️" },
};

/** Recomendação de chuva ANTES de analisar. Só informa; nunca liga nem bloqueia a bomba. */
export function WeatherCard() {
  const [w, setW] = useState<WeatherAdvice | null>(null);
  const [busy, setBusy] = useState(false);

  const load = useCallback(() => {
    setBusy(true);
    api.weather().then(setW).catch(() => setW(null)).finally(() => setBusy(false));
  }, []);

  useEffect(() => {
    load();
    const t = setInterval(() => { if (!document.hidden) load(); }, 30 * 60 * 1000);
    return () => clearInterval(t);
  }, [load]);

  if (!w) return <section className="card text-sm text-stone-500" aria-label="Recomendação de chuva">{busy ? "Consultando a previsão de chuva…" : "Recomendação de chuva indisponível."}</section>;
  const s = STYLE[w.nivel] ?? { box: "border-stone-300 bg-stone-100 dark:border-stone-700 dark:bg-stone-800", icon: "☁️" };

  return (
    <section aria-label="Recomendação de chuva" data-testid="weather" className={`rounded-2xl border p-4 ${s.box}`}>
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wide text-stone-600 dark:text-stone-300">Antes de limpar: chuva</p>
          <h2 className="text-lg font-semibold"><span aria-hidden>{s.icon}</span> {w.titulo}</h2>
        </div>
        <button className="btn btn-ghost min-h-[36px] py-1" onClick={load} disabled={busy}>{busy ? "…" : "↻ Atualizar"}</button>
      </div>
      <p className="mt-1">{w.mensagem}</p>
      {w.observacoes.map((o) => <p key={o} className="mt-1 text-sm">• {o}</p>)}
      {w.disponivel && (
        <p className="mt-2 text-sm text-stone-700 dark:text-stone-300">
          Últimas 24 h: <strong>{w.chuva_24h_passadas_mm} mm</strong> · Próximas 24 h: <strong>{w.chuva_24h_proximas_mm} mm</strong>
          {w.prob_max_24h != null && <> · chance máxima {w.prob_max_24h}%</>}
          {w.desatualizado && <> · <em>dados desatualizados (sem conexão)</em></>}
        </p>
      )}
      <p className="mt-2 text-xs text-stone-600 dark:text-stone-400">
        {w.aviso}{w.limiares ? ` Fraca ≥ ${w.limiares.fraca_mm} mm, forte ≥ ${w.limiares.forte_mm} mm em 24 h.` : ""}{" "}
        <a className="underline" href="https://open-meteo.com/" target="_blank" rel="noreferrer">{w.fonte}</a>
      </p>
    </section>
  );
}
