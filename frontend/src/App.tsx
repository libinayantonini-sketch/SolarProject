import { useCallback, useEffect, useState } from "react";
import { api } from "./api";
import type { Config } from "./types";
import { AdminKey } from "./components/AdminKey";
import { Analyze } from "./components/Analyze";
import { Assistant } from "./components/Assistant";
import { Dashboard } from "./components/Dashboard";
import { History } from "./components/History";
import { StatusPill } from "./components/StatusPill";

const TABS = [
  { id: "analisar", label: "Analisar" },
  { id: "historico", label: "Histórico" },
  { id: "painel", label: "Painel" },
  { id: "assistente", label: "Assistente" },
] as const;
type Tab = (typeof TABS)[number]["id"];

export default function App() {
  const [tab, setTab] = useState<Tab>("analisar");
  const [config, setConfig] = useState<Config | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [refresh, setRefresh] = useState(0);
  const bump = useCallback(() => setRefresh((n) => n + 1), []);

  useEffect(() => { api.config().then(setConfig).catch((e: Error) => setErr(e.message)); }, []);

  return (
    <div className="mx-auto max-w-6xl px-4 pb-16">
      <header className="flex flex-wrap items-center justify-between gap-3 py-4">
        <h1 className="text-xl font-bold">☀️ Soiling Detection</h1>
        <div className="flex flex-wrap items-center gap-2">
          <StatusPill />
          {config && <AdminKey protectedApi={config.admin_protegido} />}
        </div>
      </header>
      <nav className="mb-4 flex gap-1 overflow-x-auto rounded-xl bg-stone-200 p-1 dark:bg-stone-800" role="tablist" aria-label="Seções">
        {TABS.map((t) => (
          <button key={t.id} role="tab" aria-selected={tab === t.id} onClick={() => setTab(t.id)}
            className={`min-h-[44px] flex-1 whitespace-nowrap rounded-lg px-4 text-sm font-semibold ${tab === t.id ? "bg-white shadow dark:bg-stone-950" : "text-stone-600 dark:text-stone-300"}`}>
            {t.label}
          </button>
        ))}
      </nav>
      <main>
        {err && <p role="alert" className="card text-red-700 dark:text-red-300">{err}</p>}
        {config && tab === "analisar" && <Analyze config={config} onDone={bump} />}
        {config && tab === "historico" && <History config={config} refreshKey={refresh} onChanged={bump} />}
        {config && tab === "painel" && <Dashboard refreshKey={refresh} />}
        {config && tab === "assistente" && <Assistant config={config} onChanged={bump} />}
      </main>
    </div>
  );
}
