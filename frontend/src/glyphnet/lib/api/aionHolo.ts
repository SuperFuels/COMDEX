// Glyph_Net_Browser/src/lib/api/aionHolo.ts

export type AionMemorySeed = {
  seed_id: string;
  container_id: string;
  kind: string; // "memory_entry"
  label: string;
  created_at: string;
  tags: string[];
  payload: {
    label: string;
    timestamp: string;
    content: any;
    source?: string;
    glyph?: any;
    glyph_tree?: any;
    scroll_preview?: any;
    scroll_tree?: any;
    [key: string]: any;
  };
};

export type AionRulebookSeed = {
  seed_id: string;
  container_id: string;
  rulebook_id: string;
  created_at: string;
  updated_at: string;
  usage_count: number;
  tags: string[];
  payload: {
    rulebook_id: string;
    name?: string;
    description?: string;
    domains?: string[] | null;
    metrics?: {
      Φ_coherence?: number;
      Φ_entropy?: number;
      SQI?: number;
    };
    mutations?: any[];
    usage_count?: number;
    last_used?: number | string | null;
    [key: string]: any;
  };
};

export type CombinedAionHoloSeeds = {
  memory: AionMemorySeed[];
  rulebooks: AionRulebookSeed[];
};

async function fetchJson<T>(url: string, init?: RequestInit): Promise<T> {
  const res = await fetch(url, {
    credentials: "same-origin",
    ...init,
  });

  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(
      `Request failed (${res.status} ${res.statusText}) for ${url}: ${text}`,
    );
  }

  return res.json() as Promise<T>;
}

/**
 * Fetch combined AION holo seeds (memory + rulebooks).
 * Backend route: GET /api/holo/aion/seeds/combined
 */
export async function fetchCombinedAionHoloSeeds(
  limitMemory: number = 32,
  signal?: AbortSignal,
): Promise<CombinedAionHoloSeeds> {
  const url = `/api/holo/aion/seeds/combined?limit_memory=${encodeURIComponent(
    String(limitMemory),
  )}`;

  return fetchJson<CombinedAionHoloSeeds>(url, { signal });
}

/**
 * Fetch only memory-side seeds.
 * Backend route: GET /api/holo/aion/seeds/memory
 */
export async function fetchAionMemorySeeds(
  limit: number = 32,
  signal?: AbortSignal,
): Promise<AionMemorySeed[]> {
  const url = `/api/holo/aion/seeds/memory?limit=${encodeURIComponent(
    String(limit),
  )}`;
  return fetchJson<AionMemorySeed[]>(url, { signal });
}

/**
 * Fetch only rulebook-side seeds.
 * Backend route: GET /api/holo/aion/seeds/rulebooks
 */
export async function fetchAionRulebookSeeds(
  signal?: AbortSignal,
): Promise<AionRulebookSeed[]> {
  const url = `/api/holo/aion/seeds/rulebooks`;
  return fetchJson<AionRulebookSeed[]>(url, { signal });
}