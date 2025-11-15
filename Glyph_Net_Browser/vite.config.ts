// vite.config.ts
import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react-swc";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), "");

  // radio-node (existing)
  const radioHttp = env.VITE_BACKEND_URL || "http://127.0.0.1:8787";
  const radioWs   = radioHttp.replace(/^http/i, "ws");

  // KG backend (new) – your Node/Express on port 3000
  const kgHttp = env.VITE_KG_URL || "http://localhost:3000";

  // IMPORTANT: put "/api/kg" BEFORE the generic "/api"
  const proxy: Record<string, any> = {
    // ── Knowledge Graph endpoints → :3000
    "/api/kg": { target: kgHttp, changeOrigin: true },

    // ── Everything else under /api → radio node
    "/api":        { target: radioHttp, changeOrigin: true },

    // existing proxies
    "/ws":         { target: radioWs,   ws: true, changeOrigin: true },
    "/bridge":     { target: radioHttp, changeOrigin: true },
    "/containers": { target: radioHttp, changeOrigin: true },
    "/health":     { target: radioHttp, changeOrigin: true },

    "^/radio/qkd": {
      target: radioHttp, changeOrigin: true,
      rewrite: (p: string) => p.replace(/^\/radio\/qkd/, "/qkd"),
    },
    "^/radio": {
      target: radioHttp, changeOrigin: true, ws: true,
      rewrite: (p: string) => p.replace(/^\/radio/, ""),
    },
    "^/qkd": { target: radioHttp, changeOrigin: true },
  };

  return {
    plugins: [react()],
    resolve: { alias: { "@": path.resolve(__dirname, "src") } },
    server: { host: true, port: 5173, strictPort: true, cors: true, proxy },
    preview: { host: "0.0.0.0", port: 5173 },
    build: { outDir: "dist" },
  };
});