// src/lib/api/holo.ts
import type { HoloIR, HoloSourceView } from "../types/holo";

const API_BASE = import.meta.env.VITE_API_BASE ?? "http://localhost:8080";

// What DevTools/QFC sends when you press "Export as .holo"
export interface HoloExportViewCtx {
  tick?: number;
  reason?: string;                // "devtools_manual_export", "timefold_snapshot", ...
  source_view?: HoloSourceView;   // "qfc", "code", ...
  frame?: string;                 // "original", "mutated", "replay"

  // Optional lenses/metrics you want to bake into the holo:
  views?: HoloIR["views"];
  metrics?: Partial<HoloIR["field"]["metrics"]>;
  tags?: string[];

  // Allow extra arbitrary stuff without breaking typing
  [key: string]: unknown;
}

/**
 * Export a fresh Holo snapshot for a container.
 * Mirrors backend: POST /api/holo/export/{container_id}
 */
export async function exportHoloForContainer(
  containerId: string,
  viewCtx: HoloExportViewCtx,
  revision = 1,
): Promise<HoloIR> {
  const url = `${API_BASE}/api/holo/export/${encodeURIComponent(
    containerId,
  )}?revision=${encodeURIComponent(revision)}`;

  const res = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(viewCtx ?? {}),
  });

  if (!res.ok) {
    const text = await res.text().catch(() => "");
    console.warn(
      "[HoloAPI] exportHoloForContainer failed:",
      res.status,
      text,
    );
    throw new Error(`Holo export failed (${res.status})`);
  }

  const data = (await res.json()) as HoloIR;
  return data;
}

/**
 * (Optional / future)
 * If you later add a backend route:
 *   GET /api/holo/container/{id}/latest
 * you can keep this helper and hit that.
 */
export async function fetchLatestHoloForContainer(
  containerId: string,
): Promise<HoloIR | null> {
  const res = await fetch(
    `${API_BASE}/api/holo/container/${encodeURIComponent(containerId)}/latest`,
  );

  if (!res.ok) {
    console.warn("[HoloAPI] Failed to fetch latest holo:", res.status);
    return null;
  }

  const data = (await res.json()) as HoloIR;
  return data;
}