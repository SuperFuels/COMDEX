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
  const radioWs = radioHttp.replace(/^http/i, "ws");

  // FastAPI (GlyphNet read + Photon / AST / Holo endpoints)
  const fastApiHttp = env.VITE_FASTAPI_URL || "http://127.0.0.1:8080";

  // Node KG
  const kgHttp = env.VITE_KG_URL || "http://127.0.0.1:3000";

  // 🔌 SCI Photon IDE (Next.js app)
  const sciHttp = env.VITE_SCI_URL || "http://127.0.0.1:3001";

  const proxy: Record<string, any> = {
    // ── Knowledge Graph (KG) → Node KG (:3000)
    "/api/kg": { target: kgHttp, changeOrigin: true },

    // ── PhotonLang API → FastAPI backend (:8080)
    "/api/photon": { target: fastApiHttp, changeOrigin: true },

    // 🔭 AST / AST Hologram APIs → FastAPI (:8080)
    "/api/ast/hologram": { target: fastApiHttp, changeOrigin: true },
    "/api/ast": { target: fastApiHttp, changeOrigin: true },

    // ✅ Motif compiler API → FastAPI (:8080)
    "/api/motif": { target: fastApiHttp, changeOrigin: true },

    // ── GlyphNet read endpoints → FastAPI (:8080)
    "/api/glyphnet/thread": { target: fastApiHttp, changeOrigin: true },
    "/api/glyphnet/health": { target: fastApiHttp, changeOrigin: true },
    "/api/glyphnet/logs": { target: fastApiHttp, changeOrigin: true },
    "/api/glyphnet/simulations": { target: fastApiHttp, changeOrigin: true },
    "/api/glyphnet/ws-test": { target: fastApiHttp, changeOrigin: true },

    // ✅ Holo / AION memory APIs → FastAPI (:8080)
    "/api/holo": { target: fastApiHttp, changeOrigin: true },

    // ✅ Crystal motif APIs → FastAPI (:8080)
    "/api/crystals": { target: fastApiHttp, changeOrigin: true },

    // ── WS for GlyphNet fanout / GHX → radio-node
    "/ws/glyphnet": { target: radioWs, ws: true, changeOrigin: true },
    "/ws/rflink": { target: radioWs, ws: true, changeOrigin: true },
    "/ws/ghx": { target: radioWs, ws: true, changeOrigin: true },
    "/ws": { target: radioWs, ws: true, changeOrigin: true },

    // ✅ Dev RF mock tools (leave /dev/rf to frontend)
    "^/dev(?!/rf)": { target: radioHttp, changeOrigin: true },

    // 🔁 SCI dev proxy → Next.js SCI app (:3001)
    "/sci": {
      target: sciHttp,
      changeOrigin: true,
      secure: false,
      rewrite: (p: string) => p.replace(/^\/sci/, ""),
    },

    // ── Everything else under /api → radio-node
    "/api": { target: radioHttp, changeOrigin: true },

    // radio-node extras
    "/bridge": { target: radioHttp, changeOrigin: true },
    "/containers": { target: radioHttp, changeOrigin: true },
    "/health": { target: radioHttp, changeOrigin: true },

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