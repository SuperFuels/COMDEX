import type { QFCFrame } from "../../QFCViewport"; // adjust relative path to your QFCViewport

export type TopoNode = { id: string; w?: number };
export type TopoEdge = { a: string; b: string; w?: number };

export type QFCTopology = {
  epoch: number; // monotonic schedule step
  nodes: TopoNode[];
  edges: TopoEdge[];
  gate?: number; // 0..1
};

function clamp01(v: number) {
  return Math.max(0, Math.min(1, v));
}

// tiny deterministic PRNG (mulberry32)
function mulberry32(seed: number) {
  let t = seed >>> 0;
  return () => {
    t += 0x6d2b79f5;
    let x = Math.imul(t ^ (t >>> 15), 1 | t);
    x ^= x + Math.imul(x ^ (x >>> 7), 61 | x);
    return ((x ^ (x >>> 14)) >>> 0) / 4294967296;
  };
}

function hashStr32(s: string) {
  // FNV-ish 32-bit
  let h = 2166136261;
  for (let i = 0; i < s.length; i++) {
    h ^= s.charCodeAt(i);
    h = Math.imul(h, 16777619);
  }
  return h >>> 0;
}

function pickDistinctPairs(ids: string[], want: number, rng: () => number) {
  const out: Array<[string, string]> = [];
  const n = ids.length;
  if (n < 2) return out;

  const seen = new Set<string>();
  let guard = 0;

  while (out.length < want && guard++ < want * 20) {
    const a = ids[Math.floor(rng() * n)];
    let b = ids[Math.floor(rng() * n)];
    if (b === a) continue;

    // undirected uniqueness key
    const k = a < b ? `${a}|${b}` : `${b}|${a}`;
    if (seen.has(k)) continue;

    seen.add(k);
    out.push([a, b]);
  }

  return out;
}

/**
 * Stage C bootstrap: attach / update a deterministic adjacency graph.
 * - epoch changes every 2 seconds: floor(t / 2000)
 * - edges are re-sampled each epoch from a seeded PRNG
 */
export function ensureTopology(frame: QFCFrame, seed: number): QFCFrame {
  const t = Number(frame?.t ?? Date.now());
  const epoch = Math.floor(t / 2000);

  const existing = (frame as any).topology as QFCTopology | undefined;
  if (existing && existing.epoch === epoch) {
    // already good for this epoch
    return frame;
  }

  const chirality: 1 | -1 =
    ((frame as any)?.flags?.chirality ?? 1) === -1 ? -1 : 1;

  // derive a stable epoch-seed
  const base = (seed >>> 0) ^ (epoch * 0x9e3779b9);
  const rng = mulberry32(base);

  // node set (stable IDs; you can later swap this to telemetry-driven IDs)
  const N = 10; // tweak as needed
  const nodes: TopoNode[] = Array.from({ length: N }).map((_, i) => {
    const id = `n${i}`;
    return { id, w: 0.6 + rng() * 1.4 };
  });

  const ids = nodes.map((n) => n.id);

  // edge count changes slightly by epoch (but deterministic)
  const edgeCount = Math.max(8, Math.min(22, Math.floor(10 + rng() * 12)));

  const pairs = pickDistinctPairs(ids, edgeCount, rng);

  const edges: TopoEdge[] = pairs.map(([a0, b0]) => {
    // chirality can deterministically flip direction for display semantics
    // (topology is still effectively undirected unless you interpret direction)
    const flip = chirality === -1 && (hashStr32(`${a0}|${b0}|${epoch}`) & 1) === 1;
    const a = flip ? b0 : a0;
    const b = flip ? a0 : b0;

    return {
      a,
      b,
      w: 0.5 + rng() * 2.0,
    };
  });

  // optional gate derived from sigma/coupling if present
  const gate = clamp01(
    Number((frame as any)?.sigma ?? (frame as any)?.coupling_score ?? 1),
  );

  const topology: QFCTopology = { epoch, nodes, edges, gate };

  // return a new frame object with topology attached
  return {
    ...frame,
    topology,
  } as any;
}