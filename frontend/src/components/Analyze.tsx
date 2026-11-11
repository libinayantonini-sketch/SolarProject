import { useEffect, useRef, useState } from "react";
import { api, ApiError } from "../api";
import { prepareImage } from "../lib/image";
import { LABEL_STYLE, pct, seconds } from "../lib/format";
import type { Analysis, Config, Engine } from "../types";
import { ENGINE_NAME, LABELS } from "../types";
import { LabelBadge } from "./LabelBadge";
import { WeatherCard } from "./WeatherCard";

type Phase = "idle" | "preparing" | "analyzing";

export function Analyze({ config, onDone }: { config: Config; onDone: () => void }) {
  const [file, setFile] = useState<File | Blob | null>(null);
  const [name, setName] = useState("foto.jpg");
  const [preview, setPreview] = useState<string | null>(null);
  const [engine, setEngine] = useState<Engine>(config.engines.esp32.disponivel || !config.engines.server.disponivel ? "esp32" : "server");
  const [pump, setPump] = useState(true);
  const [phase, setPhase] = useState<Phase>("idle");
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<Analysis | null>(null);
  const [blocked, setBlocked] = useState(false);
  const input = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (!file) { setPreview(null); return; }
    const u = URL.createObjectURL(file);
    setPreview(u);
    return () => URL.revokeObjectURL(u);
  }, [file]);

  const choose = (f: File | undefined) => {
    if (!f) return;
    setFile(f); setName(f.name || "foto.jpg"); setResult(null); setError(null);
  };

  const send = async () => {
    if (!file) return;
    setError(null); setResult(null);
    try {
      setPhase("preparing");
      const small = await prepareImage(file, config.upload_max_side, config.jpeg_quality);
      setPhase("analyzing");
      const r = await api.analyze(small, name, engine === "esp32" && pump, engine);
      setResult(r.analise); setBlocked(r.bomba_bloqueada_por_falta_de_chave);
      onDone();
    } catch (e) {
      setError(e instanceof ApiError || e instanceof Error ? e.message : "Erro inesperado.");
    } finally {
      setPhase("idle");
    }
  };

  const busy = phase !== "idle";
  return (
    <div className="space-y-4">
    {config.weather && <WeatherCard />}
    <div className="grid gap-4 md:grid-cols-2">
      <section className="card space-y-3" aria-label="Enviar foto">
        <h2 className="text-lg font-semibold">1. Escolha a foto do painel</h2>
        <div
          onDragOver={(e) => e.preventDefault()}
          onDrop={(e) => { e.preventDefault(); choose(e.dataTransfer.files[0]); }}
          className="flex min-h-[220px] items-center justify-center overflow-hidden rounded-xl border-2 border-dashed border-stone-300 bg-stone-100 dark:border-stone-700 dark:bg-stone-800"
        >
          {preview ? <img src={preview} alt="Pré-visualização da foto escolhida" className="max-h-72 w-full object-contain" />
            : <p className="px-4 text-center text-stone-500">Arraste uma imagem aqui, ou use os botões abaixo</p>}
        </div>
        <input ref={input} data-testid="file-input" type="file" accept="image/*" capture="environment" className="sr-only" id="file"
          onChange={(e) => { choose(e.target.files?.[0]); e.target.value = ""; }} />
        <div className="flex flex-wrap gap-2">
          <label htmlFor="file" className="btn btn-ghost cursor-pointer">📷 Tirar foto / escolher arquivo</label>
        </div>
        <fieldset className="space-y-2" disabled={busy}>
          <legend className="mb-1 text-sm font-medium">Onde analisar</legend>
          <div className="grid gap-2 sm:grid-cols-2" role="radiogroup" aria-label="Onde analisar">
            {(["esp32", "server"] as const).map((e) => {
              const info = config.engines[e];
              return (
                <label key={e} className={`flex min-h-[44px] cursor-pointer items-start gap-2 rounded-xl border p-3 text-sm ${engine === e ? "border-amber-500 bg-amber-50 dark:bg-amber-950" : "border-stone-300 dark:border-stone-700"} ${info.disponivel ? "" : "cursor-not-allowed opacity-60"}`}>
                  <input type="radio" name="engine" value={e} checked={engine === e} disabled={!info.disponivel} onChange={() => setEngine(e)} className="mt-1 h-4 w-4 accent-amber-500" />
                  <span>
                    <strong>{e === "esp32" ? "ESP32, na hora" : "Modelo grande, no servidor"}</strong>
                    <span className="block text-xs text-stone-500">
                      {info.disponivel
                        ? e === "esp32" ? "Classifica e pode acionar a bomba." : `Análise mais robusta${info.versao ? ` (${info.versao})` : ""}. Não aciona a bomba.`
                        : `Indisponível${info.motivo ? `: ${info.motivo}` : ""}`}
                    </span>
                  </span>
                </label>
              );
            })}
          </div>
        </fieldset>
        {engine === "esp32" && (
          <label className="flex min-h-[44px] items-center gap-3">
            <input type="checkbox" checked={pump} onChange={(e) => setPump(e.target.checked)} className="h-5 w-5 accent-amber-500" />
            <span>Permitir acionar a bomba (só se o resultado for SEVERO)</span>
          </label>
        )}
        <p className="text-xs text-stone-500">A foto será reduzida para no máximo {config.upload_max_side} px no seu navegador; o servidor ajusta o tamanho para o modelo escolhido.</p>
        <button className="btn btn-primary w-full" disabled={!file || busy || !config.engines[engine].disponivel} onClick={send}>
          {phase === "preparing" ? "Preparando a imagem…" : phase === "analyzing" ? `${ENGINE_NAME[engine]} analisando…` : "2. Analisar"}
        </button>
        {error && <p role="alert" className="rounded-lg bg-red-100 p-3 text-sm text-red-900 dark:bg-red-950 dark:text-red-200">{error}</p>}
      </section>

      <section className="card" aria-label="Resultado" aria-live="polite">
        <h2 className="mb-3 text-lg font-semibold">Resultado</h2>
        {busy && <div className="flex items-center gap-3 py-10 text-stone-500"><span className="h-5 w-5 animate-spin rounded-full border-2 border-amber-500 border-t-transparent" />{phase === "analyzing" ? `Aguardando o ${ENGINE_NAME[engine]}…` : "Preparando…"}</div>}
        {!busy && !result && <p className="py-10 text-stone-500">O resultado aparece aqui.</p>}
        {!busy && result && <ResultView a={result} blocked={blocked} />}
      </section>
    </div>
    </div>
  );
}

export function ResultView({ a, blocked = false }: { a: Analysis; blocked?: boolean }) {
  return (
    <div className="space-y-4" data-testid="result">
      <div className="flex flex-wrap items-center gap-3">
        <LabelBadge label={a.classification} big />
        <span className="text-lg">confiança <strong>{pct(a.confidence)}</strong></span>
      </div>
      <p className="text-stone-600 dark:text-stone-300">{LABEL_STYLE[a.classification].desc}.</p>
      {a.needs_review && <p className="rounded-lg bg-amber-100 p-3 text-sm text-amber-900 dark:bg-amber-950 dark:text-amber-200">Confiança baixa: peça uma revisão humana antes de agir.</p>}
      {a.probs && (
        <div className="space-y-1.5" aria-label="Probabilidades por classe">
          {LABELS.filter((l) => l in (a.probs ?? {})).map((l) => (          /* só as classes que esse modelo tem (o do ESP32 pode ter 2) */
            <div key={l} className="flex items-center gap-2 text-sm">
              <span className="w-24">{l}</span>
              <div className="h-3 flex-1 overflow-hidden rounded-full bg-stone-200 dark:bg-stone-800">
                <div className="h-full rounded-full" style={{ width: pct(a.probs?.[l] ?? 0), background: LABEL_STYLE[l].solid }} />
              </div>
              <span className="w-10 text-right tabular-nums">{pct(a.probs?.[l] ?? 0)}</span>
            </div>
          ))}
        </div>
      )}
      <div className={`rounded-xl p-3 ${a.cleaning_activated ? "bg-sky-100 text-sky-900 dark:bg-sky-950 dark:text-sky-100" : "bg-stone-100 dark:bg-stone-800"}`}>
        <p className="font-semibold">{a.cleaning_activated ? `💧 Bomba acionada por ${seconds(a.pump_duration_ms)}` : a.engine === "server" ? "Análise do servidor: sem bomba" : "Bomba não acionada"}</p>
        {a.pump_reason && <p className="text-sm">{a.pump_reason}</p>}
        {blocked && <p className="text-sm font-medium">A bomba ficou bloqueada: informe a chave de administrador (botão 🔒 no topo).</p>}
      </div>
      <dl className="grid grid-cols-2 gap-x-4 gap-y-1 text-sm text-stone-600 dark:text-stone-400">
        <dt>Analisado por</dt><dd className="text-right">{ENGINE_NAME[a.engine ?? "esp32"]}</dd>
        <dt>Inferência</dt><dd className="text-right tabular-nums">{a.inference_ms ?? "—"} ms</dd>
        <dt>{a.engine === "server" ? "Tempo total" : "Ida e volta total"}</dt><dd className="text-right tabular-nums">{a.round_trip_ms ?? "—"} ms</dd>
        <dt>Modelo</dt><dd className="truncate text-right">{a.model_version ?? "—"}</dd>
      </dl>
    </div>
  );
}
