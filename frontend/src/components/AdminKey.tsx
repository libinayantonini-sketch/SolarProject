import { useState } from "react";
import { getAdminKey, setAdminKey } from "../api";

export function AdminKey({ protectedApi }: { protectedApi: boolean }) {
  const [open, setOpen] = useState(false);
  const [v, setV] = useState(getAdminKey());
  if (!protectedApi) return null;
  return (
    <div className="relative">
      <button className="btn btn-ghost" onClick={() => setOpen(!open)} aria-expanded={open}>
        {getAdminKey() ? "🔓 Admin ativo" : "🔒 Admin"}
      </button>
      {open && (
        <div className="card absolute right-0 z-20 mt-2 w-72 space-y-2">
          <label className="block text-sm font-medium" htmlFor="adminkey">Chave de administrador</label>
          <input id="adminkey" type="password" value={v} onChange={(e) => setV(e.target.value)}
            className="w-full rounded-lg border border-stone-300 bg-transparent px-3 py-2 dark:border-stone-700" />
          <p className="text-xs text-stone-500">Necessária para acionar a bomba, corrigir rótulos e apagar. Fica só nesta aba.</p>
          <button className="btn btn-primary w-full" onClick={() => { setAdminKey(v); setOpen(false); }}>Salvar</button>
        </div>
      )}
    </div>
  );
}
