// radioPatch.ts (FINAL: safe; no global WebSocket monkeypatch)
// Import once at app bootstrap (main.tsx)

const V = (import.meta as any)?.env ?? {};
const RAW_BASE = String(V.VITE_RADIO_BASE || "").trim();
const DISABLE_PATCH = String(V.VITE_DISABLE_RADIO_PATCH || "").trim() === "1";

// Radio token is still useful, but apply it at the callsite for glyphnet WS.
// (Do NOT global-monkeypatch WebSocket; it breaks debugging + can cause side-effects.)
export const GLYPH_TOKEN: string = String(V.VITE_GLYPHNET_TOKEN || "dev-bridge");

function autoRadioBase8787(): string {
  try {
    const origin = window.location.origin;

    // Codespaces: https://<name>-5173.app.github.dev -> https://<name>-8787.app.github.dev
    if (origin.includes("-5173.")) return origin.replace("-5173.", "-8787.");

    // Local: http://localhost:5173 -> http://localhost:8787
    if (origin.endsWith(":5173")) return origin.replace(":5173", ":8787");

    return origin;
  } catch {
    return "http://localhost:8787";
  }
}

const USING_PROXY = RAW_BASE.toLowerCase() === "proxy";
const RADIO_BASE = USING_PROXY ? "" : (RAW_BASE || autoRadioBase8787()).replace(/\/+$/, "");

function httpAbs(path: string) {
  const p = path.startsWith("/") ? path : "/" + path;
  if (USING_PROXY || !RADIO_BASE) return p; // relative; Vite proxy handles it
  return `${RADIO_BASE}${p}`;
}

if (!DISABLE_PATCH) {
  console.info(USING_PROXY ? "[radioPatch] mode=proxy" : `[radioPatch] base=${RADIO_BASE || "(relative)"}`);
} else {
  console.info("[radioPatch] DISABLED via VITE_DISABLE_RADIO_PATCH=1");
}

// Helper you can use anywhere you create glyphnet WS yourself:
export function glyphnetWsUrl(path = "/ws/glyphnet", token = GLYPH_TOKEN) {
  const p = path.startsWith("/") ? path : "/" + path;

  // If using proxy, WS should be same-origin (5173) so Vite proxies it
  if (USING_PROXY || !RADIO_BASE) {
    const baseWs = window.location.origin.replace(/^http/i, "ws");
    const u = new URL(p, baseWs);
    if (!u.searchParams.get("token")) u.searchParams.set("token", token);
    return u.toString();
  }

  // Direct to radio-node host
  const baseWs = RADIO_BASE.startsWith("https")
    ? RADIO_BASE.replace(/^https/i, "wss")
    : RADIO_BASE.replace(/^http/i, "ws");

  const u = new URL(p, baseWs);
  if (!u.searchParams.get("token")) u.searchParams.set("token", token);
  return u.toString();
}

// fetch rewrite ONLY for radio-node owned paths (DO NOT touch /api/wallet, /api/lean, etc.)
(() => {
  if (DISABLE_PATCH) return;
  if (USING_PROXY) return; // let Vite proxy handle it

  const origFetch = window.fetch.bind(window);

  const RADIO_HTTP_PATHS = [
    /^\/bridge\b/i,
    /^\/containers\b/i,
    /^\/health\b/i,

    // if radio-node serves these:
    /^\/api\/health\b/i,
    /^\/api\/session\/(me|attach|clear)\b/i,
    /^\/api\/glyphnet\/tx\b/i,
  ];

  function toRadioPath(input: RequestInfo | URL): string | null {
    const url =
      typeof input === "string"
        ? input
        : (input as any)?.url
        ? String((input as any).url)
        : String(input);

    try {
      const u = new URL(url, window.location.origin);
      const path = u.pathname + (u.search || "");
      return RADIO_HTTP_PATHS.some((rx) => rx.test(u.pathname)) ? path : null;
    } catch {
      return null;
    }
  }

  window.fetch = async (input: any, init?: RequestInit) => {
    const p = toRadioPath(input);
    if (p) return origFetch(httpAbs(p), init);
    return origFetch(input, init);
  };
})();