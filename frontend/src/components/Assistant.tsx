import { useState } from "react";
import { api } from "../api";
import type { Analysis, AskResult, Config } from "../types";
import { AnalysisCard } from "./AnalysisCard";
import { DetailModal } from "./DetailModal";

const EXAMPLES = ["fotos sujas de hoje", "análises que precisam de revisão", "quando a bomba foi acionada?", "painéis limpos da última semana"];

export function Assistant({ config, onChanged }: { config: Config; onChanged: () => void }) {
  const [q, setQ] = useState("");
  const [mode, setMode] = useState<"buscar" | "duvida">("buscar");
  const [res, setRes] = useState<AskResult | null>(null);
  const [info, setInfo] = useState<{ texto: string; fonte: string; aviso: string } | null>(null);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [open, setOpen] = useState<Analysis | null>(null);

  const go = async (text: string) => {
    if (text.trim().length < 2) return;
    setBusy(true); setErr(null); setRes(null); setInfo(null);
    try {
      if (mode === "buscar") setRes(await api.ask(text)); else setInfo(await api.explain(text));
    } catch (e) { setErr(e instanceof Error ? e.message : "Erro inesperado."); } finally { setBusy(false); }
  };

  return (
    <div className="space-y-4">
      <div className="card space-y-3">
        <div className="flex flex-wrap gap-2" role="group" aria-label="Modo">
          <button className="chip" aria-pressed={mode === "buscar"} onClick={() => setMode("buscar")}>Buscar nas análises</button>
          <button className="chip" aria-pressed={mode === "duvida"} onClick={() => setMode("duvida")}>Tirar dúvida sobre soiling</button>
          <span className="ml-auto text-xs text-stone-500">{config.ia_gemini ? "IA: Gemini ativo" : "IA não configurada: usando regras simples"}</span>
        </div>
        <form className="flex gap-2" onSubmit={(e) => { e.preventDefault(); void go(q); }}>
          <label htmlFor="q" className="sr-only">Pergunta</label>
          <input id="q" value={q} onChange={(e) => setQ(e.target.value)} maxLength={300} placeholder={mode === "buscar" ? "Ex.: fotos sujas de hoje" : "Ex.: por que a poeira reduz a geração?"}
            className="min-h-[44px] flex-1 rounded-xl border border-stone-300 bg-transparent px-3 dark:border-stone-700" />
          <button className="btn btn-primary" disabled={busy}>{busy ? "…" : "Perguntar"}</button>
        </form>
        {mode === "buscar" && <div className="flex flex-wrap gap-2">{EXAMPLES.map((x) => <button key={x} className="chip" onClick={() => { setQ(x); void go(x); }}>{x}</button>)}</div>}
      </div>
      {err && <p role="alert" className="text-red-700 dark:text-red-300">{err}</p>}
      {res && (
        <section className="space-y-3" aria-live="polite">
          <div className="card">
            <p>{res.resumo}</p>
            <p className="mt-2 text-xs text-stone-500">Filtro aplicado: {res.filtro_texto} · {res.total} resultado(s) · resumo por {res.fonte === "gemini" ? "Gemini" : "regras (sem IA)"}</p>
          </div>
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6">{res.analises.map((a) => <AnalysisCard key={a.id} a={a} onOpen={setOpen} />)}</div>
        </section>
      )}
      {info && (
        <section className="card" aria-live="polite">
          <p className="whitespace-pre-line">{info.texto}</p>
          <p className="mt-2 text-xs text-stone-500">{info.aviso} Fonte: {info.fonte === "gemini" ? "Gemini" : "sem IA"}.</p>
        </section>
      )}
      {open && <DetailModal a={open} config={config} onClose={() => setOpen(null)} onChanged={onChanged} />}
    </div>
  );
}
