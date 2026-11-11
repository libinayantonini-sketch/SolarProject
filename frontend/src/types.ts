export type Label = "LIMPO" | "MODERADO" | "SEVERO";
export const LABELS: Label[] = ["LIMPO", "MODERADO", "SEVERO"];

/** Quem classificou: o ESP32 (decide a bomba) ou o modelo grande no servidor (nunca aciona a bomba). */
export type Engine = "esp32" | "server";
export const ENGINE_NAME: Record<Engine, string> = { esp32: "ESP32", server: "Servidor" };

export interface Analysis {
  id: number;
  engine: Engine;
  image_url: string;
  original_filename: string;
  classification: Label;
  final_label: Label;
  human_label: Label | null;
  confidence: number;
  probs: Record<string, number> | null;
  low_confidence: boolean;
  needs_review: boolean;
  cleaning_activated: boolean;
  pump_duration_ms: number;
  pump_reason: string | null;
  model_version: string | null;
  inference_ms: number | null;
  round_trip_ms: number | null;
  width: number;
  height: number;
  created_at: string;
  acao_sugerida: string;
}

export interface EngineInfo {
  disponivel: boolean;
  classes: Label[] | null;
  input_size: number | null;
  aciona_bomba: boolean;
  versao?: string | null;
  motivo: string | null;
}

export interface Config {
  engines: Record<Engine, EngineInfo>;
  upload_max_side: number;
  jpeg_quality: number;
  max_upload_mb: number;
  low_confidence_threshold: number;
  weather: boolean;
  ia_gemini: boolean;
  admin_protegido: boolean;
}

export interface DeviceStatus {
  configured: boolean;
  online: boolean;
  latency_ms?: number;
  error?: string;
  info?: { model_version?: string; device?: string; input_size?: number };
}

export interface Stats {
  total: number;
  por_rotulo: Record<Label, number>;
  para_revisao: number;
  revisadas: number;
  por_motor: Record<Engine, number>;
  limpezas_acionadas: number;
  tempo_total_bomba_ms: number;
  confianca_media: number | null;
  inferencia_media_ms: number | null;
  ultima_analise: string | null;
  serie_diaria: ({ dia: string } & Record<Label, number>)[];
}

export interface AskResult {
  filtro_texto: string;
  total: number;
  analises: Analysis[];
  resumo: string;
  fonte: "gemini" | "regras";
}

export interface Filters {
  engine: Engine | "";
  labels: Label[];
  needs_review: boolean;
  cleaning_activated: boolean;
}

export interface WeatherAdvice {
  disponivel: boolean;
  nivel: "limpar_agora" | "avaliar" | "adiar" | "indisponivel" | "desativado";
  titulo: string;
  mensagem: string;
  observacoes: string[];
  chuva_24h_passadas_mm?: number;
  chuva_24h_proximas_mm?: number;
  prob_max_24h?: number | null;
  limiares?: { fraca_mm: number; forte_mm: number };
  desatualizado?: boolean;
  atualizado_em?: string | null;
  fonte: string;
  aviso: string;
}
