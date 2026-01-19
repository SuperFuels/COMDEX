// frontend/tabs/Aion/demos/types.ts
// Keep this minimal + tolerant: backend payloads may evolve.

export type JsonValue = null | boolean | number | string | JsonValue[] | { [k: string]: JsonValue };

export type Envelope<T = any> = {
  ok?: boolean;
  ts?: number | string;
  data_root?: string;
  source_file?: string | null;
  source_files?: Record<string, string>;
  derived?: Record<string, any>;
} & T;

/* ---------------- Demo 01 (Metabolism / Φ) ---------------- */

export type PhiDerived = {
  last_update_iso?: string | null;
  last_update_age_s?: number | null;
  metabolic_pulse?: "ACTIVE" | "AT_REST" | string;
};

export type PhiBundle = Envelope<{
  state?: Record<string, any>;
  derived?: PhiDerived;
}>;

/* ---------------- Demo 02 (Immune / ADR) ---------------- */

export type AdrDerived = {
  rsi?: number | null;
  drift_entropy?: number | null;
  zone?: "GREEN" | "YELLOW" | "RED" | "UNKNOWN" | string;
  adr_status?: "ARMED" | "TRIGGERED" | "RECOVERING" | string;
  red_pulse?: boolean;
  last_trigger_age_s?: number | null;
  trigger_id?: string | null;
};

export type AdrBundle = Envelope<{
  latest_stream_event?: Record<string, any> | null;
  latest_drift_repair?: Record<string, any> | null;
  pal_state?: Record<string, any>;
  derived?: AdrDerived;
}>;

/* ---------------- Demo 03 (Heartbeat / Θ) ---------------- */

export type HeartbeatEnvelope = Envelope<{
  namespace?: string | null;
  age_ms?: number | null;
  now_s?: number | null;
  heartbeat?: Record<string, any> | null;
}>;

/* ---------------- Demo 04 (Reflex / Cognitive Grid) ----------------
   Expected shape from demo_bridge:
     "reflex": { "ok": true, "state": { ... } }
   And (recommended) /api/reflex returns:
     { ok, state, derived? }
*/

export type ReflexState = {
  // minimal expected fields; keep optional
  grid_size?: number;
  vision_range?: number;
  max_steps?: number;

  steps?: number;
  score?: number;
  status?: "running" | "complete" | "failed" | string;

  position?: [number, number];
  alive?: boolean;

  // last event / reflection (optional)
  last_event?: Record<string, any> | null;

  // anything else the backend writes
  [k: string]: any;
};

export type ReflexEnvelope = Envelope<{
  state?: ReflexState | null;
  derived?: Record<string, any>;
}>;

/* ---------------- Shared demo meta ---------------- */

export type DemoMeta = {
  id: string;
  pillar: string;
  title: string;
  testName: string;
  copy: string;
};