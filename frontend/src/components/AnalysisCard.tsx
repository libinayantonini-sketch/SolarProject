import { pct, when } from "../lib/format";
import type { Analysis } from "../types";
import { ENGINE_NAME } from "../types";
import { LabelBadge } from "./LabelBadge";

export function AnalysisCard({ a, onOpen }: { a: Analysis; onOpen: (a: Analysis) => void }) {
  return (
    <button onClick={() => onOpen(a)} className="card flex flex-col gap-2 p-3 text-left transition hover:border-amber-400 focus:outline-none focus-visible:ring-2 focus-visible:ring-amber-500" data-testid="analysis-card">
      <img src={a.image_url} alt={`Foto ${a.id}: ${a.final_label}`} loading="lazy" className="aspect-square w-full rounded-lg bg-stone-200 object-cover dark:bg-stone-800" />
      <div className="flex items-center justify-between gap-2">
        <LabelBadge label={a.final_label} />
        <span className="text-sm tabular-nums">{pct(a.confidence)}</span>
      </div>
      <div className="flex flex-wrap items-center gap-x-2 text-xs text-stone-500">
        <span>{when(a.created_at)}</span>
        <span className="rounded bg-stone-200 px-1.5 dark:bg-stone-800">{ENGINE_NAME[a.engine ?? "esp32"]}</span>
        {a.cleaning_activated && <span title="Bomba acionada">💧</span>}
        {a.needs_review && <span className="font-semibold text-amber-700 dark:text-amber-300">revisar</span>}
        {a.human_label && <span>✎ corrigido</span>}
      </div>
    </button>
  );
}
