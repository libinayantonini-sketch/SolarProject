import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Em desenvolvimento, /api vai para o backend (uvicorn na porta 8000).
export default defineConfig({
  plugins: [react()],
  server: { host: true, port: 5173, proxy: { "/api": "http://localhost:8000" } },
  build: { outDir: "dist", sourcemap: false },
});
