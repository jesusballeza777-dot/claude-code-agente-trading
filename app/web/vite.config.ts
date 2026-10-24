import tailwindcss from "@tailwindcss/vite";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// En desarrollo, /api va al backend local (127.0.0.1:8000). En producción, FastAPI sirve
// la app compilada desde el mismo origen: sin CORS (ADR-015).
export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    host: "127.0.0.1",
    port: 5173,
    proxy: { "/api": "http://127.0.0.1:8000" },
  },
  preview: {
    host: "127.0.0.1",
    port: 4173,
    proxy: { "/api": "http://127.0.0.1:8000" },
  },
  // Sin recursos incrustados como data: URI: la CSP solo permite fuentes e imágenes propias.
  build: { sourcemap: false, chunkSizeWarningLimit: 900, assetsInlineLimit: 0 },
});
