// src/utils/transport.ts
import { Telemetry } from "./telemetry"; // ← named import (matches your file)

export type TransportMode = "auto" | "radio-only" | "ip-only";

const MODE_KEY = "gnet:transportMode";
let lastRadioOk = false;

/** Persisted transport policy */
export function getTransportMode(): TransportMode {
  const v = (localStorage.getItem(MODE_KEY) || "auto").toLowerCase();
  return v === "radio-only" || v === "ip-only" ? v : "auto";
}
export function setTransportMode(m: TransportMode) {
  try { localStorage.setItem(MODE_KEY, m); } catch {}
}

/** http(s)://… for the local radio-node */
export function radioBase(): string {
  const { host, protocol } = window.location;
  if (host.endsWith(".app.github.dev")) return `https://${host.replace("-5173", "-8787")}`;
  if (/:(5173)$/.test(host)) return `${protocol.replace("https", "http")}//${host.replace(":5173", ":8787")}`;
  return `${protocol}//${host.replace(/:\d+$/, ":8787")}`;
}

/** Poll radio-node /health and push results into a setter (already wired in ChatThread). */
export function onRadioHealth(set: (ok: boolean) => void, everyMs = 4000): () => void {
  let stop = false;
  async function check() {
    try {
      const r = await fetch(`${radioBase()}/health`, { cache: "no-store" });
      lastRadioOk = r.ok;
      if (!stop) set(lastRadioOk);
    } catch {
      lastRadioOk = false;
      if (!stop) set(false);
    }
  }
  check();
  const id = window.setInterval(check, everyMs);
  return () => { stop = true; clearInterval(id); };
}

/** Pick the HTTP base according to mode + last radio health. */
export function transportBase(ipBase: string): string {
  const mode = getTransportMode();
  if (mode === "ip-only")    return ipBase;
  if (mode === "radio-only") return radioBase();
  return lastRadioOk ? radioBase() : ipBase;
}

/** Build a WS URL (wss://…/ws/glyphnet) that follows the same policy. */
export function wsBaseFor(ipBase: string): string {
  const http = transportBase(ipBase);               // http(s)://…
  return http.replace(/^http(s?):\/\//, (_, s) => `ws${s || ""}://`);
}

/** Convenience: WS URL for GlyphNet (topic, kg, token). */
export function glyphnetWsUrl(ipBase: string, topic: string, kg: string, token = "dev-token"): string {
  const wsBase = wsBaseFor(ipBase);
  const q = new URLSearchParams({ topic, kg, token }).toString();
  return `${wsBase}/ws/glyphnet?${q}`;
}

/** POST /tx with policy + telemetry bumps */
export async function postTx(
  ipBase: string,                          // pass the cloud base; policy applied here
  payload: any,
  headers: Record<string, string> = {}
): Promise<Response> {
  const base = transportBase(ipBase);      // apply Auto / RF-only / IP-only policy
  const url = `${base}/api/glyphnet/tx`;

  // crude but effective: :8787 = local radio node
  const transport: "rf" | "ip" = url.includes(":8787") ? "rf" : "ip";

  try {
    const res = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json", ...headers },
      body: JSON.stringify(payload),
    });

    // bump ok/err counters
    Telemetry.inc(transport === "rf" ? "rf_ok" : "ip_ok");
    if (!res.ok) Telemetry.inc(transport === "rf" ? "rf_err" : "ip_err");

    return res;
  } catch (e) {
    Telemetry.inc(transport === "rf" ? "rf_err" : "ip_err");
    throw e;
  }
}