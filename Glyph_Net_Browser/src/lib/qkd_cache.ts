// apps/web/src/lib/qkd_cache.ts
// Gateway-backed QKD lease fetcher.
// Always call the local radio gateway (/radio); in go-live it proxies to the real agent.
// Returns an object that ALWAYS has a `lease` property so callers can do:
//   const { lease } = await getLease(...)

export type AAD = "glyph" | "voice_note" | "voice_frame";

const QKD_PREFIX = "/radio";

/**
 * Fetch a QKD lease via the local gateway.
 * The server may return either `{ ok, lease:{...} }` or a flat `{ kid, ... }`.
 * We normalize to always return an object with a `lease` property.
 */
export async function getLease(
  aad: AAD,
  kg: string,
  localWA: string,
  remoteWA: string
) {
  const r = await fetch(`${QKD_PREFIX}/qkd/lease`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ aad, kg, localWA, remoteWA }),
  });
  if (!r.ok) throw new Error(`lease ${r.status}`);

  const j = await r.json();
  return j && typeof j === "object" && "lease" in j ? j : { lease: j };
}

/** Legacy no-ops kept for compatibility with older imports. */
export function bumpSeq(..._args: unknown[]): void { /* noop */ }
export function currentSeq(..._args: unknown[]): number { return 0; }