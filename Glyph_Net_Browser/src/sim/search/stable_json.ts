import type { Json } from "./types";

/** Stable JSON stringify: sorts object keys recursively for deterministic bundles. */
export function stableStringify(x: Json): string {
  return JSON.stringify(stabilize(x));
}

function stabilize(x: Json): Json {
  if (x === null) return null;
  if (typeof x === "boolean" || typeof x === "number" || typeof x === "string") return x;

  if (Array.isArray(x)) return x.map(stabilize);

  // object
  const obj = x as Record<string, Json>;
  const out: Record<string, Json> = {};
  const keys = Object.keys(obj).sort();
  for (const k of keys) out[k] = stabilize(obj[k]);
  return out;
}
