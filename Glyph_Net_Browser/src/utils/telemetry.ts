// src/utils/telemetry.ts
export type TeleCounters = { rf_ok: number; rf_err: number; ip_ok: number; ip_err: number };

const counters: TeleCounters = { rf_ok: 0, rf_err: 0, ip_ok: 0, ip_err: 0 };

export const Telemetry = {
  inc(key: keyof TeleCounters) {
    counters[key] = (counters[key] || 0) + 1;
  },
  reset() {
    counters.rf_ok = 0;
    counters.rf_err = 0;
    counters.ip_ok = 0;
    counters.ip_err = 0;
  },
  snap(): TeleCounters {
    // return a shallow copy so React state updates properly
    return { ...counters };
  },
};

// expose for places that don’t import (e.g., transport.ts optional global)
try { (window as any).__tele = Telemetry; } catch {}