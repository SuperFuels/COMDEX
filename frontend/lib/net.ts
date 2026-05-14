export function apiBase(): string {
  const raw = process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, "");
  return raw ? `${raw}/api` : "/api";   // 👈 always append /api here
}

export async function http<T = any>(path: string, init?: RequestInit): Promise<T> {
  const base = apiBase();
  const url  = `${base}${path.startsWith("/") ? path : `/${path}`}`;
  const res  = await fetch(url, init);
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
  return res.json();
}

export function wsBase(): string {
  const raw = process.env.NEXT_PUBLIC_API_URL;
  if (raw) {
    try {
      const u = new URL(raw);
      u.protocol = u.protocol === "https:" ? "wss:" : "ws:";
      return u.toString().replace(/\/$/, "");
    } catch {}
  }
  if (typeof window !== "undefined") {
    const wsProto = window.location.protocol === "https:" ? "wss:" : "ws:";
    return `${wsProto}//${window.location.host}`;
  }
  return "";
}
