// src/lib/api/wormholes.ts
// Client for: GET /api/wormhole/resolve?name=<...>

export type ResolveRecord = {
  /** Normalized wormhole name, e.g. "tesseract_hq.tp" */
  name: string;
  /** Optional source/target ids if the backend includes them */
  from?: string;
  to?: string;

  /** Canonical container URI, e.g. "ucs://local/tesseract_hq#container" */
  address: string;

  /** Extra metadata from the registry */
  meta?: any;

  /** Optional expanded container record */
  container?: {
    address: string;
    kind: string;
    meta?: any;
  };
};

/** Exported for consumers (ContainerView, etc.) */
export type ResolveReply = ResolveRecord;

/** Normalizes inputs like "🌀tesseract_hq" -> "tesseract_hq.tp" (lowercased) */
export function normalizeWormholeName(input: string): string {
  let v = (input || "").trim().replace(/^🌀/u, "");
  if (!/\.tp$/i.test(v)) v = `${v}.tp`;
  return v.toLowerCase();
}

/** Resolve a wormhole name to a concrete container record */
export async function resolveWormhole(
  rawName: string,
  signal?: AbortSignal
): Promise<ResolveReply> {
  const name = normalizeWormholeName(rawName);
  const res = await fetch(`/api/wormhole/resolve?name=${encodeURIComponent(name)}`, { signal });
  if (!res.ok) {
    throw new Error(`Resolver HTTP ${res.status}`);
  }
  return res.json();
}