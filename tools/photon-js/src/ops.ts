// tools/photon-js/src/ops.ts
import fs from "node:fs";
import path from "node:path";

export type OpSpec = {
  glyph: string;
  name: string;
  arity: "1" | "2" | "n";
  precedence: number;
  associativity: "left" | "right" | "none";
  laws?: { commutative?: boolean; associative?: boolean; idempotent?: boolean };
  lowering?: { call?: string };
  hover?: string;
  examples?: string[];
};

export function loadOps(jsonPath?: string): OpSpec[] {
  const p = jsonPath ?? path.resolve(process.cwd(), "backend/modules/photonlang/ops/operators.json");
  return JSON.parse(fs.readFileSync(p, "utf8")).operators as OpSpec[];
}

export function makeCheatsheetMap() {
  const map: Record<string,string> = {};
  for (const op of loadOps()) map[op.glyph] = op.hover ?? op.name;
  return map;
}