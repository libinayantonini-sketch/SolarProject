import { useCallback, useEffect, useState } from "react";
import { api, ApiError, getAdminKey } from "../api";
import type { Analysis, Config, Filters } from "../types";
import { ENGINE_NAME, LABELS } from "../types";
import { AnalysisCard } from "./AnalysisCard";
import { DetailModal } from "./DetailModal";

const PAGE = 24;

export function History({ config, refreshKey, onChanged }: { config: Config; refreshKey: number; onChanged: () => void }) {
  const [f, setF] = useState<Filters>({ engine: "", labels: [], needs_review: false, cleaning_activated: false });
  const [items, setItems] = useState<Analysis[]>([]);
  const [total, setTotal] = useState(0);
  const [open, setOpen] = useState<Analysis | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async (offset = 0) => {
    setLoading(true);
    try {
      const r = await api.list(f, PAGE, offset);
      setItems((prev) => (offset ? [...prev, ...r.itens] : r.itens));
      setTotal(r.total); setErr(null);
    } catch (e) { setErr(e instanceof Error ? e.message : "Falha ao carregar."); } finally { setLoading(false); }
  }, [f]);

  useEffect(() => { void load(0); }, [load, refreshKey]);

  const [exportMsg, setExportMsg] = useState<string | null>(null);

  const exportZip = async () => {
    setExportMsg(null);
    try {
      const blob = await api.exportTraining(true);
      const a = document.createElement("a");
      a.href = URL.createObjectURL(blob);
      a.download = "fotos-para-retreino.zip";
      a.click();
      URL.revokeObjectURL(a.href);
    } catch (e) {
      setExportMsg(e instanceof ApiError ? e.message : "Falha ao exportar.");
    }
  };

  const toggle = (l: (typeof LABELS)[number]) => setF((p) => ({ ...p, labels: p.labels.includes(l) ? p.labels.filter((x) => x !== l) : [...p.labels, l] }));

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-2" role="group" aria-label="Filtros">
        {LABELS.map((l) => <button key={l} className="chip" aria-pressed={f.labels.includes(l)} onClick={() => toggle(l)}>{l}</button>)}
        <button className="chip" aria-pressed={f.needs_review} onClick={() => setF((p) => ({ ...p, needs_review: !p.needs_review }))}>Para revisar</button>
        <button className="chip" aria-pressed={f.cleaning_activated} onClick={() => setF((p) => ({ ...p, cleaning_activated: !p.cleaning_activated }))}>💧 Bomba acionada</button>
        {(["esp32", "server"] as const).map((e) => (
          <button key={e} className="chip" aria-pressed={f.engine === e} onClick={() => setF((p) => ({ ...p, engine: p.engine === e ? "" : e }))}>{ENGINE_NAME[e]}</button>
        ))}
        <span className="ml-auto text-sm text-stone-500">{total} análise(s)</span>
      </div>
      <div className="flex flex-wrap items-center gap-2">
        <button className="btn btn-ghost" onClick={exportZip} title="Zip com as fotos corrigidas por pessoas, em pastas por classe, para retreinar os modelos">⬇ Exportar fotos revisadas (retreino)</button>
        {!getAdminKey() && <span className="text-xs text-stone-500">Se o servidor tiver chave de administrador, informe-a no botão 🔒 do topo.</span>}
        {exportMsg && <span role="alert" className="text-sm text-amber-800 dark:text-amber-300">{exportMsg}</span>}
      </div>
      {err && <p role="alert" className="text-red-700 dark:text-red-300">{err}</p>}
      {!loading && items.length === 0 && !err && <p className="card text-stone-500">Nenhuma análise com esses filtros ainda.</p>}
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-5">
        {items.map((a) => <AnalysisCard key={a.id} a={a} onOpen={setOpen} />)}
      </div>
      {items.length < total && <button className="btn btn-ghost w-full" disabled={loading} onClick={() => load(items.length)}>Carregar mais</button>}
      {open && <DetailModal a={open} config={config} onClose={() => setOpen(null)} onChanged={() => { onChanged(); void load(0); }} />}
    </div>
  );
}
