import type { Label } from "../types";

export const LABEL_STYLE: Record<Label, { text: string; bg: string; solid: string; icon: string; desc: string }> = {
  LIMPO: { text: "text-limpo dark:text-limpo-dark", bg: "bg-limpo-soft dark:bg-limpo-darksoft", solid: "#16a34a", icon: "✓", desc: "Painel limpo" },
  MODERADO: { text: "text-moderado dark:text-moderado-dark", bg: "bg-moderado-soft dark:bg-moderado-darksoft", solid: "#ca8a04", icon: "!", desc: "Poeira moderada" },
  SEVERO: { text: "text-severo dark:text-severo-dark", bg: "bg-severo-soft dark:bg-severo-darksoft", solid: "#dc2626", icon: "✕", desc: "Sujeira severa" },
};

export const pct = (v: number | null | undefined) => (v == null ? "—" : `${(v * 100).toFixed(0)}%`);

export function when(iso: string): string {
  const d = new Date(iso);
  return d.toLocaleString("pt-BR", { day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit" });
}

export function seconds(ms: number): string {
  return `${(ms / 1000).toFixed(ms % 1000 === 0 ? 0 : 1)} s`;
}
