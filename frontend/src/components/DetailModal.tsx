import { useEffect, useState } from "react";
import { api, ApiError, getAdminKey } from "../api";
import { prepareImage } from "../lib/image";
import { when } from "../lib/format";
import type { Analysis, Config, Label } from "../types";
import { ENGINE_NAME, LABELS } from "../types";
import { LabelBadge } from "./LabelBadge";
import { ResultView } from "./Analyze";

export function DetailModal({ a, config, onClose, onChanged }: { a: Analysis; config: Config; onClose: () => void; onChanged: () => void }) {
  const [cur, setCur] = useState(a);
  const [msg, setMsg] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    const k = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", k);
    return () => window.removeEventListener("keydown", k);
  }, [onClose]);

  const run = async (fn: () => Promise<void>) => {
    setBusy(true); setMsg(null);
    try { await fn(); } catch (e) { setMsg(e instanceof ApiError ? e.message : "Erro inesperado."); } finally { setBusy(false); }
  };

  const relabel = (l: Label | null) => run(async () => { setCur(await api.relabel(cur.id, l)); onChanged(); });
  const remove = () => run(async () => {
    if (!window.confirm("Apagar esta análise e a imagem? Não dá para desfazer.")) return;
    await api.remove(cur.id); onChanged(); onClose();
  });
  // "Imagem de reserva": reenvia uma foto já guardada, sem câmera. Útil se a câmera falhar na apresentação.
  const reanalyze = () => run(async () => {
    const blob = await (await fetch(cur.image_url)).blob();
    const small = await prepareImage(blob, config.upload_max_side, config.jpeg_quality);
    const r = await api.analyze(small, cur.original_filename || "reanalise.jpg", false, cur.engine ?? "esp32");
    setCur(r.analise); onChanged();
    setMsg("Reanalisado (bomba desativada nesta repetição). Uma nova análise foi criada no histórico.");
  });

  return (
    <div role="dialog" aria-modal="true" aria-label={`Análise ${cur.id}`} className="fixed inset-0 z-30 flex items-end justify-center bg-black/60 p-0 sm:items-center sm:p-4" onClick={onClose}>
      <div className="card max-h-[92vh] w-full max-w-3xl overflow-y-auto rounded-b-none sm:rounded-b-2xl" onClick={(e) => e.stopPropagation()}>
        <div className="mb-3 flex items-center justify-between">
          <h2 className="text-lg font-semibold">Análise #{cur.id} · {when(cur.created_at)}</h2>
          <button className="btn btn-ghost" onClick={onClose} aria-label="Fechar">✕</button>
        </div>
        <div className="grid gap-4 sm:grid-cols-2">
          <img src={cur.image_url} alt={`Foto da análise ${cur.id}`} className="w-full rounded-xl bg-stone-200 object-contain dark:bg-stone-800" />
          <div className="space-y-3">
            <ResultView a={cur} />
            {cur.human_label && <p className="text-sm">Corrigido por pessoa para <LabelBadge label={cur.human_label} /> ({ENGINE_NAME[cur.engine ?? "esp32"]} disse {cur.classification}).</p>}
          </div>
        </div>
        <div className="mt-4 space-y-2 border-t border-stone-200 pt-3 dark:border-stone-800">
          <p className="text-sm font-medium">Revisão humana {getAdminKey() ? "" : "(requer chave de administrador, se configurada)"}</p>
          <div className="flex flex-wrap gap-2">
            {LABELS.map((l) => <button key={l} className="chip" aria-pressed={cur.final_label === l && !!cur.human_label} disabled={busy} onClick={() => relabel(l)}>É {l}</button>)}
            {cur.human_label && <button className="chip" disabled={busy} onClick={() => relabel(null)}>Remover correção</button>}
          </div>
          <div className="flex flex-wrap gap-2 pt-1">
            <button className="btn btn-ghost" disabled={busy} onClick={reanalyze}>↻ Reanalisar esta foto</button>
            <button className="btn btn-ghost text-red-700 dark:text-red-300" disabled={busy} onClick={remove}>Apagar</button>
          </div>
          {msg && <p role="alert" className="text-sm text-amber-800 dark:text-amber-300">{msg}</p>}
        </div>
      </div>
    </div>
  );
}
