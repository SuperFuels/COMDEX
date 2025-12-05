// src/lib/api/holo.ts
import type { HoloIR, HoloSourceView } from "../types/holo";

const API_BASE = import.meta.env.VITE_API_BASE ?? "http://localhost:8080";

// What DevTools/QFC sends when you press "Export as .holo"
export interface HoloExportViewCtx {
  tick?: number;
  reason?: string;              // "devtools_manual_export", "timefold_snapshot", ...
  source_view?: HoloSourceView; // "qfc", "code", ...
  frame?: string;               // "original", "mutated", "replay"

  // Optional lenses/metrics you want to bake into the holo:
  views?: HoloIR["views"];
  metrics?: Partial<HoloIR["field"]["metrics"]>;
  tags?: string[];

  // Allow extra arbitrary stuff without breaking typing
  [key: string]: unknown;
}

export interface HoloIndexEntry {
  container_id: string;
  holo_id: string;
  revision: number;
  tick: number;
  created_at: string;
  tags: string[];
}

// Full file-based index entry (from /container/{container_id}/index)
export interface HoloFileIndexEntry extends HoloIndexEntry {
  path: string;
  mtime: number;
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

  return (await res.json()) as HoloIR;
}

/**
 * Fetch the latest holo snapshot for a container (if any).
 * GET /api/holo/container/{container_id}/latest
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

  return (await res.json()) as HoloIR;
}

/**
 * List holo snapshot history for a container (lightweight logical index).
 * GET /api/holo/container/{container_id}/history
 *
 * Backed by holo_index.json in the backend.
 */
export async function listHolosForContainer(
  containerId: string,
): Promise<HoloIndexEntry[]> {
  const res = await fetch(
    `${API_BASE}/api/holo/container/${encodeURIComponent(
      containerId,
    )}/history`,
  );

  if (!res.ok) {
    console.warn("[HoloAPI] Failed to fetch holo history:", res.status);
    return [];
  }

  return (await res.json()) as HoloIndexEntry[];
}

/**
 * Low-level file index for a container.
 * GET /api/holo/container/{container_id}/index
 *
 * Reads directly from .holo.json files on disk.
 */
export async function listHoloFileIndexForContainer(
  containerId: string,
): Promise<HoloFileIndexEntry[]> {
  const res = await fetch(
    `${API_BASE}/api/holo/container/${encodeURIComponent(
      containerId,
    )}/index`,
  );

  if (!res.ok) {
    console.warn("[HoloAPI] Failed to fetch holo file index:", res.status);
    return [];
  }

  return (await res.json()) as HoloFileIndexEntry[];
}

/**
 * Fetch a specific holo snapshot by (tick, revision).
 * (Requires matching backend route:
 *  GET /api/holo/container/{container_id}/at?tick=...&revision=...)
 */
export async function fetchHoloAtTick(
  containerId: string,
  tick: number,
  revision = 1,
): Promise<HoloIR | null> {
  const url = `${API_BASE}/api/holo/container/${encodeURIComponent(
    containerId,
  )}/at?tick=${encodeURIComponent(tick)}&revision=${encodeURIComponent(
    revision,
  )}`;

  const res = await fetch(url);

  if (!res.ok) {
    console.warn(
      "[HoloAPI] Failed to fetch holo at tick:",
      tick,
      "rev:",
      revision,
      "status:",
      res.status,
    );
    return null;
  }

  return (await res.json()) as HoloIR;
}

/**
 * Global holo index search.
 * GET /api/holo/index/search?container_id=...&tag=...
 *
 * Uses the global holo_index.json on the backend.
 */
export async function searchHoloIndex(params: {
  containerId?: string;
  tag?: string;
}): Promise<HoloIndexEntry[]> {
  const query = new URLSearchParams();
  if (params.containerId) query.set("container_id", params.containerId);
  if (params.tag) query.set("tag", params.tag);

  const res = await fetch(
    `${API_BASE}/api/holo/index/search?${query.toString()}`,
  );

  if (!res.ok) {
    console.warn("[HoloAPI] Failed to search holo index:", res.status);
    return [];
  }

  return (await res.json()) as HoloIndexEntry[];
}