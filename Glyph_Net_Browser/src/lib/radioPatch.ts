// Centralized radio base + safe URL patchers for Codespaces / local / prod.
// Import this once at app bootstrap (see main.tsx).

const V = (import.meta as any)?.env ?? {};
const RAW_BASE = String(V.VITE_RADIO_BASE || "").trim();
const USING_PROXY = RAW_BASE === "" || RAW_BASE.toLowerCase() === "proxy";

// If not using the proxy, we expect a full URL (http/https). Trim trailing slashes.
const RADIO_BASE = USING_PROXY ? "" : RAW_BASE.replace(/\/+$/, "");
const GLYPH_TOKEN: string = String(V.VITE_GLYPHNET_TOKEN || "dev-bridge");

function httpAbs(path: string) {
  const p = path.startsWith("/") ? path : "/" + path;
  if (USING_PROXY) return p; // let Vite proxy handle it
  return `${RADIO_BASE}${p}`;
}

function wsAbs(path: string) {
  const p = path.startsWith("/") ? path : "/" + path;
  if (USING_PROXY) {
    const origin = window.location.origin.replace(/^http/i, "ws");
    return `${origin}${p}`;
  }
  const wsBase = RADIO_BASE.startsWith("https")
    ? RADIO_BASE.replace(/^https/i, "wss")
    : RADIO_BASE.replace(/^http/i, "ws");
  return `${wsBase}${p}`;
}

// Log mode so we can verify quickly in the console.
console.info(
  USING_PROXY ? "[radioPatch] mode = proxy" : `[radioPatch] base = ${RADIO_BASE}`
);

// --- Patch WebSocket: only touch /ws/glyphnet, add token if missing ----------
(() => {
  const OrigWS = window.WebSocket;
  function targetsGlyph(url: string) {
    try {
      const u = new URL(url, window.location.origin);
      return /^\/ws\/glyphnet/i.test(u.pathname);
    } catch {
      return false;
    }
  }

  (window as any).WebSocket = function PatchedWS(url: string, protocols?: string | string[]) {
    if (!targetsGlyph(url)) {
      return new OrigWS(url, protocols as any);
    }

    // Build URL on the correct host, then ensure token param exists
    const u = new URL(url, USING_PROXY ? window.location.origin : RADIO_BASE || window.location.origin);
    if (!u.searchParams.get("token")) u.searchParams.set("token", GLYPH_TOKEN);

    const finalUrl = USING_PROXY
      ? wsAbs(u.pathname + (u.search || ""))
      : wsAbs(u.pathname + (u.search || ""));

    return new OrigWS(finalUrl, protocols as any);
  } as any;

  (window as any).WebSocket.prototype = OrigWS.prototype;
})();

// --- Patch fetch: ONLY rewrite our radio endpoints. In proxy mode we do nothing.
(() => {
  if (USING_PROXY) return; // leave fetch alone; Vite proxy handles /api, /health, /bridge, etc.

  const origFetch = window.fetch.bind(window);
  const RADIO_PATHS = [
    /^\/api\/health\b/i,
    /^\/api\/session\/(me|attach|clear)\b/i,
    /^\/api\/glyphnet\/tx\b/i,
    /^\/bridge\//i,
    /^\/containers\b/i,
    /^\/health\b/i,
  ];

  function toPath(input: RequestInfo | URL): string | null {
    const url = typeof input === "string"
      ? input
      : (input as any)?.url
      ? String((input as any).url)
      : String(input);
    try {
      const u = new URL(url, window.location.origin);
      return RADIO_PATHS.some(rx => rx.test(u.pathname))
        ? u.pathname + (u.search || "")
        : null;
    } catch {
      return null;
    }
  }

  window.fetch = async (input: any, init?: RequestInit) => {
    const path = toPath(input);
    if (path) return origFetch(httpAbs(path), init);
    return origFetch(input, init);
  };
})();