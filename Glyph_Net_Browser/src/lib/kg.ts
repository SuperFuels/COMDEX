// src/lib/kg.ts

// ─────────────────────────────────────────
// Emit KG events
// ─────────────────────────────────────────

export async function emitKG(
  base: string,
  args: {
    kg: "personal" | "work";
    owner: string; // owner WA
    events: Array<{
      id?: string;
      thread_id?: string;
      topic_wa?: string;
      type: string; // "message"|"visit"|"file"|"call"|"ptt_session"|"floor_lock"
      kind?: string; // e.g. "text"|"voice"|"offer"|"answer"...
      ts?: number;
      size?: number;
      sha256?: string | null;
      payload?: any;
    }>;
  }
) {
  const r = await fetch(`${base}/api/kg/events`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(args),
  });
  if (!r.ok) throw new Error(`emitKG ${r.status}`);
  return r.json();
}

// ─────────────────────────────────────────
// Entanglement view helper
// ─────────────────────────────────────────

export type EntanglementView = {
  ok: boolean;
  kg: "personal" | "work";
  container_id: string;
  entangled_with: string[];
  edges: { from: string; to: string; ts: number }[];
};

export async function fetchEntanglements(
  kg: "personal" | "work",
  containerId: string,
  base = ""
): Promise<EntanglementView> {
  const params = new URLSearchParams({
    kg,
    container_id: containerId,
  });

  const res = await fetch(
    `${base}/api/kg/view/entanglement?${params.toString()}`,
    {
      headers: { Accept: "application/json" },
    }
  );

  if (!res.ok) {
    throw new Error(`fetchEntanglements ${res.status}`);
  }

  return (await res.json()) as EntanglementView;
}

// ─────────────────────────────────────────
// KG stats helper (A70)
// ─────────────────────────────────────────

export type KgId = "personal" | "work";

export interface KgStats {
  ok: boolean;
  kg: KgId;
  events_total: number;
  events_by_type: Record<string, number>;
  edges_by_kind: Record<string, number>;
  files_total: number;
  attachments_total: number;
  container_refs_total: number;
  visits_total: number;
}

export async function fetchKgStats(
  base: string,
  kg: KgId = "personal"
): Promise<KgStats> {
  const r = await fetch(
    `${base}/api/kg/stats?kg=${encodeURIComponent(kg)}`,
    { cache: "no-store" }
  );
  if (!r.ok) throw new Error(`fetchKgStats ${r.status}`);
  return r.json();
}

// ─────────────────────────────────────────
// Forget helper (A59) – wraps /api/kg/forget
// ─────────────────────────────────────────

export interface ForgetVisitsPayload {
  kg: KgId;
  host?: string;
  topic_wa?: string;
  from_ms?: number;
  to_ms?: number;
}

/**
 * Forget visit events in the KG.
 * NOTE: server will reject requests that are "too broad" – so callers must
 * pass at least one of {host, topic_wa, from_ms, to_ms}.
 */
export async function forgetVisits(
  base: string,
  payload: ForgetVisitsPayload
): Promise<{ ok: boolean; deleted: number }> {
  const body = {
    ...payload,
    scope: "visits" as const,
  };

  const r = await fetch(`${base}/api/kg/forget`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });

  if (!r.ok) {
    throw new Error(`forgetVisits ${r.status}`);
  }

  return r.json();
}