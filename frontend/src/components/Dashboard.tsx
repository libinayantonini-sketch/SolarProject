import { useEffect, useState } from "react";
import { Bar, BarChart, CartesianGrid, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { api } from "../api";
import { LABEL_STYLE, pct, seconds } from "../lib/format";
import type { Stats } from "../types";
import { LABELS } from "../types";

function Tile({ title, value, hint }: { title: string; value: string; hint?: string }) {
  return (
    <div className="card">
      <p className="text-sm text-stone-500">{title}</p>
      <p className="text-3xl font-bold tabular-nums">{value}</p>
      {hint && <p className="text-xs text-stone-500">{hint}</p>}
    </div>
  );
}

export function Dashboard({ refreshKey }: { refreshKey: number }) {
  const [s, setS] = useState<Stats | null>(null);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    let alive = true;
    const load = () => api.stats().then((v) => alive && (setS(v), setErr(null))).catch((e: Error) => alive && setErr(e.message));
    void load();
    const t = setInterval(() => { if (!document.hidden) void load(); }, 10000);
    return () => { alive = false; clearInterval(t); };
  }, [refreshKey]);

  if (err) return <p role="alert" className="text-red-700 dark:text-red-300">{err}</p>;
  if (!s) return <p className="text-stone-500">Carregando…</p>;
  if (s.total === 0) return <p className="card text-stone-500">Ainda não há análises. Envie a primeira foto na aba “Analisar”.</p>;

  const data = s.serie_diaria.map((d) => ({ ...d, dia: d.dia.slice(8) + "/" + d.dia.slice(5, 7) }));
  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <Tile title="Análises" value={String(s.total)} hint={`${s.revisadas} revisadas · ESP32 ${s.por_motor.esp32} / servidor ${s.por_motor.server}`} />
        <Tile title="Limpezas acionadas" value={String(s.limpezas_acionadas)} hint={`bomba ligada por ${seconds(s.tempo_total_bomba_ms)} no total`} />
        <Tile title="Para revisar" value={String(s.para_revisao)} hint="confiança baixa, sem revisão" />
        <Tile title="Confiança média" value={pct(s.confianca_media)} hint={s.inferencia_media_ms != null ? `inferência média ${s.inferencia_media_ms.toFixed(0)} ms` : undefined} />
      </div>
      <div className="grid grid-cols-3 gap-3">
        {LABELS.map((l) => (
          <div key={l} className={`card ${LABEL_STYLE[l].bg}`}>
            <p className={`text-sm font-semibold ${LABEL_STYLE[l].text}`}>{LABEL_STYLE[l].icon} {l}</p>
            <p className="text-3xl font-bold tabular-nums">{s.por_rotulo[l]}</p>
          </div>
        ))}
      </div>
      <section className="card" aria-label="Análises por dia">
        <h2 className="mb-2 font-semibold">Análises por dia (últimos 14 dias)</h2>
        <div className="h-64">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={data} margin={{ left: -20, right: 8, top: 8 }}>
              <CartesianGrid strokeDasharray="3 3" strokeOpacity={0.25} />
              <XAxis dataKey="dia" tick={{ fontSize: 12 }} interval="preserveStartEnd" />
              <YAxis allowDecimals={false} tick={{ fontSize: 12 }} />
              <Tooltip />
              <Legend />
              {LABELS.map((l) => <Bar key={l} dataKey={l} stackId="a" fill={LABEL_STYLE[l].solid} isAnimationActive={false} />)}
            </BarChart>
          </ResponsiveContainer>
        </div>
      </section>
    </div>
  );
}
