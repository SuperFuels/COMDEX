// radioPatch.ts
// Safe: no global WebSocket monkeypatch. Fetch rewrite is STRICT + non-destructive.
// Import once at app bootstrap (main.tsx).

const V = (import.meta as any)?.env ?? {};
const RAW_BASE = String(V.VITE_RADIO_BASE || "").trim();
const DISABLE_PATCH = String(V.VITE_DISABLE_RADIO_PATCH || "").trim() === "1";

// Token is useful for WS URLs you build yourself.
export const GLYPH_TOKEN: string = String(V.VITE_GLYPHNET_TOKEN || "dev-bridge");

function autoRadioBase8787(): string {
  try {
    const origin = window.location.origin;

    // Codespaces: https://<name>-5173.app.github.dev -> https://<name>-8787.app.github.dev
    if (origin.includes("-5173.")) return origin.replace("-5173.", "-8787.");

    // Local dev: http://localhost:5173 -> http://localhost:8787
    if (origin.endsWith(":5173")) return origin.replace(":5173", ":8787");

    // Fallback: same origin (useful if you reverse-proxy)
    return origin;
  } catch {
    return "http://127.0.0.1:8787";
  }
}

const USING_PROXY = RAW_BASE.toLowerCase() === "proxy";
// If proxy mode: use relative paths and let Vite handle proxying.
// Otherwise: absolute base to radio-node.
const RADIO_BASE = USING_PROXY ? "" : (RAW_BASE || autoRadioBase8787()).replace(/\/+$/, "");

function httpAbs(pathnameAndSearch: string) {
  const p = pathnameAndSearch.startsWith("/") ? pathnameAndSearch : "/" + pathnameAndSearch;
  if (USING_PROXY || !RADIO_BASE) return p;
  return `${RADIO_BASE}${p}`;
}

if (DISABLE_PATCH) {
  console.info("[radioPatch] DISABLED via VITE_DISABLE_RADIO_PATCH=1");
} else {
  console.info(USING_PROXY ? "[radioPatch] mode=proxy" : `[radioPatch] base=${RADIO_BASE || "(relative)"}`);
}

/** Helper to build WS URLs without monkeypatching WebSocket. */
export function glyphnetWsUrl(path = "/ws/glyphnet", token = GLYPH_TOKEN) {
  const p = path.startsWith("/") ? path : "/" + path;

  // Proxy mode: same-origin WS so Vite can proxy /ws/*
  if (USING_PROXY || !RADIO_BASE) {
    const baseWs = window.location.origin.replace(/^http/i, "ws");
    const u = new URL(p, baseWs);
    if (!u.searchParams.get("token")) u.searchParams.set("token", token);
    return u.toString();
  }

  // Direct to radio-node
  const baseWs = RADIO_BASE.startsWith("https")
    ? RADIO_BASE.replace(/^https/i, "wss")
    : RADIO_BASE.replace(/^http/i, "ws");

  const u = new URL(p, baseWs);
  if (!u.searchParams.get("token")) u.searchParams.set("token", token);
  return u.toString();
}

/**
 * Fetch rewrite ONLY for radio-node owned *paths*.
 * Rules:
 *  - Never touch absolute URLs to other hosts.
 *  - Never touch non-matching paths.
 *  - Preserve the native fetch so debugging isn't bricked.
 */
(() => {
  if (DISABLE_PATCH) return;

  // In proxy mode, do NOTHING: relative fetches should stay same-origin (5173) and Vite proxies them.
  if (USING_PROXY) return;

  // Preserve the true/native fetch (and expose it for debugging).
  const nativeFetch = window.fetch.bind(window);
  (window as any).__nativeFetch = nativeFetch;

  // Only these paths get redirected to RADIO_BASE.
  // Keep this list tight and explicit.
  const RADIO_HTTP_PATHS: RegExp[] = [
    // Debug/status (NOTE: keep /__routes here only if you want it rewritten)
    // If you prefer to call BASE + "/__routes" manually, remove this line.
    /^\/__routes\b/i,

    /^\/health\b/i,
    /^\/bridge\b/i,
    /^\/containers\b/i,

    // Session + glyphnet TX
    /^\/api\/session\/(me|attach|clear)\b/i,
    /^\/api\/glyphnet\/tx\b/i,

    // WirePack (legacy + v46 session/template/delta)
    /^\/api\/wirepack\b/i, // includes /api/wirepack/v46/*
  ];

  function isAbsoluteUrl(s: string): boolean {
    return /^https?:\/\//i.test(s);
  }

  function extractUrl(input: RequestInfo | URL): string {
    if (typeof input === "string") return input;
    if (input instanceof URL) return input.toString();
    const anyReq = input as any; // Request
    return typeof anyReq?.url === "string" ? anyReq.url : String(input);
  }

  function shouldRewrite(u: URL): boolean {
    // Only rewrite same-origin PATH calls (or relative calls resolved to same origin).
    // Never rewrite calls that already target some other host.
    if (u.origin !== window.location.origin) return false;
    return RADIO_HTTP_PATHS.some((rx) => rx.test(u.pathname));
  }

  window.fetch = async (input: any, init?: RequestInit) => {
    try {
      const raw = extractUrl(input);

      // If caller already passed an absolute URL, DO NOT rewrite.
      // This keeps console tests like fetch(BASE + "/health") working.
      if (isAbsoluteUrl(raw)) return nativeFetch(input, init);

      // Resolve relative to current page origin
      const u = new URL(raw, window.location.origin);

      // Not on allowlist -> don't touch
      if (!shouldRewrite(u)) return nativeFetch(input, init);

      // Rewrite to radio base, preserving path + query.
      const rewritten = httpAbs(u.pathname + u.search);

      // If input was a Request object, we keep semantics by:
      // - using the rewritten URL
      // - preserving init (method/headers/body/etc) passed by caller
      return nativeFetch(rewritten, init);
    } catch {
      // On any parsing weirdness, fall back to native behavior.
      return nativeFetch(input, init);
    }
  };
})();