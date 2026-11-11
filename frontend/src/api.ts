import type { Analysis, AskResult, Config, DeviceStatus, Engine, Filters, Label, Stats, WeatherAdvice } from "./types";

let adminKey = "";
try { adminKey = sessionStorage.getItem("adminKey") ?? ""; } catch { /* sem storage: segue sem chave */ }

export const getAdminKey = () => adminKey;
export function setAdminKey(k: string) {
  adminKey = k;
  try { sessionStorage.setItem("adminKey", k); } catch { /* ignora */ }
}

export class ApiError extends Error {
  constructor(public status: number, message: string) { super(message); }
}

async function call<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers);
  if (adminKey) headers.set("X-API-Key", adminKey);
  let res: Response;
  try {
    res = await fetch(path, { ...init, headers });
  } catch {
    throw new ApiError(0, "Sem conexão com o servidor. Confira se o backend está no ar e se você está na mesma rede.");
  }
  if (!res.ok) {
    let detail = `Erro ${res.status}`;
    try { const j = await res.json(); if (typeof j.detail === "string") detail = j.detail; else if (Array.isArray(j.detail)) detail = j.detail.map((d: { msg: string }) => d.msg).join("; "); } catch { /* corpo não é JSON */ }
    throw new ApiError(res.status, detail);
  }
  return res.status === 204 ? (undefined as T) : ((await res.json()) as T);
}

const json = (body: unknown): RequestInit => ({ method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });

export const api = {
  config: () => call<Config>("/api/config"),
  deviceStatus: () => call<DeviceStatus>("/api/devices/status"),
  stats: () => call<Stats>("/api/stats"),
  weather: () => call<WeatherAdvice>("/api/weather/advice"),
  analyze: (blob: Blob, name: string, pump: boolean, engine: Engine = "esp32") => {
    const fd = new FormData();
    fd.append("file", blob, name);
    fd.append("pump", String(pump));
    fd.append("engine", engine);
    return call<{ analise: Analysis; bomba_bloqueada_por_falta_de_chave: boolean }>("/api/analyze", { method: "POST", body: fd });
  },
  list: (f: Filters, limit = 24, offset = 0) => {
    const q = new URLSearchParams({ limit: String(limit), offset: String(offset) });
    f.labels.forEach((l) => q.append("labels", l));
    if (f.engine) q.set("engine", f.engine);
    if (f.needs_review) q.set("needs_review", "true");
    if (f.cleaning_activated) q.set("cleaning_activated", "true");
    return call<{ total: number; itens: Analysis[] }>(`/api/analyses?${q}`);
  },
  relabel: (id: number, label: Label | null) => call<Analysis>(`/api/analyses/${id}/label`, { ...json({ label }), method: "PATCH" }),
  remove: (id: number) => call<void>(`/api/analyses/${id}`, { method: "DELETE" }),
  /** Baixa o zip de fotos revisadas (pastas por classe + labels.csv) para retreinar. Exige a chave de administrador. */
  exportTraining: async (onlyReviewed: boolean): Promise<Blob> => {
    let res: Response;
    try {
      res = await fetch(`/api/export/training.zip?only_reviewed=${onlyReviewed}`, { headers: adminKey ? { "X-API-Key": adminKey } : {} });
    } catch {
      throw new ApiError(0, "Sem conexão com o servidor.");
    }
    if (!res.ok) {
      let detail = `Erro ${res.status}`;
      try { const j = await res.json(); if (typeof j.detail === "string") detail = j.detail; } catch { /* sem corpo JSON */ }
      throw new ApiError(res.status, detail);
    }
    return res.blob();
  },
  ask: (question: string) => call<AskResult>("/api/assistant/ask", json({ question })),
  explain: (question: string) => call<{ texto: string; fonte: string; aviso: string }>("/api/assistant/explain", json({ question })),
};
