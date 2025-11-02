#!/usr/bin/env node
import fs from "node:fs";
import path from "node:path";
import Parser from "tree-sitter";
import JavaScript from "tree-sitter-javascript";
import { typescript as TypeScript } from "tree-sitter-typescript";

type Mode = "compress" | "expand";

type TokenMap = {
  keywords?: Record<string, string>;
  operators: Record<string, string>;
  punctuation: Record<string, string>;
};

function loadMap(): TokenMap {
  const mapPath =
    process.env.PHOTON_JS_MAP ??
    path.resolve(
      process.cwd(),
      "backend/modules/photonlang_js/javascript_token_map.json"
    );
  return JSON.parse(fs.readFileSync(mapPath, "utf8"));
}

function readSource(arg?: string): string {
  if (!arg || arg === "-") return fs.readFileSync(0, "utf8");
  return fs.readFileSync(arg, "utf8");
}

type Range = [number, number];

function invertMap(m: Record<string, string>): Record<string, string> {
  const out: Record<string, string> = {};
  for (const [k, v] of Object.entries(m)) out[v] = k;
  return out;
}

function buildReplacer(map: Record<string, string>) {
  const esc = (s: string) => s.replace(/[-/\\^$*+?.()|[\]{}]/g, "\\$&");
  const entries = Object.entries(map).sort((a, b) => b[0].length - a[0].length);
  if (entries.length === 0) return (s: string) => s;
  const re = new RegExp(entries.map(([k]) => esc(k)).join("|"), "g");
  const tbl = new Map(entries);
  return (s: string) => s.replace(re, (m) => tbl.get(m) ?? m);
}

/**
 * Collect “code” ranges using tree-sitter:
 * - Mask strings, comments, regexes, full template strings
 * - But *unmask* template_substitution nodes (${ ... }) so expressions transform
 */
function computeCodeRanges(src: string, lang: "js" | "ts"): Range[] {
  const parser = new Parser();
  parser.setLanguage(lang === "ts" ? (TypeScript as any) : (JavaScript as any));
  const tree = parser.parse(src);

  const maskTypes = new Set(["string", "comment", "regex", "template_string"]);
  const addBackTypes = new Set(["template_substitution"]);

  const masks: Range[] = [];
  const addBack: Range[] = [];

  const stack = [tree.rootNode];
  while (stack.length) {
    const n = stack.pop()!;
    if (maskTypes.has(n.type)) masks.push([n.startIndex, n.endIndex]);
    if (addBackTypes.has(n.type)) addBack.push([n.startIndex, n.endIndex]);
    for (const c of n.children) stack.push(c);
  }

  // helpers
  const merge = (rs: Range[]) => {
    if (!rs.length) return rs;
    rs.sort((a, b) => a[0] - b[0]);
    const out: Range[] = [[...rs[0]] as Range];
    for (let i = 1; i < rs.length; i++) {
      const [s0, s1] = out[out.length - 1];
      const [e0, e1] = rs[i];
      if (e0 <= s1) out[out.length - 1][1] = Math.max(s1, e1);
      else out.push([e0, e1]);
    }
    return out;
  };

  const subtract = (base: Range[], cut: Range[]) => {
    const out: Range[] = [];
    for (const [b0, b1] of base) {
      let segs: Range[] = [[b0, b1]];
      for (const [c0, c1] of cut) {
        const next: Range[] = [];
        for (const [s0, s1] of segs) {
          if (c1 <= s0 || c0 >= s1) {
            next.push([s0, s1]);
          } else {
            if (c0 > s0) next.push([s0, Math.min(c0, s1)]);
            if (c1 < s1) next.push([Math.max(c1, s0), s1]);
          }
        }
        segs = next;
      }
      out.push(...segs);
    }
    return merge(out);
  };

  const whole: Range[] = [[0, src.length]];
  const codeMinusMasks = subtract(whole, merge(masks));
  // Add back ${ ... } expression pockets from template strings
  return merge([...codeMinusMasks, ...addBack]);
}

function processCode(
  src: string,
  dir: Mode,
  tmap: TokenMap,
  lang: "js" | "ts"
): string {
  const opMap = dir === "compress" ? tmap.operators : invertMap(tmap.operators);
  const puncMap =
    dir === "compress" ? tmap.punctuation : invertMap(tmap.punctuation);

  const replaceOps = buildReplacer(opMap);
  const replacePunc = buildReplacer(puncMap);

  const ranges = computeCodeRanges(src, lang);
  let out = "";
  let idx = 0;
  for (const [a, b] of ranges) {
    if (idx < a) out += src.slice(idx, a); // pass-through masked (strings/comments/etc.)
    const chunk = src.slice(a, b);
    out += replacePunc(replaceOps(chunk)); // transform code only
    idx = b;
  }
  if (idx < src.length) out += src.slice(idx);
  return out;
}

function usage(): never {
  console.error("Usage: photon-js <compress|expand> <js|ts> [FILE|-]");
  process.exit(2);
}

(function main() {
  const [, , cmd, flavor, file] = process.argv;
  if (
    (cmd !== "compress" && cmd !== "expand") ||
    (flavor !== "js" && flavor !== "ts")
  )
    usage();

  const src = readSource(file);
  const map = loadMap();
  const out = processCode(src, cmd as Mode, map, flavor as "js" | "ts");
  process.stdout.write(out);
})();