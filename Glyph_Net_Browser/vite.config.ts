// vite.config.ts
import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react-swc";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

type ProxyTarget = {
  target: string;
  ws?: boolean;
  changeOrigin?: boolean;
  secure?: boolean;
  timeout?: number;
  proxyTimeout?: number;
  rewrite?: (path: string) => string;
};

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), "");

  // FastAPI (primary backend)
  // IMPORTANT: default to 8099 (your working local FastAPI in this wirepack run)
  const fastApiHttp = (env.VITE_FASTAPI_URL || "http://127.0.0.1:8099").replace(/\/+$/, "");

  // GX1 (separate service)
  const gx1Http = (env.VITE_GX1_URL || "http://127.0.0.1:8091").replace(/\/+$/, "");

  // Aion module endpoints (your launch script ports)
  const srelHttp = (env.VITE_SREL_URL || "http://127.0.0.1:8001").replace(/\/+$/, "");
  const ralHttp  = (env.VITE_RAL_URL  || "http://127.0.0.1:8002").replace(/\/+$/, "");
  const aqciHttp = (env.VITE_AQCI_URL || "http://127.0.0.1:8004").replace(/\/+$/, "");
  const tcfkHttp = (env.VITE_TCFK_URL || "http://127.0.0.1:8005").replace(/\/+$/, "");
  const rqfsHttp = (env.VITE_RQFS_URL || "http://127.0.0.1:8006").replace(/\/+$/, "");

  // Optional radio-node (Express) — KEEP vars, but DO NOT PROXY ANYTHING TO IT here.
  // (Offline browser only, per your instruction.)
  const radioDisabled = env.VITE_DISABLE_RADIO === "1";
  const radioHttp = (env.VITE_BACKEND_URL || "http://127.0.0.1:8787").replace(/\/+$/, "");
  void radioDisabled; void radioHttp;

  // Node KG + SCI
  const kgHttp  = (env.VITE_KG_URL  || "http://127.0.0.1:3000").replace(/\/+$/, "");
  const sciHttp = (env.VITE_SCI_URL || "http://127.0.0.1:3001").replace(/\/+$/, "");

  const httpProxy = (targetHttp: string): ProxyTarget => ({
    target: targetHttp,
    changeOrigin: true,
    secure: false,
  });

  const wsProxy = (targetHttp: string, rewrite?: (p: string) => string): ProxyTarget => ({
    target: targetHttp,
    ws: true,
    changeOrigin: true,
    secure: false,
    timeout: 120000,
    proxyTimeout: 120000,
    ...(rewrite ? { rewrite } : {}),
  });

  // Aion module servers expose /ws/*, not /api/ws/*
  const dropApiPrefix = (p: string) => p.replace(/^\/api/, "");

  const proxy: Record<string, ProxyTarget | any> = {
    // ─────────────────────────────────────────────────────────────
    // KG (node)
    // ─────────────────────────────────────────────────────────────
    "/api/kg": httpProxy(kgHttp),

    // ─────────────────────────────────────────────────────────────
    // GX1 HTTP APIs (MUST be above catch-all /api)
    // Frontend calls: 5173/api/gx1/... -> gx1Http/api/gx1/...
    // ─────────────────────────────────────────────────────────────
    "/api/gx1": httpProxy(gx1Http),

    // ─────────────────────────────────────────────────────────────
    // FastAPI HTTP APIs (explicit)
    // ─────────────────────────────────────────────────────────────
    "/api/photon": httpProxy(fastApiHttp),
    "/api/ast/hologram": httpProxy(fastApiHttp),
    "/api/ast": httpProxy(fastApiHttp),
    "/api/motif": httpProxy(fastApiHttp),

    "/api/glyphnet/thread": httpProxy(fastApiHttp),
    "/api/glyphnet/health": httpProxy(fastApiHttp),
    "/api/glyphnet/logs": httpProxy(fastApiHttp),
    "/api/glyphnet/simulations": httpProxy(fastApiHttp),
    "/api/glyphnet/ws-test": httpProxy(fastApiHttp),

    "/api/holo": httpProxy(fastApiHttp),
    "/api/crystals": httpProxy(fastApiHttp),

    "/api/wallet": httpProxy(fastApiHttp),
    "/api/mesh": httpProxy(fastApiHttp),
    "/api/gma": httpProxy(fastApiHttp),
    "/api/photon_pay": httpProxy(fastApiHttp),
    "/api/wave": httpProxy(fastApiHttp),
    "/api/glyph_bonds": httpProxy(fastApiHttp),
    "/api/bonds": httpProxy(fastApiHttp),
    "/api/photon_savings": httpProxy(fastApiHttp),
    "/api/escrow": httpProxy(fastApiHttp),
    "/api/transactable_docs": httpProxy(fastApiHttp),

    "/api/chain_sim": httpProxy(fastApiHttp),
    "/api/glyphchain": httpProxy(fastApiHttp),
    "/api/lean": httpProxy(fastApiHttp),

    // ✅ WirePack is served by FastAPI here (NOT radio-node)
    "/api/wirepack": httpProxy(fastApiHttp),

    // ─────────────────────────────────────────────────────────────
    // WebSockets
    // ─────────────────────────────────────────────────────────────
    "/api/ws/qfc": wsProxy(fastApiHttp),
    "/api/ws/containers": wsProxy(fastApiHttp),

    "/api/ws/symatics": wsProxy(srelHttp, dropApiPrefix),
    "/api/ws/analytics": wsProxy(ralHttp, dropApiPrefix),
    "/api/ws/control": wsProxy(aqciHttp, dropApiPrefix),
    "/api/ws/fusion": wsProxy(tcfkHttp, dropApiPrefix),
    "/api/ws/rqfs_feedback": wsProxy(rqfsHttp, dropApiPrefix),

    // extra WS endpoints you actually use
    "/ws": wsProxy(fastApiHttp),
    "/resonance": wsProxy(fastApiHttp),

    // ─────────────────────────────────────────────────────────────
    // SCI proxy
    // ─────────────────────────────────────────────────────────────
    "/sci": {
      target: sciHttp,
      changeOrigin: true,
      secure: false,
      rewrite: (p: string) => p.replace(/^\/sci/, ""),
    },

    // ─────────────────────────────────────────────────────────────
    // Catch-all /api ALWAYS goes to FastAPI
    // ─────────────────────────────────────────────────────────────
    "^/api(?:/|$)": {
      target: fastApiHttp,
      changeOrigin: true,
      secure: false,
    },
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