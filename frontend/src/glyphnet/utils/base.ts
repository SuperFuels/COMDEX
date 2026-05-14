// frontend/src/glyphnet/utils/base.ts

/**
 * Next-safe API base resolver.
 * - No import.meta usage (Vite-only)
 * - SSR-safe (won't touch window/location on server)
 * - Supports Codespaces + localhost dev heuristics
 *
 * Precedence:
 *  1) NEXT_PUBLIC_API_URL (full URL, e.g. https://api.example.com)
 *  2) Browser heuristics (codespaces/localhost/port mapping)
 *  3) Same-origin
 */
export function resolveApiBase(): string {
  // 1) Explicit override (works in Next)
  const envUrl =
    (process.env.NEXT_PUBLIC_API_URL || "").trim();

  if (envUrl) return stripTrailingSlash(envUrl);

  // 2) SSR-safe fallback
  if (typeof window === "undefined" || typeof location === "undefined") {
    // Reasonable server default; should rarely be used because pages using this
    // should run client-side, but keeps builds from exploding.
    return "http://localhost:8080";
  }

  const host = location.host; // includes port
  const proto = location.protocol; // "http:" | "https:"

  // Codespaces: map frontend port -> backend port
  // Example host: something-5173.app.github.dev -> something-8080.app.github.dev
  const isCodespaces = host.endsWith(".app.github.dev");
  if (isCodespaces) return `${proto}//${host.replace("-5173", "-8080")}`;

  // Local dev: Vite -> backend
  if (host === "localhost:5173" || host === "127.0.0.1:5173") return "http://localhost:8080";

  // Port mapping: *:5173 -> *:8080 (if you run UI on 5173 and API on 8080)
  const m = host.match(/^(.*):5173$/);
  if (m) return `${proto}//${m[1]}:8080`;

  // Same-origin
  return `${proto}//${host}`;
}

export function resolveWsBase(): string {
  const envWs = (process.env.NEXT_PUBLIC_WS_URL || "").trim();
  if (envWs) return stripTrailingSlash(envWs);

  const api = resolveApiBase();
  return api.replace(/^http/i, "ws");
}

function stripTrailingSlash(s: string): string {
  return s.replace(/\/+$/, "");
}