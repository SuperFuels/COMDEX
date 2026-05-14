// frontend/lib/api/holo.ts
import type { HoloIR } from "@/lib/types/holo";

export type HoloRunStatus = "ok" | "error" | "running";

export type HoloRunResult = {
  status?: HoloRunStatus;
  mode?: string;

  holo_id?: string;
  container_id?: string;

  output?: unknown;
  updated_holo?: HoloIR | null;
  metrics?: unknown;
};

const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "";

export async function runHoloSnapshot(body: {
  holo: HoloIR;
  inputCtx?: unknown;   // ✅ matches your code
  mode?: string;        // ✅ matches your code
}): Promise<HoloRunResult> {
  const res = await fetch(`${API_BASE}/api/holo/run_snapshot`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(body),
  });

  if (!res.ok) {
    // return a typed error payload (so callers can safely read status)
    const text = await res.text().catch(() => "");
    return { status: "error", metrics: { http_status: res.status, body: text } };
  }

  const json = (await res.json()) as any;
  // normalize: backend might return {result: ...} or direct
  return (json?.result ?? json) as HoloRunResult;
}