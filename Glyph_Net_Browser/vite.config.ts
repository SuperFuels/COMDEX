// vite.config.ts
import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react-swc";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), "");
  const backendHttp = env.VITE_BACKEND_URL || env.VITE_API_BASE || "http://localhost:8080";
  const backendWs   = backendHttp.replace(/^http(s?):/, (_m, s) => (s ? "wss:" : "ws:"));

  return {
    plugins: [react()],
    resolve: { alias: { "@": path.resolve(__dirname, "src") } },
    server: {
      host: true,
      port: 5173,
      strictPort: true,
      cors: true,
      proxy: {
        // ── Radio-node (local GlyphNet)
        // Put the specific bridge rule BEFORE the catch-all /radio rule.
        "^/radio/bridge": {
          target: "http://localhost:8787",
          changeOrigin: true,
          rewrite: p => p.replace(/^\/radio\/bridge/, "/bridge"),
        },

        // Catch-all: keeps /api and /ws intact by stripping only the /radio prefix
        "^/radio": {
          target: "http://localhost:8787",
          changeOrigin: true,
          ws: true,
          rewrite: p => p.replace(/^\/radio/, ""),
        },

        // ── GHX (landing page) → your backend
        "^/api/(container|containers)/.*": { target: backendHttp, changeOrigin: true },
        "^/ws/ghx": { target: backendWs, ws: true, changeOrigin: true },

        // ── Everything else → backend
        "/api": { target: backendHttp, changeOrigin: true, ws: true },
        "^/ws":  { target: backendWs,   ws: true, changeOrigin: true },
      },
    },
    preview: { host: "0.0.0.0", port: 5173 },
    build: { outDir: "dist" },
  };
});