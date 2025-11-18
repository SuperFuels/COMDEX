// vite.config.ts
import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react-swc";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), "");

  // radio-node (Express)
  const radioHttp = env.VITE_BACKEND_URL || "http://127.0.0.1:8787";
  const radioWs   = radioHttp.replace(/^http/i, "ws");

  // FastAPI (GlyphNet read endpoints)
  const fastApiHttp = env.VITE_FASTAPI_URL || "http://localhost:8080";
  // We are NOT using FastAPI WS from the browser for now.

  // Node KG
  const kgHttp = env.VITE_KG_URL || "http://localhost:3000";

  // Specific routes BEFORE generic ones
  const proxy: Record<string, any> = {
    // ── Knowledge Graph (KG) → Node KG (:3000)
    "/api/kg": { target: kgHttp, changeOrigin: true },

    // ── GlyphNet read endpoints → FastAPI (:8080)
    "/api/glyphnet/thread":      { target: fastApiHttp, changeOrigin: true },
    "/api/glyphnet/health":      { target: fastApiHttp, changeOrigin: true },
    "/api/glyphnet/logs":        { target: fastApiHttp, changeOrigin: true },
    "/api/glyphnet/simulations": { target: fastApiHttp, changeOrigin: true },
    "/api/glyphnet/ws-test":     { target: fastApiHttp, changeOrigin: true },

    // ── WS for GlyphNet fanout → radio-node (so RF mock + bridge show up)
    "/ws/glyphnet": { target: radioWs, ws: true, changeOrigin: true },

    // ✅ Dev RF mock tools (now hit radio-node)
    "/dev": { target: radioHttp, changeOrigin: true },

    // ── Everything else under /api → radio-node (keeps /api/glyphnet/tx on radio)
    "/api": { target: radioHttp, changeOrigin: true },

    // radio-node extras (keep AFTER /ws/glyphnet so it doesn't catch it)
    "/ws/rflink":  { target: radioWs, ws: true, changeOrigin: true },
    "/ws/ghx":     { target: radioWs, ws: true, changeOrigin: true },
    "/ws":         { target: radioWs, ws: true, changeOrigin: true },
    "/bridge":     { target: radioHttp, changeOrigin: true },
    "/containers": { target: radioHttp, changeOrigin: true },
    "/health":     { target: radioHttp, changeOrigin: true },

    "^/radio/qkd": {
      target: radioHttp,
      changeOrigin: true,
      rewrite: (p: string) => p.replace(/^\/radio\/qkd/, "/qkd"),
    },
    "^/radio": {
      target: radioHttp,
      changeOrigin: true,
      ws: true,
      rewrite: (p: string) => p.replace(/^\/radio/, ""),
    },
    "^/qkd": { target: radioHttp, changeOrigin: true },
  };

  return {
    plugins: [react()],
    resolve: { alias: { "@": path.resolve(__dirname, "src") } },
    server: {
      host: true,
      port: 5173,
      strictPort: true,
      cors: true,
      proxy,
    },
    preview: { host: "0.0.0.0", port: 5173 },
    build: { outDir: "dist" },
  };
});