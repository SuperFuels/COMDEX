import fs from "node:fs";
import path from "node:path";

export type OperatorSpec = { glyph: string; name: string; arity: string; };
export type Registry = Record<string, OperatorSpec>;

export function loadRegistry(): Registry {
  const p = process.env.PHOTON_OPS_JSON ??
    path.resolve(process.cwd(), "backend/modules/photonlang/ops/operators.json");
  const raw = JSON.parse(fs.readFileSync(p, "utf8"));
  const out: Registry = {};
  for (const op of raw.operators as OperatorSpec[]) out[op.glyph] = op;
  return out;
}