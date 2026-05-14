// src/utils/transport.ts
import { Telemetry } from "./telemetry";

export type TransportMode = "auto" | "radio-only" | "ip-only";

const MODE_KEY = "gnet:transportMode";

// module state is fine (client), but SSR must not depend on it
let lastRadioHealthy = false;

function isBrowser(): boolean {
  return typeof window !== "undefined" && typeof location !== "undefined";
}

/** Persisted transport policy (falls back to NEXT_PUBLIC_TRANSPORT_MODE, then "auto"). */
export function getTransportMode(): TransportMode {
  // SSR-safe: no localStorage access
  if (isBrowser()) {
    try {
      const v = (localStorage.getItem(MODE_KEY) as TransportMode | null) || null;
      if (v === "radio-only" || v === "ip-only" || v === "auto") return v;
    } catch {
      // ignore
    }
  }

  // Next-safe env (replaces import.meta.env.VITE_TRANSPORT_MODE)
  const def = (process.env.NEXT_PUBLIC_TRANSPORT_MODE || "").trim() as TransportMode;

  return def === "radio-only" || def === "ip-only" ? def : "auto";
}

export function setTransportMode(m: TransportMode) {
  if (!isBrowser()) return;
  try {
    localStorage.setItem(MODE_KEY, m);
  } catch {
    // ignore
  }
}

/** Probe radio-node health via proxy and update `lastRadioHealthy`. */
export function onRadioHealth(set: (ok: boolean) => void, everyMs = 4000): () => void {
  // SSR-safe: no timers/fetch
  if (!isBrowser()) return () => {};

  let stop = false;

  async function check() {
    try {
      const r = await fetch(`/radio/health`, { cache: "no-store" });
      lastRadioHealthy = r.ok;
      if (!stop) set(r.ok);
    } catch {
      lastRadioHealthy = false;
      if (!stop) set(false);
    }
  }

  check();
  const id = window.setInterval(check, everyMs);
  return () => {
    stop = true;
    clearInterval(id);
  };
}

/**
 * Return a *relative* base so rewrites/proxies can route:
 * - "/radio" → radio-node
 * - ""       → backend/cloud (default)
 *
 * `ipBase` kept for call-site compatibility but ignored for routing.
 */
export function transportBase(_ipBase: string): string {
  const mode = getTransportMode();
  if (mode === "radio-only") return "/radio";
  if (mode === "ip-only") return "";

  // auto
  return lastRadioHealthy ? "/radio" : "";
}

/** Build a WS URL relative to current origin, honoring the selected base. */
export function buildWsUrl(base: string, path: string, qs?: string): string {
  // SSR-safe fallback (won't be used until client mounts)
  if (!isBrowser()) return `ws://localhost:5173${base}${path}${qs ? (qs.startsWith("?") ? qs : `?${qs}`) : ""}`;

  const proto = location.protocol === "https:" ? "wss:" : "ws:";
  const q = qs ? (qs.startsWith("?") ? qs : `?${qs}`) : "";
  return `${proto}//${location.host}${base}${path}${q}`;
}

/** Convenience: WS URL for GlyphNet. */
export function glyphnetWsUrl(ipBase: string, topic: string, kg: string, token = "dev-token"): string {
  const base = transportBase(ipBase);
  const qs = new URLSearchParams({ topic, kg, token }).toString();
  return buildWsUrl(base, "/ws/glyphnet", qs);
}

/**
 * Backward-compat helper: produce a WS base (wss://host[/radio]) for custom callers.
 * Prefer using `buildWsUrl` directly.
 */
export function wsBaseFor(ipBase: string): string {
  const base = transportBase(ipBase);

  if (!isBrowser()) return `ws://localhost:5173${base}`;

  const proto = location.protocol === "https:" ? "wss:" : "ws:";
  return `${proto}//${location.host}${base}`;
}

/** POST /api/glyphnet/tx with policy + telemetry bumps. */
export async function postTx(
  ipBase: string, // unused for routing now; kept for call sites
  payload: any,
  headers: Record<string, string> = {}
): Promise<Response> {
  const base = transportBase(ipBase); // "" (backend) or "/radio" (radio-node)
  const url = `${base}/api/glyphnet/tx`;
  const transport: "rf" | "ip" = base === "/radio" ? "rf" : "ip";

  try {
    const res = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json", ...headers },
      body: JSON.stringify(payload),
    });

    Telemetry.inc(transport === "rf" ? "rf_ok" : "ip_ok");
    if (!res.ok) Telemetry.inc(transport === "rf" ? "rf_err" : "ip_err");
    return res;
  } catch (e) {
    Telemetry.inc(transport === "rf" ? "rf_err" : "ip_err");
    throw e;
  }
}

/** Old-style absolute radio base; retained for any external callers. */
export function radioBase(): string {
  return "/radio";
}