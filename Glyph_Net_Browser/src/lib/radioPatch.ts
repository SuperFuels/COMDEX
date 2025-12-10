// Centralized radio base + safe URL patchers for Codespaces / local / prod.
// Import this once at app bootstrap (see main.tsx).

const V = (import.meta as any)?.env ?? {};
const RAW_BASE = String(V.VITE_RADIO_BASE || "").trim();
const GLYPH_TOKEN: string = String(V.VITE_GLYPHNET_TOKEN || "dev-bridge");

// "proxy" means: let Vite dev proxy handle /api/* (original behavior).
// Empty RAW_BASE now means "auto-detect radio base" instead of proxy.
const USING_PROXY = RAW_BASE.toLowerCase() === "proxy";

/**
 * Auto-detect radio base when VITE_RADIO_BASE is not set.
 * - Codespaces: swap 5173 -> 8080 on same host
 * - Local:      swap :5173 -> :8080
 * - Fallback:   http://localhost:8080
 */
function autoRadioBase(): string {
  try {
    const origin = window.location.origin;
    if (origin.includes("-5173.")) {
      return origin.replace("-5173.", "-8080.");
    }
    if (origin.endsWith(":5173")) {
      return origin.replace(":5173", ":8080");
    }
    return origin;
  } catch {
    return "http://localhost:8080";
  }
}

// Decide final RADIO_BASE:
//   - RAW_BASE = "proxy" → proxy mode, RADIO_BASE = ""
//   - RAW_BASE non-empty → use it
//   - RAW_BASE empty     → auto-detect
const RADIO_BASE = USING_PROXY
  ? ""
  : (RAW_BASE || autoRadioBase()).replace(/\/+$/, "");

function httpAbs(path: string) {
  const p = path.startsWith("/") ? path : "/" + path;
  if (USING_PROXY && !RADIO_BASE) return p; // explicit proxy mode: leave as-is
  return `${RADIO_BASE}${p}`;
}

function wsAbs(path: string) {
  const p = path.startsWith("/") ? path : "/" + path;

  if (USING_PROXY && !RADIO_BASE) {
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
  USING_PROXY && !RADIO_BASE
    ? "[radioPatch] mode = proxy"
    : `[radioPatch] base = ${RADIO_BASE}`
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

  (window as any).WebSocket = function PatchedWS(
    url: string,
    protocols?: string | string[]
  ) {
    if (!targetsGlyph(url)) {
      return new OrigWS(url, protocols as any);
    }

    // Build URL on the correct host, then ensure token param exists
    const u = new URL(
      url,
      USING_PROXY && !RADIO_BASE ? window.location.origin : RADIO_BASE || window.location.origin
    );
    if (!u.searchParams.get("token")) u.searchParams.set("token", GLYPH_TOKEN);

    const finalUrl = wsAbs(u.pathname + (u.search || ""));

    return new OrigWS(finalUrl, protocols as any);
  } as any;

  (window as any).WebSocket.prototype = OrigWS.prototype;
})();

// --- Patch fetch: rewrite our radio/backend endpoints ------------------------
(() => {
  // In strict "proxy" mode, leave fetch alone; Vite proxy handles everything.
  if (USING_PROXY && !RADIO_BASE) {
    console.info("[radioPatch] fetch: proxy mode (no rewrites)");
    return;
  }

  const origFetch = window.fetch.bind(window);

  const RADIO_PATHS = [
    // existing
    /^\/api\/health\b/i,
    /^\/api\/session\/(me|attach|clear)\b/i,
    /^\/api\/glyphnet\/tx\b/i,
    /^\/bridge\//i,
    /^\/containers\b/i,
    /^\/health\b/i,

    // NEW: wallet + mesh APIs
    /^\/api\/wallet\/balances\b/i,
    /^\/api\/mesh\/local_state\b/i,
    /^\/api\/mesh\/local_send\b/i,
    /^\/api\/mesh\//i,
  ];

  function toPath(input: RequestInfo | URL): string | null {
    const url =
      typeof input === "string"
        ? input
        : (input as any)?.url
        ? String((input as any).url)
        : String(input);

    try {
      const u = new URL(url, window.location.origin);
      const path = u.pathname + (u.search || "");
      return RADIO_PATHS.some((rx) => rx.test(u.pathname)) ? path : null;
    } catch {
      return null;
    }
  }

  window.fetch = async (input: any, init?: RequestInit) => {
    const path = toPath(input);
    if (path) {
      const target = httpAbs(path);
      // Uncomment for debugging:
      // console.debug("[radioPatch] fetch →", target);
      return origFetch(target, init);
    }
    return origFetch(input, init);
  };
})();