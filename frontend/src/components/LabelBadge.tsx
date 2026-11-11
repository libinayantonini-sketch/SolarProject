import type { Label } from "../types";
import { LABEL_STYLE } from "../lib/format";

/** Sempre texto + símbolo, nunca só cor (acessibilidade e projetor ruim). */
export function LabelBadge({ label, big = false }: { label: Label; big?: boolean }) {
  const s = LABEL_STYLE[label];
  return (
    <span className={`inline-flex items-center gap-1.5 rounded-full font-bold ${s.bg} ${s.text} ${big ? "px-4 py-2 text-xl" : "px-2.5 py-0.5 text-xs"}`}>
      <span aria-hidden>{s.icon}</span>
      {label}
    </span>
  );
}
