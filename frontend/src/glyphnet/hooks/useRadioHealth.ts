// src/hooks/useRadioHealth.ts
// src/glyphnet/hooks/useRadioHealth.ts
import { httpUrl } from "@glyphnet/lib/net";

export type RadioStatus = "unknown" | "up" | "reconnecting" | "down";

type Options = {
  intervalMs?: number;
  timeoutMs?: number;
  onRecovered?: () => void; // fires when status transitions to "up"
};

/**
 * Lightweight poller (no React state) for radio health.
 * Returns a small facade with subscribe()/dispose().
 *
 * Works with either:
 *  - Vite proxy (relative /health goes to the radio-node via the proxy)
 *  - Direct radio base (VITE_RADIO_BASE), which httpUrl() expands to absolute
 *
 * Tip: To force a specific base at runtime, set:
 *   localStorage.setItem("gnet:radioNodeBase", "http://127.0.0.1:8787")
 */
export function useRadioHealth(opts: Options = {}) {
  const intervalMs = opts.intervalMs ?? 3000;
  const timeoutMs = opts.timeoutMs ?? 1500;

  // Optional runtime override (bypasses proxy/env)
  const override = localStorage.getItem("gnet:radioNodeBase");
  const HEALTH_URL = override
    ? `${override.replace(/\/+$/, "")}/health`
    : httpUrl("/health");

  const statusRef = { current: "unknown" as RadioStatus };
  const failuresRef = { current: 0 };
  let subscribers: Array<(s: RadioStatus) => void> = [];
  let lastOkTs = 0;

  const setStatus = (next: RadioStatus) => {
    if (statusRef.current !== next) {
      const prev = statusRef.current;
      statusRef.current = next;
      if (prev !== "up" && next === "up") opts.onRecovered?.();
      subscribers.forEach((fn) => fn(next));
    }
  };

  const poll = async () => {
    const ac = new AbortController();
    const t = setTimeout(() => ac.abort(), timeoutMs);
    try {
      const res = await fetch(HEALTH_URL, { signal: ac.signal, cache: "no-store" });
      clearTimeout(t);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      // Shape may vary; we just need a 200.
      await res.json().catch(() => ({}));
      failuresRef.current = 0;
      lastOkTs = Date.now();
      setStatus("up");
    } catch {
      failuresRef.current += 1;
      if (failuresRef.current === 1) setStatus("reconnecting");
      else if (failuresRef.current >= 3) setStatus("down");
    }
  };

  // Simple pub-sub so consumers can re-render
  const subscribe = (fn: (s: RadioStatus) => void) => {
    subscribers.push(fn);
    // push current immediately
    try {
      fn(statusRef.current);
    } catch {}
    return () => {
      subscribers = subscribers.filter((x) => x !== fn);
    };
  };

  // Background poller
  const timer = setInterval(poll, intervalMs);
  // Immediate first check
  void poll();

  // Facade
  return {
    get status() {
      return statusRef.current;
    },
    get lastOkTs() {
      return lastOkTs;
    },
    refresh: () => poll(),
    subscribe,
    dispose: () => clearInterval(timer),
  };
}