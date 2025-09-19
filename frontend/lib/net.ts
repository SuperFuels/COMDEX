// frontend/lib/net.ts
export function apiBase(): string {
  // e.g. NEXT_PUBLIC_API_URL = https://comdex-api-xxxx.a.run.app/api
  const raw = process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, "");
  return raw ?? ""; // when empty, you can still call relative /api routes
}

export async function http<T = any>(path: string, init?: RequestInit): Promise<T> {
  // accepts "/aion/containers", "/aion/engine/qwave/fields", etc.
  const base = apiBase();                  // "" or "https://.../api"
  const url  = `${base}${path.startsWith("/") ? path : `/${path}`}`;
  const res  = await fetch(url, init);
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
  return res.json();
}

export function wsBase(): string {
  // Prefer WS next to NEXT_PUBLIC_API_URL, else fall back to current origin.
  const raw = process.env.NEXT_PUBLIC_API_URL;
  if (raw) {
    try {
      const u = new URL(raw);              // https://host.tld[/api]
      u.protocol = u.protocol === "https:" ? "wss:" : "ws:";
      u.pathname = "";                     // drop trailing "/api"
      return u.toString().replace(/\/$/, "");
    } catch (_) { /* fall through */ }
  }
  if (typeof window !== "undefined") {
    const wsProto = window.location.protocol === "https:" ? "wss:" : "ws:";
    return `${wsProto}//${window.location.host}`;
  }
  return ""; // SSR: don't open sockets
}