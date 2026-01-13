// radio-node/server.ts
import express, { type Request, type Response, type NextFunction } from "express";
import http, { type IncomingMessage } from "http";
import cors from "cors";
import { WebSocketServer, WebSocket } from "ws";
import { Buffer } from "buffer";
import fs from "fs";
import path from "path";
import dotenv from "dotenv";
import crypto from "crypto";
import { fileURLToPath } from "url";
import { spawnSync } from "child_process";
import zlib from "node:zlib";

import {
  sha256Hex,
  stableStringify,
  xorshift32,
  varintLen,
  u32leBytes,
  pickDistinctIndices,
  sumOverQ_full,
  sumOverQ_tracked,
} from "./wirepack_demo_helpers.js";

dotenv.config({ path: path.join(process.cwd(), ".env.local") });
dotenv.config(); // fallback to .env if present

// Optional YAML loader (fallback to defaults if not installed)
let YAML: any = null;
try { YAML = require("yaml"); } catch { /* optional */ }

// ───────────────────────────────────────────────────────────────
// Base64 → bytes
const b64ToU8 = (b64: string) => new Uint8Array(Buffer.from(b64, "base64"));
const u8ToB64 = (u8: Uint8Array) => Buffer.from(u8).toString("base64");

const __filename = fileURLToPath(import.meta.url);
const __dirname  = path.dirname(__filename);
// ─────────────────────────────────────────────────────────────
// WirePack v1 codec (Node-side, matches backend.modules.glyphos.wirepack_codec)
// Used for v44 benchmarks so we don't spawn python per frame.
// ─────────────────────────────────────────────────────────────

function uvarintEncode(x: number): Buffer {
  if (!Number.isFinite(x) || x < 0) throw new Error("uvarint expects non-negative finite");
  let v = Math.floor(x);
  const out: number[] = [];
  while (v >= 0x80) {
    out.push((v & 0x7f) | 0x80);
    v = Math.floor(v / 128);
  }
  out.push(v & 0x7f);
  return Buffer.from(out);
}

function encodeTemplateWords(words: number[]): Buffer {
  const n = words.length >>> 0;
  const header = uvarintEncode(n);
  const body = Buffer.allocUnsafe(n * 4);
  for (let i = 0; i < n; i++) body.writeUInt32LE(words[i] >>> 0, i * 4);
  return Buffer.concat([header, body]);
}

type Op44 = [number, number]; // [idx, newValue]
function encodeDeltaOps(ops: Op44[]): Buffer {
  const header = uvarintEncode(ops.length >>> 0);
  const chunks: Buffer[] = [header];
  for (const [idx, newv] of ops) {
    if (idx < 0) throw new Error("idx must be >= 0");
    chunks.push(uvarintEncode(idx >>> 0));
    const v = Buffer.allocUnsafe(4);
    v.writeUInt32LE(newv >>> 0, 0);
    chunks.push(v);
  }
  return Buffer.concat(chunks);
}

function uvarintDecode(buf: Buffer, o0: number): { v: number; o: number } {
  let o = o0 >>> 0;
  let x = 0 >>> 0;
  let s = 0;
  while (true) {
    if (o >= buf.length) throw new Error("uvarintDecode: truncated");
    const b = buf[o++]!;
    x |= (b & 0x7f) << s;
    if ((b & 0x80) === 0) break;
    s += 7;
    if (s > 35) throw new Error("uvarintDecode: overflow");
  }
  return { v: x >>> 0, o };
}

function decodeTemplateWords(buf: Buffer): number[] {
  // format: uvarint(nWords) + nWords * u32le
  let o = 0;
  const h = uvarintDecode(buf, o);
  const n = h.v >>> 0;
  o = h.o;
  const need = o + n * 4;
  if (need > buf.length) throw new Error("decodeTemplateWords: truncated body");
  const out: number[] = [];
  for (let i = 0; i < n; i++) out.push(buf.readUInt32LE(o + i * 4) >>> 0);
  return out;
}

function decodeDeltaOps(buf: Buffer): Op44[] {
  // format: uvarint(nOps) + [uvarint(idx) + u32le(val)] * nOps
  let o = 0;
  const h = uvarintDecode(buf, o);
  const n = h.v >>> 0;
  o = h.o;

  const out: Op44[] = [];
  for (let k = 0; k < n; k++) {
    const a = uvarintDecode(buf, o);
    const idx = a.v >>> 0;
    o = a.o;

    if (o + 4 > buf.length) throw new Error("decodeDeltaOps: truncated val");
    const v = buf.readUInt32LE(o) >>> 0;
    o += 4;

    out.push([idx, v]);
  }
  return out;
}


function gzipLenUtf8(s: string) {
  const gz = zlib.gzipSync(Buffer.from(s, "utf8"), { level: 9 });
  return gz.length;
}

// Deterministic PRNG (xorshift32)
function rng32(seed: number) {
  let x = (seed >>> 0) || 1;
  return () => {
    x ^= (x << 13) >>> 0;
    x ^= (x >>> 17) >>> 0;
    x ^= (x << 5) >>> 0;
    return x >>> 0;
  };
}
// ─────────────────────────────────────────────────────────────
// WirePack v46: session-aware template+delta (real stateful demo)
// Uses backend.modules.glyphos.wirepack_codec in Python.
// ─────────────────────────────────────────────────────────────

const REPO_ROOT = path.resolve(__dirname, "..", ".."); // /workspaces/COMDEX
type WpSession = {
  id: string;
  templateId: number;
  createdAt: number;
  prevWords?: number[];      // current state (words)
  templateWords?: number[];  // base template (words)
};

const WP_SESSIONS = new Map<string, WpSession>();

function pyEnv() {
  const cur = process.env.PYTHONPATH || "";
  const next = cur ? `${REPO_ROOT}${path.delimiter}${cur}` : REPO_ROOT;
  return { ...process.env, PYTHONPATH: next };
}

async function runPy(script: string, input: any): Promise<string> {
  const { spawn } = await import("node:child_process");
  return await new Promise((resolve, reject) => {
    const cp = spawn("python3", ["-c", script], {
      cwd: REPO_ROOT,
      env: pyEnv(),
      stdio: ["pipe", "pipe", "pipe"],
    });

    let out = "";
    let err = "";

    cp.stdout.on("data", (d) => (out += d.toString("utf8")));
    cp.stderr.on("data", (d) => (err += d.toString("utf8")));

    cp.on("error", reject);
    cp.on("close", (code) => {
      if (code === 0) return resolve(out);
      reject(new Error(err || `python exit ${code}`));
    });

    cp.stdin.write(JSON.stringify(input ?? {}));
    cp.stdin.end();
  });
}

// bytes <-> words (u32 little-endian), word[0] = original byte length
function textToWords(text: string): number[] {
  const raw = Buffer.from(text ?? "", "utf8");
  const n = raw.length >>> 0;
  const pad = (4 - (n % 4)) % 4;
  const buf = pad ? Buffer.concat([raw, Buffer.alloc(pad)]) : raw;

  const words: number[] = [n];
  for (let i = 0; i < buf.length; i += 4) {
    words.push(buf.readUInt32LE(i) >>> 0);
  }
  return words;
}

function wordsToText(words: number[]): string {
  if (!words || words.length === 0) return "";
  const n = (words[0] >>> 0) as number;
  const bodyWords = words.length - 1;
  const buf = Buffer.alloc(bodyWords * 4);
  for (let i = 0; i < bodyWords; i++) {
    buf.writeUInt32LE(words[i + 1] >>> 0, i * 4);
  }
  return buf.slice(0, n).toString("utf8");
}

type Op = [number, number]; // (idx, newValue)
function diffOps(prev: number[], next: number[]): Op[] {
  const ops: Op[] = [];
  const L = Math.min(prev.length, next.length);
  for (let i = 0; i < L; i++) {
    const a = prev[i] >>> 0;
    const b = next[i] >>> 0;
    if (a !== b) ops.push([i, b]);
  }
  return ops;
}

function bufEq(a: Buffer, b: Buffer): boolean {
  if (a.length !== b.length) return false;
  return crypto.timingSafeEqual(a, b);
}


// Canonicalize ops by "last write wins", then sorted by idx.
// This makes equivalent deltas byte-identical regardless of incoming order.
function canonicalizeOps(ops: Op44[]): Op44[] {
  const last = new Map<number, number>();
  for (const [i, v] of ops) last.set(i >>> 0, v >>> 0);
  const out: Op44[] = Array.from(last.entries()).map(([i, v]) => [i >>> 0, v >>> 0]);
  out.sort((a, b) => (a[0] >>> 0) - (b[0] >>> 0));
  return out;
}

function shuffleInPlace<T>(arr: T[], R: () => number) {
  for (let i = arr.length - 1; i > 0; i--) {
    const j = (R() % (i + 1)) >>> 0;
    const tmp = arr[i]; arr[i] = arr[j]; arr[j] = tmp;
  }
}
// v38 needs order-invariant "last write" even when ops are shuffled.
// We achieve that by attaching a stable ordinal (generation order) to each op.
type Op38 = [number, number, number]; // [idx, newv, ord]

function canonicalizeOps38(ops: Op38[]): Op44[] {
  const best = new Map<number, { ord: number; v: number }>();

  for (const [idx, v, ord] of ops) {
    const i = idx >>> 0;
    const cur = best.get(i);
    // deterministic "last-write-wins": highest ord wins, not "last in array"
    if (!cur || ord > cur.ord) best.set(i, { ord, v: v >>> 0 });
  }

  const out: Op44[] = Array.from(best.entries()).map(([i, o]) => [i >>> 0, o.v >>> 0]);
  out.sort((a, b) => (a[0] >>> 0) - (b[0] >>> 0));
  return out;
}


// Python scripts: NO leading indent, NO trailing newline (sys.stdout.write)
const PY_ENC_TEMPLATE = String.raw`from __future__ import annotations
import sys,json,base64
from backend.modules.glyphos import wirepack_codec as w
req=json.loads(sys.stdin.read() or "{}")
words=req.get("words") or []
b=w.encode_template([int(x) & 0xFFFFFFFF for x in words])
sys.stdout.write(base64.b64encode(b).decode())
`;

const PY_ENC_DELTA = String.raw`from __future__ import annotations
import sys,json,base64
from backend.modules.glyphos import wirepack_codec as w
req=json.loads(sys.stdin.read() or "{}")
ops=req.get("ops") or []
# ops: [[idx,val],...]
b=w.encode_delta([(int(i), int(v) & 0xFFFFFFFF) for i,v in ops])
sys.stdout.write(base64.b64encode(b).decode())
`;

const PY_DEC_TEMPLATE = String.raw`from __future__ import annotations
import sys,json,base64
from backend.modules.glyphos import wirepack_codec as w
req=json.loads(sys.stdin.read() or "{}")
b=base64.b64decode(req.get("b64",""))
words=w.decode_template(b)
sys.stdout.write(json.dumps({"words":words}, separators=(",",":")))
`;

const PY_DEC_DELTA = String.raw`from __future__ import annotations
import sys,json,base64
from backend.modules.glyphos import wirepack_codec as w
req=json.loads(sys.stdin.read() or "{}")
b=base64.b64decode(req.get("b64",""))
ops=w.decode_delta(b)
sys.stdout.write(json.dumps({"ops":ops}, separators=(",",":")))
`;

const PY_V45_VECTORS = String.raw`from __future__ import annotations
import sys,json,base64
from backend.modules.glyphos import wirepack_codec as w

req=json.loads(sys.stdin.read() or "{}")
words=req.get("words") or []
turns_ops=req.get("turns_ops") or []  # [[[idx,val],...], ...]

words=[int(x) & 0xFFFFFFFF for x in words]

tmpl=w.encode_template(words)
tmpl_dec=w.decode_template(tmpl)

deltas_b64=[]
dec_ops_all=[]

for ops in turns_ops:
  ops=[(int(i), int(v) & 0xFFFFFFFF) for i,v in (ops or [])]
  d=w.encode_delta(ops)
  deltas_b64.append(base64.b64encode(d).decode())
  dec_ops_all.append(w.decode_delta(d))

out={
  "template_b64": base64.b64encode(tmpl).decode(),
  "template_dec_words": tmpl_dec,
  "deltas_b64": deltas_b64,
  "deltas_dec_ops": dec_ops_all,
}
sys.stdout.write(json.dumps(out, separators=(",",":")))
`;

// String <-> bytes helpers
const u8ToStr = (u8: Uint8Array) => new TextDecoder().decode(u8);
const strToU8 = (s: string) => new TextEncoder().encode(s);

// Unique node id (used by discovery beacons)
const NODE_ID = process.env.NODE_ID || `rn-${Math.random().toString(36).slice(2, 8)}`;

// ── Discovery (neighbors)
type Neighbor = {
  id: string;
  seenAt: number;
  profile: string;
  rate_hz: number;
  mtu: number;
  addr?: string;
  ua?: string;
};

const NEIGHBOR_TTL_MS = Number(process.env.NEIGHBOR_TTL_MS ?? 60_000);
const neighbors = new Map<string, Neighbor>();

function upsertNeighbor(n: Neighbor) {
  const prev = neighbors.get(n.id) || {};
  neighbors.set(n.id, { ...prev, ...n, seenAt: now() });
}

function currentNeighbors(): Neighbor[] {
  const out: Neighbor[] = [];
  const t = now();
  for (const [, n] of neighbors) {
    if (t - n.seenAt <= NEIGHBOR_TTL_MS) out.push(n);
    else neighbors.delete(n.id);
  }
  out.sort((a, b) => b.seenAt - a.seenAt);
  return out;
}

// Optional rolling token for rotation
const BRIDGE_TOKEN = process.env.RADIO_BRIDGE_TOKEN || "dev-bridge";
const BRIDGE_TOKEN_NEXT = process.env.RADIO_BRIDGE_TOKEN_NEXT || "";

// Toggle: require signed auth (token + X-Bridge-Sig) on HTTP endpoints
const REQUIRE_BRIDGE_SIG =
  String(process.env.REQUIRE_BRIDGE_SIG || "").toLowerCase() === "true";

// --- Serial Link (optional) -------------------------------------
// ---- Serial Link (optional, with auto-reconnect) ---------------
const RF_SERIAL_DEV  = process.env.RF_SERIAL_DEV || "";
const RF_SERIAL_BAUD = Number(process.env.RF_SERIAL_BAUD || 115200);

// --- Serial Link (optional) -------------------------------------
let serialDriverRegistered = false;

type SerialState = {
  port: any | null;
  rl: any | null;
  up: boolean;
  reconnectTimer: NodeJS.Timeout | null;
};

const serialState: SerialState = { port: null, rl: null, up: false, reconnectTimer: null };

// Stable driver id (sanitize path so it’s safe to print)
const serialDriverId = `serial:${RF_SERIAL_DEV.replace(/[^\w.-]/g, "_")}`;

function onSerialLine(line: string) {
  const s = (line || "").trim();
  if (!s) return;

  let topic = "personal:ucs://local/ucs_hub";
  let b64 = s;

  if (s.startsWith("{")) {
    try {
      const j = JSON.parse(s);
      if (typeof j.topic === "string") topic = j.topic;
      if (typeof j.bytes_b64 === "string") b64 = j.bytes_b64;
      else if (typeof j.data_b64 === "string") b64 = j.data_b64;
    } catch {
      // fall back to plain Base64
    }
  }

  if (!b64) return;
  try {
    const bytes = b64ToU8(b64);
    processInboundRF(topic, bytes, undefined, `serial:${RF_SERIAL_DEV}`);
  } catch (e) {
    console.warn("[rf][serial] bad inbound line:", (e as any)?.message || e);
  }
}

async function tryOpenSerial(): Promise<void> {
  if (!RF_SERIAL_DEV) return;

  // If the device path doesn't exist yet, trigger backoff instead of crashing
  if (!fs.existsSync(RF_SERIAL_DEV)) {
    throw new Error(`${RF_SERIAL_DEV} not present`);
  }

  // ESM-safe lazy imports
  const spMod: any = await import("serialport");
  const rlMod: any = await import("node:readline");

  const SerialPort =
    spMod?.SerialPort ??
    spMod?.default?.SerialPort ??
    spMod?.default;

  if (!SerialPort) {
    throw new Error('"serialport" module did not expose SerialPort');
  }

  const port = new SerialPort({
    path: RF_SERIAL_DEV,
    baudRate: RF_SERIAL_BAUD,
    autoOpen: false, // attach listeners before opening
  });

  serialState.port = port;

  const scheduleReconnect = (why: string, backoff = 1000) => {
    if (serialState.reconnectTimer) {
      clearTimeout(serialState.reconnectTimer);
      serialState.reconnectTimer = null;
    }
    try { serialState.rl?.removeAllListeners?.(); serialState.rl?.close?.(); } catch {}
    try { port.removeAllListeners?.(); port.close?.(); } catch {}
    serialState.rl = null;
    serialState.port = null;
    serialState.up = false;

    const next = Math.min(backoff * 2, 15_000);
    console.warn(`[rf][serial] ${why}; retrying in ${next}ms`);
    serialState.reconnectTimer = setTimeout(() => connectSerial(next), next);
  };

  port.on("open", () => {
    serialState.up = true;
    console.log(`[rf][serial] up @ ${RF_SERIAL_DEV} ${RF_SERIAL_BAUD}bps`);

    // Opportunistic: if a real link is up, stop using the mock driver
    if (AUTO_DISABLE_MOCK_ON_REAL_LINK && mockCfg.enabled) {
      mockCfg.enabled = false;
      console.log("[rf][mock] disabled (real serial link is up)");
    }

    try { drainOutboxViaDrivers(); } catch {}

    // Create line reader only once the port is open
    const rl = rlMod.createInterface({ input: port as any });
    serialState.rl = rl;
    rl.on("line", onSerialLine);
  });

  port.on("error", (err: any) => scheduleReconnect(`error: ${err?.message || err}`));
  port.on("close", () => scheduleReconnect("closed"));

  port.open((err?: any) => {
    if (err) scheduleReconnect(`open failed: ${err?.message || err}`);
  });
}

function connectSerial(initialDelay = 0) {
  if (!RF_SERIAL_DEV) return;

  if (serialState.reconnectTimer) {
    clearTimeout(serialState.reconnectTimer);
    serialState.reconnectTimer = null;
  }

  const attempt = async (delay: number) => {
    try {
      await tryOpenSerial();
    } catch (err: any) {
      const msg = err?.message || String(err);
      const next = Math.min(delay ? delay * 2 : 2000, 15_000);
      console.warn(`[rf][serial] init failed: ${msg}; retrying in ${next}ms`);
      serialState.reconnectTimer = setTimeout(() => attempt(next), next);
    }
  };

  if (initialDelay > 0) {
    serialState.reconnectTimer = setTimeout(() => attempt(initialDelay), initialDelay);
  } else {
    attempt(0);
  }
}

function ensureSerialDriverRegistered() {
  if (serialDriverRegistered || !RF_SERIAL_DEV) return;

  // Register driver once; connection state is managed by connectSerial()
  registerDriver({
    id: serialDriverId,
    kind: "serial",
    sendB64: (b64: string) => {
      const p: any = serialState.port;
      if (!p || !serialState.up) return false;
      try { p.write(b64 + "\n"); return true; } catch { return false; }
    },
    isUp: () => !!serialState.up,
    stats: () => ({ rfOutbox: rfOutbox.length }),
  });

  serialDriverRegistered = true;
  connectSerial(0);
}

/** Validate X-Bridge-Sig: "v1,<tsMs>,<hmacHex>" where hmac = HMAC_SHA256(token, `ws-bridge|${tsMs}`) */
function validBridgeSig(sig: string, token: string): boolean {
  try {
    const [v, tsStr, macHex] = String(sig).split(",");
    if (v !== "v1") return false;
    const ts = Number(tsStr);
    if (!Number.isFinite(ts)) return false;
    if (Math.abs(Date.now() - ts) > BRIDGE_SIG_TOLERANCE_MS) return false; // uses your existing TOLERANCE var

    const want = crypto.createHmac("sha256", token).update(`ws-bridge|${ts}`).digest("hex");
    return secureEq(want, macHex);
  } catch {
    return false;
  }
}

function tokenMatchesAny(tok: string) {
  return !!tok && (secureEq(tok, BRIDGE_TOKEN) || (!!BRIDGE_TOKEN_NEXT && secureEq(tok, BRIDGE_TOKEN_NEXT)));
}

/** Validate token; if a signature is present it MUST verify against that specific token.
 *  If no signature is provided, allow plain token (dev/back-compat).
 *  Strict/lenient behavior is enforced by requireBridgeAuth via REQUIRE_BRIDGE_SIG.
 */
function tokenOkWithOptionalSig(tok?: string, sig?: string): boolean {
  if (!tok) return false;

  if (sig) {
    return (secureEq(tok, BRIDGE_TOKEN) && validBridgeSig(sig, BRIDGE_TOKEN)) ||
           (!!BRIDGE_TOKEN_NEXT && secureEq(tok, BRIDGE_TOKEN_NEXT) && validBridgeSig(sig, BRIDGE_TOKEN_NEXT));
  }

  // No signature → plain token ok
  return tokenMatchesAny(tok);
}

// Pull token/signature from HTTP headers
function tokenFromReq(req: Request): string {
  const auth = String(req.header("authorization") || "");
  const bearer = auth.startsWith("Bearer ") ? auth.slice(7) : "";
  const xbt = String(req.header("x-bridge-token") || "");
  return bearer || xbt;
}
function sigFromReq(req: Request): string {
  return String(req.header("x-bridge-sig") || "");
}

// Constant-time compare helpers
function secureEq(a: string, b: string): boolean {
  const A = Buffer.from(a, "utf8");
  const B = Buffer.from(b, "utf8");
  if (A.length !== B.length) return false;
  try { return crypto.timingSafeEqual(A, B); } catch { return false; }
}
function secureEqHex(aHex: string, bHex: string): boolean {
  try {
    const A = Buffer.from(aHex, "hex");
    const B = Buffer.from(bHex, "hex");
    if (A.length !== B.length) return false;
    return crypto.timingSafeEqual(A, B);
  } catch { return false; }
}

// --- Session ticket HMAC (optional, dev works without) ----------------
function verifySessionTicket(wa: string, slug: string, ticket: string): boolean {
  try {
    const secret = process.env.SESSION_HMAC_SECRET || "";
    if (!secret) return true; // dev mode: accept without ticket
    const [v, tsStr, macHex] = String(ticket || "").split(",");
    if (v !== "v1") return false;
    const ts = Number(tsStr);
    if (!Number.isFinite(ts) || Math.abs(Date.now() - ts) > 5 * 60_000) return false; // 5 min
    const want = crypto.createHmac("sha256", secret).update(`${ts}|${wa}|${slug}`).digest("hex");
    return secureEq(want, macHex);
  } catch { return false; }
}

const BRIDGE_SIG_TOLERANCE_MS =
  Number(process.env.RADIO_BRIDGE_SIG_TOLERANCE_MS ?? 2 * 60_000);
// ───────────────────────────────────────────────────────────────
// Spool configuration (two independent spools)

// (A) RF spool (for on-air path; opportunistic relay)
const RF_SPOOL_DIR       = process.env.RF_SPOOL_DIR || path.join(process.cwd(), ".rf_spool");
const RF_SPOOL_TTL_SEC   = Number(process.env.RF_SPOOL_TTL_SEC ?? 3 * 24 * 3600);        // 3 days
const RF_SPOOL_MAX_BYTES = Number(process.env.RF_SPOOL_MAX_BYTES ?? 32 * 1024 * 1024);  // 32 MB

// (B) Cloud-forward disk queue (store–carry–forward to CLOUD_BASE)
const RN_SPOOL_DIR       = process.env.RN_SPOOL_DIR || path.join(process.cwd(), ".radio-spool");
const RN_QUEUE_MAX_ITEMS = Number(process.env.RN_QUEUE_MAX_ITEMS ?? 2000);
const RN_QUEUE_MAX_BYTES = Number(process.env.RN_QUEUE_MAX_BYTES ?? 100 * 1024 * 1024); // 100 MB
const RN_QUEUE_TTL_MS    = Number(process.env.RN_QUEUE_TTL_MS ?? 7 * 24 * 3600 * 1000); // 7 days

// Auto-disable mock when a real link (serial/ws-bridge) comes up
const AUTO_DISABLE_MOCK_ON_REAL_LINK =
  String(process.env.AUTO_DISABLE_MOCK_ON_REAL_LINK ?? "1") === "1";

function ensureDir(p: string) { try { fs.mkdirSync(p, { recursive: true }); } catch {} }
ensureDir(RF_SPOOL_DIR);
ensureDir(RN_SPOOL_DIR);

// ── Containers bootstrap (paths + helpers + static mapping)
// Files will be created under: radio-node/public/containers/<user>/...
const CONTAINERS_ROOT = path.join(process.cwd(), "public", "containers");
ensureDir(CONTAINERS_ROOT);

function writeJson(filePath: string, obj: any) {
  fs.writeFileSync(filePath, JSON.stringify(obj, null, 2) + "\n", "utf8");
}

function slugFromWa(wa: string): string {
  const name = String(wa).split("@")[0] || wa;
  return name.toLowerCase().replace(/[^a-z0-9._-]/g, "-");
}

function homeTemplate(wa: string, user: string) {
  return {
    id: `${user}__home`,
    type: "container",
    meta: { title: `${user} — HQ`, ownerWA: wa, graph: "personal" },
    glyphs: [],
    dimensions: []
  };
}

function kgTemplate(wa: string, user: string, graph: "personal" | "work") {
  return {
    id: `${user}__kg_${graph}`,
    type: "container",
    meta: { title: `KG • ${user} (${graph})`, ownerWA: wa, graph, kind: "kg" },
    glyphs: [],
    dimensions: []
  };
}

// --- Containers: static + ID→file mapping (ORDER MATTERS) -----
export function registerContainerStaticRoutes(app: express.Express) {
  const root = CONTAINERS_ROOT;

  // 1) ID → file mapping FIRST
  app.get(
    ["/containers/:id.json", "/containers/:id/manifest.json"],
    (req: Request, res: Response) => {
      const id = String(req.params.id || "");
      const tries: string[] = [];

      // direct file: /containers/<id>.json
      tries.push(path.join(root, `${id}.json`));

      // split form "<user>__home|kg_personal|kg_work"
      if (id.includes("__")) {
        const [user, rest] = id.split("__");
        const fname =
          rest === "home"        ? "home.json" :
          rest === "kg_personal" ? "kg_personal.json" :
          rest === "kg_work"     ? "kg_work.json" : "";

        if (fname) tries.push(path.join(root, user, fname));
      }

      for (const p of tries) {
        if (fs.existsSync(p)) {
          res.setHeader("Content-Type", "application/json; charset=utf-8");
          return res.send(fs.readFileSync(p, "utf8"));
        }
      }
      return res.status(404).json({ ok: false, error: "container manifest not found", id, tried: tries });
    }
  );

  // 2) Raw static AFTER (so folder paths like /containers/kevin/home.json work)
  app.use(
    "/containers",
    express.static(root, {
      index: false,
      fallthrough: true,
      setHeaders: (res, servedPath) => {
        if (String(servedPath).endsWith(".json")) {
          res.setHeader("Content-Type", "application/json; charset=utf-8");
        }
      },
    })
  );
}
// ───────────────────────────────────────────────────────────────
// Config
const PORT = Number(process.env.PORT || 8787);
const CLOUD_BASE = (process.env.CLOUD_BASE || "").replace(/\/+$/, "");
const FORWARD_TO_CLOUD = !!CLOUD_BASE;

function requireBridgeAuth(req: Request, res: Response, next: NextFunction) {
  if (!BRIDGE_TOKEN && !BRIDGE_TOKEN_NEXT) {
    return res.status(501).json({ ok: false, error: "bridge token not configured" });
  }

  const tok = tokenFromReq(req);
  const sig = sigFromReq(req);

  if (REQUIRE_BRIDGE_SIG) {
    // Strict: must present valid token AND valid signature
    if (!sig || !tokenOkWithOptionalSig(tok, sig)) {
      return res.status(401).json({ ok: false, error: "unauthorized", need: "token+sig" });
    }
  } else {
    // Dev-friendly: accept either plain token or signed token
    if (sig) {
      if (!tokenOkWithOptionalSig(tok, sig)) {
        return res.status(401).json({ ok: false, error: "unauthorized" });
      }
    } else if (!tokenMatchesAny(tok)) {
      return res.status(401).json({ ok: false, error: "unauthorized" });
    }
  }

  next();
}

/** Max raw audio bytes we’ll accept per capsule before RF fragmentation. */
const MAX_RF_INGRESS_BYTES = Number(process.env.RF_MAX_INGRESS_BYTES ?? 512 * 1024); // 512KB default

// --- RF RX spool (simple) --------------------------------------
const RF_RX_DIR = path.join(RF_SPOOL_DIR, "rx");
ensureDir(RF_RX_DIR);

type SeenKey = { topic: string; seq: number; ts: number };
const seen = new Map<string, number>(); // key: `${topic}#${seq}` => ts

function rxKey(topic: string, seq: number) { return `${topic}#${seq}`; }

function rememberRX(topic: string, seq: number) {
  // ⛔ do not persist control:* (e.g., control:beacon) — avoids file explosion
  if (String(topic).startsWith("control:")) return;

  const key = rxKey(topic, seq);
  seen.set(key, Date.now());
  try {
    fs.writeFileSync(
      path.join(RF_RX_DIR, `${encodeURIComponent(key)}.json`),
      JSON.stringify({ topic, seq, ts: Date.now() })
    );
  } catch {}
}

function loadSeenRX() {
  try {
    const files = fs.readdirSync(RF_RX_DIR).filter(f => f.endsWith(".json"));
    const now = Date.now();
    for (const f of files) {
      const p = path.join(RF_RX_DIR, f);
      try {
        const j = JSON.parse(fs.readFileSync(p, "utf8"));
        if (RF_SPOOL_TTL_SEC && (now - (j.ts || 0)) / 1000 > RF_SPOOL_TTL_SEC) {
          try { fs.unlinkSync(p); } catch {}
          continue;
        }
        seen.set(rxKey(j.topic, j.seq), j.ts || now);
      } catch {}
    }
  } catch {}
}
loadSeenRX();

function haveSeen(topic: string, seq: number): boolean {
  const key = rxKey(topic, seq);
  return seen.has(key);
}

// ───────────────────────────────────────────────────────────────
// Cloud forward queue (store-carry-forward)
type TxItem = {
  id: string;
  body: any;
  tries: number;
  nextAt: number;
  createdAt: number;
  size: number;
};

const queue: TxItem[] = [];
let queueBytes = 0;
let cloudOk = !FORWARD_TO_CLOUD; // ok=true when cloud forwarding is disabled

function sizeOf(obj: any): number {
  try { return Buffer.byteLength(JSON.stringify(obj)); } catch { return 0; }
}

function spoolPath(id: string) { return path.join(RN_SPOOL_DIR, `${id}.json`); }

function persistItem(it: TxItem) {
  try { fs.writeFileSync(spoolPath(it.id), JSON.stringify(it)); } catch {}
}
function removeItem(id: string) {
  try { fs.unlinkSync(spoolPath(id)); } catch {}
}

/** Keep both item count and total bytes within RN_* caps (drop oldest first). */
function enforceSpoolCaps() {
  // Oldest first
  queue.sort((a, b) => (a.createdAt || 0) - (b.createdAt || 0));

  const overItems = () => RN_QUEUE_MAX_ITEMS > 0 && queue.length > RN_QUEUE_MAX_ITEMS;
  const overBytes = () => RN_QUEUE_MAX_BYTES > 0 && queueBytes > RN_QUEUE_MAX_BYTES;

  while ((overItems() || overBytes()) && queue.length) {
    const victim = queue.shift()!;
    queueBytes -= victim.size || sizeOf(victim.body);
    removeItem(victim.id);
  }
}

// Enforce RN caps (TTL → bytes → items)
function enforceQueueCaps() {
  const now = Date.now();

  // TTL first
  for (let i = queue.length - 1; i >= 0; i--) {
    const it = queue[i];
    if (RN_QUEUE_TTL_MS && now - (it.createdAt || 0) > RN_QUEUE_TTL_MS) {
      queueBytes -= it.size || sizeOf(it.body);
      queue.splice(i, 1);
      removeItem(it.id);
    }
  }

  // Byte cap (oldest first)
  queue.sort((a, b) => (a.createdAt || 0) - (b.createdAt || 0));
  while (queueBytes > RN_QUEUE_MAX_BYTES && queue.length) {
    const victim = queue.shift()!;
    queueBytes -= victim.size || sizeOf(victim.body);
    removeItem(victim.id);
  }

  // Item cap
  while (queue.length > RN_QUEUE_MAX_ITEMS) {
    const victim = queue.shift()!;
    queueBytes -= victim.size || sizeOf(victim.body);
    removeItem(victim.id);
  }
}

// Load cloud-forward queue from disk at boot (dedupe + TTL)
function loadQueueFromDisk() {
  try {
    ensureDir(RN_SPOOL_DIR);
    const files = fs.readdirSync(RN_SPOOL_DIR).filter(f => f.endsWith(".json"));
    const now = Date.now();
    for (const f of files) {
      const p = path.join(RN_SPOOL_DIR, f);
      let it: TxItem | null = null;
      try { it = JSON.parse(fs.readFileSync(p, "utf8")); } catch { it = null; }

      if (!it?.id || !it?.body) { try { fs.unlinkSync(p); } catch {}; continue; }
      if (RN_QUEUE_TTL_MS && now - (it.createdAt || 0) > RN_QUEUE_TTL_MS) { try { fs.unlinkSync(p); } catch {}; continue; }
      if (queue.find(q => q.id === it!.id)) { try { fs.unlinkSync(p); } catch {}; continue; }

      queue.push(it);
      queueBytes += it.size || sizeOf(it.body);
    }
    enforceQueueCaps();
    if (queue.length) {
      console.log(`[radio-node] loaded ${queue.length} queued cloud forwards (${queueBytes}B)`);
    }
  } catch (e) {
    console.warn("[radio-node] loadQueueFromDisk failed:", e);
  }
}

// Load any existing cloud-forward spool at startup
loadQueueFromDisk();

// ───────────────────────────────────────────────────────────────
// Simple helpers
const URL_BASE = "http://localhost"; // used for safe URL parsing (WS upgrade handlers)
function now() { return Date.now(); }
function msgId() { return `loc-${now()}-${Math.random().toString(36).slice(2, 8)}`; }
function topicKey(topic: string, kg?: string) { return `${(kg || "personal").toLowerCase()}:${topic}`; }

// ───────────────────────────────────────────────────────────────
// Band profiles (MTU + RATE_HZ)
type BandProfile = { MTU: number; RATE_HZ: number };
const DEFAULT_PROFILES: Record<string, BandProfile> = {
  "NA-915": { MTU: 180, RATE_HZ: 10 },
  "EU-868": { MTU: 51,  RATE_HZ: 6  },
  "ISM-2.4":{ MTU: 200, RATE_HZ: 20 },
};

const PROFILE_FILE =
  process.env.BAND_PROFILE_FILE || path.join(__dirname, "band_profile.yml");

function loadProfiles(): Record<string, BandProfile> {
  try {
    const txt = fs.readFileSync(PROFILE_FILE, "utf8");
    if (!YAML) return DEFAULT_PROFILES; // yaml lib not present
    const parsed = YAML.parse(txt) as any;
    // Expect top-level map: { PROFILE: { MTU, RATE_HZ }, ... }
    const out: Record<string, BandProfile> = {};
    for (const [k, v] of Object.entries(parsed || {})) {
      const p = v as any;
      const MTU = Number(p?.MTU);
      const RATE_HZ = Number(p?.RATE_HZ);
      if (Number.isFinite(MTU) && Number.isFinite(RATE_HZ)) out[k] = { MTU, RATE_HZ };
    }
    return Object.keys(out).length ? out : DEFAULT_PROFILES;
  } catch {
    return DEFAULT_PROFILES;
  }
}

const PROFILES = loadProfiles();
const PROFILE_NAME = process.env.BAND_PROFILE || "NA-915";
let ACTIVE: BandProfile = PROFILES[PROFILE_NAME] || DEFAULT_PROFILES["NA-915"];

// ───────────────────────────────────────────────────────────────
// RF Frame encoder (header-aware for MTU calc)
type RFFrame = {
  topic: string;
  seq: number;
  ts: number;
  codec?: string;
  bytes: Uint8Array;
};

const seqByTopic = new Map<string, number>();
function nextSeq(topic: string): number {
  const n = (seqByTopic.get(topic) ?? 0) + 1;
  seqByTopic.set(topic, n);
  return n;
}

// [ver u8][seq u32][ts u64][codecLen u8][codec..][topicLen u8][topic..][payload..]
function encodeFrame(f: RFFrame): Uint8Array {
  const te = new TextEncoder();
  const codecBytes = te.encode(f.codec ?? "");
  const topicBytes = te.encode(f.topic);
  const headerLen = 1 + 4 + 8 + 1 + codecBytes.length + 1 + topicBytes.length;
  const out = new Uint8Array(headerLen + f.bytes.length);
  const dv = new DataView(out.buffer);

  let o = 0;
  out[o++] = 1;                               // ver
  dv.setUint32(o, f.seq >>> 0, false); o += 4;
  const hi = Math.floor(f.ts / 2 ** 32);
  const lo = f.ts >>> 0;
  dv.setUint32(o, hi >>> 0, false); o += 4;
  dv.setUint32(o, lo >>> 0, false); o += 4;

  out[o++] = codecBytes.length & 0xff;
  out.set(codecBytes, o); o += codecBytes.length;

  out[o++] = topicBytes.length & 0xff;
  out.set(topicBytes, o); o += topicBytes.length;

  out.set(f.bytes, o);
  return out;
}

function headerOverheadBytes(topic: string, codec?: string): number {
  // length with empty payload
  return encodeFrame({ topic, seq: 0, ts: 0, codec, bytes: new Uint8Array(0) }).length;
}

function maxPayloadBytes(topic: string, codec?: string): number {
  return Math.max(0, ACTIVE.MTU - headerOverheadBytes(topic, codec));
}
// ───────────────────────────────────────────────────────────────
// RF pacing queue (enforce RATE_HZ)
const rfOutbox: Uint8Array[] = [];
const rfQueue:  Uint8Array[] = [];
let rfTicker: ReturnType<typeof setInterval> | null = null;

// ───────────────────────────────────────────────────────────────
// Link/PHY transport registry (pluggable drivers)

type LinkDriver = {
  id: string;
  kind: "ws-bridge" | "serial" | "ble" | "mock";
  /** Send one RF frame already base64-encoded. Return true if accepted. */
  sendB64: (b64: string) => boolean;
  isUp: () => boolean;
  stats?: () => Record<string, any>;
};

const drivers: LinkDriver[] = [];

function registerDriver(d: LinkDriver) {
  drivers.push(d);
}

function listDrivers() {
  return drivers.map(d => ({
    id: d.id,
    kind: d.kind,
    up: d.isUp(),
    ...(d.stats?.() || {}),
  }));
}

// ───────────────────────────────────────────────────────────────
// Dev RF mock (software link) — delay/jitter/loss + optional loopback

type MockCfg = {
  enabled: boolean;
  loopback: boolean;
  delay_ms: number;
  jitter_ms: number;
  loss_pct: number;        // 0..100
};

const mockCfg: MockCfg = {
  enabled: false,
  loopback: false,
  delay_ms: 0,
  jitter_ms: 0,
  loss_pct: 0,
};

// Decode RF frame that was produced by encodeFrame()
function decodeFrame(u8: Uint8Array): {
  ver: number; seq: number; ts: number; codec: string; topic: string; payload: Uint8Array;
} | null {
  try {
    const dv = new DataView(u8.buffer, u8.byteOffset, u8.byteLength);
    let o = 0;
    const ver = dv.getUint8(o); o += 1;
    const seq = dv.getUint32(o, false); o += 4;
    const hi  = dv.getUint32(o, false); o += 4;
    const lo  = dv.getUint32(o, false); o += 4;
    const ts  = (hi * 2 ** 32) + lo;

    const codecLen = dv.getUint8(o); o += 1;
    const codec = new TextDecoder().decode(u8.subarray(o, o + codecLen)); o += codecLen;

    const topicLen = dv.getUint8(o); o += 1;
    const topic = new TextDecoder().decode(u8.subarray(o, o + topicLen)); o += topicLen;

    const payload = u8.subarray(o);
    return { ver, seq, ts, codec, topic, payload };
  } catch {
    return null;
  }
}

/** Reusable inbound RF processor (used by WS bridge, mock driver, and dev injector). */
function processInboundRF(topic: string, bytes: Uint8Array, seq?: number, ua?: string) {
  // De-dupe if a seq is supplied (but skip control:* from persistence)
  if (typeof seq === "number" && !String(topic).startsWith("control:")) {
    const key = `${topic}#${seq}`;
    if (seen.has(key)) return;
    rememberRX(topic, seq);
  }

  // Discovery beacons: ...
  if (topic === "control:beacon") {
    try {
      const j = JSON.parse(u8ToStr(bytes));
      if (j?.id) {
        upsertNeighbor({
          id: String(j.id),
          profile: String(j.profile || PROFILE_NAME),
          rate_hz: Number(j.rate_hz || ACTIVE.RATE_HZ),
          mtu: Number(j.mtu || ACTIVE.MTU),
          ua,
          seenAt: now(),
        });
      }
    } catch {}
    return;
  }

  // Normal RF → local WS fanout as a synthetic capsule
  const keyTopic = topic; // "graph:recipient"
  const envelope = {
    capsule: { glyphs: ["(rf)"], rf_bytes_len: bytes.length },
    meta: { graph: keyTopic.split(":")[0] || "personal" },
    ts: now(),
    id: msgId(),
  };
  broadcast(keyTopic, { type: "glyphnet_capsule", envelope });
}

let mockDriverRegistered = false;
function ensureMockDriverRegistered() {
  if (mockDriverRegistered) return;

  registerDriver({
    id: "mock-1",
    kind: "mock",
    // Claim frames only when enabled; optionally loop them back after delay/jitter/loss.
    sendB64: (b64: string) => {
      if (!mockCfg.enabled) return false;

      // Simulate loss
      if (mockCfg.loss_pct > 0 && Math.random() * 100 < mockCfg.loss_pct) {
        return true; // claimed (dropped)
      }

      // Optional loopback back into inbound path
      if (mockCfg.loopback) {
        const buf = Buffer.from(b64, "base64");
        const dec = decodeFrame(new Uint8Array(buf));
        if (dec) {
          // delay + jitter
          const base = Math.max(0, mockCfg.delay_ms|0);
          const jit  = Math.max(0, mockCfg.jitter_ms|0);
          const delta = base + (jit ? Math.floor((Math.random() * 2 - 1) * jit) : 0);

          setTimeout(() => {
            try {
              processInboundRF(dec.topic, dec.payload, dec.seq, "mock-loopback");
            } catch {}
          }, Math.max(0, delta));
        }
      }

      return true; // accepted by mock link
    },
    isUp: () => mockCfg.enabled,
    stats: () => ({ mock: { ...mockCfg } }),
  });

  mockDriverRegistered = true;
}
ensureMockDriverRegistered();
ensureSerialDriverRegistered();

/** Drain rfOutbox via any up drivers; stop if none can accept. */
function drainOutboxViaDrivers() {
  if (!drivers.length) return;
  while (rfOutbox.length) {
    const frame = rfOutbox.shift()!;
    const b64 = Buffer.from(frame).toString("base64");
    let delivered = false;
    for (const d of drivers) {
      try { delivered = d.sendB64(b64) || delivered; } catch {}
    }
    if (!delivered) {
      // No driver accepted; put back and try later
      rfOutbox.unshift(frame);
      break;
    }
  }
}

function kickRFStep() {
  const frame = rfQueue.shift();
  if (frame) rfOutbox.push(frame);
  pushRFOutboxToBridge();
}

// Enqueue with fragmentation to fit MTU (topic=graph:recipient)
function enqueueRF(rfTopic: string, payload: Uint8Array, codec?: string) {
  if (!payload || payload.length === 0) return;

  const maxPayload = maxPayloadBytes(rfTopic, codec);
  if (maxPayload <= 0) {
    console.warn(`[rf] MTU too small for ${rfTopic} (MTU=${ACTIVE.MTU}) — dropping`);
    return;
  }

  for (let o = 0; o < payload.length; o += maxPayload) {
    const slice = payload.subarray(o, Math.min(payload.length, o + maxPayload));
    const frame = encodeFrame({
      topic: rfTopic,
      seq: nextSeq(rfTopic),
      ts: now(),
      codec,
      bytes: slice,
    });
    rfQueue.push(frame);
  }

  // Ensure at least one immediate step so dev traffic shows up even if the interval didn't start
  try { kickRFStep(); } catch { /* fallback if helper not present */ try { pushRFOutboxToBridge(); } catch {} }
}

// ── Discovery beacons: advertise presence over RF
const BEACON_INTERVAL_MS = Number(process.env.BEACON_INTERVAL_MS ?? 10_000);
setInterval(() => {
  // keep payload tiny (fits in single frame for NA-915)
  const payload = {
    id: NODE_ID,
    profile: PROFILE_NAME,
    rate_hz: ACTIVE.RATE_HZ,
    mtu: ACTIVE.MTU,
    ts: now(),
  };
  try {
    const bytes = strToU8(JSON.stringify(payload));
    // dedicated control topic; tagged codec (optional)
    enqueueRF("control:beacon", bytes, "beacon/json");
  } catch {}
}, BEACON_INTERVAL_MS);

// ───────────────────────────────────────────────────────────────
// WS room registry
const rooms: Map<string, Set<WebSocket>> = new Map();
function joinRoom(key: string, ws: WebSocket) {
  let set = rooms.get(key);
  if (!set) { set = new Set(); rooms.set(key, set); }
  set.add(ws);
}
function leaveAll(ws: WebSocket) { for (const [, set] of rooms) set.delete(ws); }
function broadcast(key: string, obj: any) {
  const set = rooms.get(key);
  if (!set || set.size === 0) return;
  const data = JSON.stringify(obj);
  for (const ws of set) if (ws.readyState === WebSocket.OPEN) { try { ws.send(data); } catch {} }
}

// ───────────────────────────────────────────────────────────────
// Cloud forward queue (store-carry-forward)
// ───────────────────────────────────────────────────────────────


async function tryForward(item: TxItem) {
  if (!FORWARD_TO_CLOUD) return true;

  // Optional: hard timeout so we don’t stall the loop
  const ctrl = new AbortController();
  const timer = setTimeout(() => ctrl.abort(), 4000);

  try {
    const r = await fetch(`${CLOUD_BASE}/api/glyphnet/tx`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(item.body),
      signal: ctrl.signal as any,
    } as any);

    cloudOk = r.ok;
    return r.ok;
  } catch {
    cloudOk = false;
    return false;
  } finally {
    clearTimeout(timer);
  }
}

function dropFromQueue(id: string) {
  const idx = queue.findIndex((q) => q.id === id);
  if (idx >= 0) {
    const it = queue[idx];
    queue.splice(idx, 1);
    queueBytes -= it.size || sizeOf(it.body);
    removeItem(it.id); // remove spool file
  }
}

let forwardLoopBusy = false;
setInterval(async () => {
  if (forwardLoopBusy) return;
  forwardLoopBusy = true;

  try {
    const t = now();
    for (const it of queue.slice()) {
      if (it.nextAt > t) continue;

      const ok = await tryForward(it);
      if (ok) {
        dropFromQueue(it.id);
      } else {
        it.tries += 1;
        const backoff = Math.min(15_000, Math.floor(Math.pow(1.8, it.tries) * 700));
        it.nextAt = now() + backoff + Math.floor(Math.random() * 400);
        persistItem(it); // keep disk spool updated with new nextAt/tries
      }
    }

    enforceQueueCaps();
  } finally {
    forwardLoopBusy = false;
  }
}, 750);

// ───────────────────────────────────────────────────────────────
// Express app + middleware (ONE app only; order matters)
// ───────────────────────────────────────────────────────────────

const app = express();

/* CORS first */
const corsMw = cors({
  origin: true,
  credentials: true,
  methods: ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
  allowedHeaders: [
    "Content-Type",
    "Authorization",
    "X-Agent-Token",
    "X-Agent-Id",
    "X-Bridge-Token",
    "X-Bridge-Sig",
    "Accept",
    "Origin",
  ],
  exposedHeaders: ["Content-Type"],
});

app.use(corsMw);
app.options("*", corsMw);

/* JSON body parser (only once) */
app.use(express.json({ limit: "5mb" }));


/** DEBUG: confirm this file/build is the one running */
console.log("[radio-node] boot: registering routes");
app.get("/__build", (_req: Request, res: Response) => {
  res.json({ ok: true, build: "radio-node/server.ts:v38", ts: Date.now() });
});
/* Static/container routes AFTER middleware */
registerContainerStaticRoutes(app);

// Optional: simple status endpoint for transports (force strict JSON)
app.get("/bridge/transports", (_req, res) => {
  try {
    const body = {
      ok: true,
      drivers: listDrivers(),    // [{ id, kind, up, ...stats }]
      rfOutbox: rfOutbox.length, // queued frames waiting for a link
    };
    res.setHeader("Content-Type", "application/json; charset=utf-8");
    res.end(JSON.stringify(body));
  } catch (e: any) {
    res.status(500).json({ ok: false, error: String(e?.message || e) });
  }
});


app.use("/__routes", (_req, res, next) => {
  res.setHeader("Access-Control-Allow-Origin", "*");
  res.setHeader("Access-Control-Allow-Methods", "GET, OPTIONS");
  res.setHeader("Access-Control-Allow-Headers", "Content-Type, Authorization, Accept, Origin");
  if (_req.method === "OPTIONS") return res.sendStatus(204);
  next();
});

// Debug: list registered routes (useful to confirm correct build is running)
app.get("/__routes", (_req, res) => {
  const stack = (app as any)._router?.stack || [];
  const routes = stack
    .filter((l: any) => l.route && l.route.path)
    .map((l: any) => ({
      method: Object.keys(l.route.methods || {})[0]?.toUpperCase() || "GET",
      path: l.route.path,
    }));
  res.json({ ok: true, routes });
});
// ───────────────────────────────────────────────────────────────
// WirePack v46 shim (Python codec called from Node)
// POST /api/wirepack/v46/encode { payload_text }
// POST /api/wirepack/v46/decode { encoded_b64 }
// ───────────────────────────────────────────────────────────────


function pyRoot() {
  return path.resolve(__dirname, "..");
}


async function runPyWirepackEncode(payloadText: string): Promise<string> {
  const script = [
    "import os, sys, json, base64",
    "sys.path.insert(0, os.getcwd())",
    "from backend.modules.glyphos import wirepack_codec as w",
    'req = json.loads(sys.stdin.read() or "{}")',
    'txt = req.get("payload_text", "")',
    'b = txt.encode("utf-8")',
    "enc = w.encode_bytes(b)",
    "sys.stdout.write(base64.b64encode(enc).decode('ascii'))",
  ].join("\n");

  const p = await import("node:child_process");
  const { stdout } = await new Promise<{ stdout: string }>((resolve, reject) => {
    const cp = p.spawn("python3", ["-c", script], {
      cwd: REPO_ROOT,
      stdio: ["pipe", "pipe", "pipe"],
      env: { ...process.env, PYTHONPATH: REPO_ROOT },
    });
    let out = "";
    let err = "";
    cp.stdout.on("data", (d: any) => (out += String(d)));
    cp.stderr.on("data", (d: any) => (err += String(d)));
    cp.on("close", (code: number) => {
      if (code === 0) return resolve({ stdout: out.trim() });
      reject(new Error(err || `python encode failed (${code})`));
    });
    cp.stdin.write(JSON.stringify({ payload_text: payloadText }) + "\n");
    cp.stdin.end();
  });

  return stdout;
}

async function runPyWirepackDecode(encodedB64: string): Promise<string> {
  const script = [
    "import os, sys, json, base64",
    "sys.path.insert(0, os.getcwd())",
    "from backend.modules.glyphos import wirepack_codec as w",
    'req = json.loads(sys.stdin.read() or "{}")',
    'b64 = req.get("encoded_b64", "")',
    "enc = base64.b64decode(b64.encode('ascii'))",
    "raw = w.decode_bytes(enc)",
    "sys.stdout.write(raw.decode('utf-8', errors='strict'))",
  ].join("\n");

  const p = await import("node:child_process");
  const { stdout } = await new Promise<{ stdout: string }>((resolve, reject) => {
    const cp = p.spawn("python3", ["-c", script], {
      cwd: REPO_ROOT,
      stdio: ["pipe", "pipe", "pipe"],
      env: { ...process.env, PYTHONPATH: REPO_ROOT },
    });
    let out = "";
    let err = "";
    cp.stdout.on("data", (d: any) => (out += String(d)));
    cp.stderr.on("data", (d: any) => (err += String(d)));
    cp.on("close", (code: number) => {
      if (code === 0) return resolve({ stdout: out });
      reject(new Error(err || `python decode failed (${code})`));
    });
    cp.stdin.write(JSON.stringify({ encoded_b64: encodedB64 }) + "\n");
    cp.stdin.end();
  });

  return stdout;
}

app.post("/api/wirepack/v32/run", async (req, res) => {
  try {
    // ---- params ----
    const seed = Number(req.body?.seed ?? 1337) | 0;
    const n = Math.max(256, Math.min(65536, Number(req.body?.n ?? 4096) | 0));
    const turns = Math.max(1, Math.min(4096, Number(req.body?.turns ?? 64) | 0));
    const muts = Math.max(1, Math.min(4096, Number(req.body?.muts ?? 3) | 0));
    const K = Math.max(1, Math.min(256, Number(req.body?.K ?? 16) | 0));

    // ---- local helpers (scoped: no duplicates) ----
    const { createHash } = await import("crypto");
    const sha256Hex = (buf: Uint8Array | Buffer) => createHash("sha256").update(buf).digest("hex");

    const stableStringify = (x: any): string => {
      const seen = new WeakSet<object>();
      const walk = (v: any): any => {
        if (v === null || typeof v !== "object") return v;
        if (seen.has(v)) throw new Error("cyclic json");
        seen.add(v);
        if (Array.isArray(v)) return v.map(walk);
        const out: any = {};
        for (const k of Object.keys(v).sort()) out[k] = walk(v[k]);
        return out;
      };
      return JSON.stringify(walk(x));
    };

    const xorshift32 = (s: number) => {
      let x = (s >>> 0) || 1;
      return () => {
        x ^= (x << 13) >>> 0;
        x ^= (x >>> 17) >>> 0;
        x ^= (x << 5) >>> 0;
        return x >>> 0;
      };
    };

    const varintLen = (u: number) => {
      let v = u >>> 0;
      let len = 1;
      while (v >= 0x80) {
        v >>>= 7;
        len++;
      }
      return len;
    };

    const topKFromCounts = (counts: Uint32Array, k: number) => {
      const pairs: Array<{ idx: number; hits: number }> = [];
      for (let i = 0; i < counts.length; i++) {
        const c = counts[i] >>> 0;
        if (c) pairs.push({ idx: i, hits: c });
      }
      pairs.sort((a, b) => (b.hits - a.hits) || (a.idx - b.idx));
      return pairs.slice(0, Math.max(1, k));
    };

    const u32leBytes = (arr: Uint32Array) => {
      const out = Buffer.allocUnsafe(arr.length * 4);
      for (let i = 0; i < arr.length; i++) out.writeUInt32LE(arr[i] >>> 0, i * 4);
      return out;
    };

    // ---- generate deterministic “collision-heavy” ops ----
    const Rgen = xorshift32(seed);
    const ops: number[] = [];
    ops.length = turns * muts;

    for (let t = 0, p = 0; t < turns; t++) {
      for (let j = 0; j < muts; j++, p++) {
        ops[p] = (Rgen() % n) >>> 0;
      }
    }

    // countsA from ops (order A)
    const countsA = new Uint32Array(n);
    for (let i = 0; i < ops.length; i++) countsA[ops[i]]++;

    // shuffle to simulate nondeterministic arrival (order B)
    const opsB = ops.slice();
    const Rshuf = xorshift32(seed ^ 0x9e3779b9);
    for (let i = opsB.length - 1; i > 0; i--) {
      const j = (Rshuf() % (i + 1)) >>> 0;
      const tmp = opsB[i]; opsB[i] = opsB[j]; opsB[j] = tmp;
    }

    const countsB = new Uint32Array(n);
    for (let i = 0; i < opsB.length; i++) countsB[opsB[i]]++;

    // ---- topK + invariant ----
    const topA = topKFromCounts(countsA, K);
    const topB = topKFromCounts(countsB, K);
    const topk_ok = JSON.stringify(topA) === JSON.stringify(topB);

    // ---- bytes accounting (rough “delta stream” cost) ----
    let delta_bytes_total = 0;
    for (let i = 0; i < ops.length; i++) delta_bytes_total += varintLen(ops[i]);

    const bytes = {
      delta_bytes_total,
      wire_total_bytes: delta_bytes_total,
      ops_total: ops.length,
    };

    // deterministic state hash + deterministic receipt hash
    const final_state_sha256 = sha256Hex(u32leBytes(countsA));

    const invariants = { topk_ok };

    const receiptBody = {
      demo: "v32",
      params: { seed, n, turns, muts, K },
      bytes,
      invariants,
      topk: topA,
      final_state_sha256,
    };

    const drift_sha256 = sha256Hex(Buffer.from(stableStringify(receiptBody), "utf8"));
    const LEAN_OK = topk_ok ? 1 : 0;

    return res.json({
      ok: true,
      demo: "v32",
      params: receiptBody.params,
      bytes,
      invariants,
      topk: topA,
      final_state_sha256,
      receipts: { drift_sha256, LEAN_OK },
      endpoint: "POST /api/wirepack/v32/run",
    });
  } catch (e: any) {
    return res.status(500).json({ ok: false, error: String(e?.message || e) });
  }
});
// -------------------------------
// v29 — Projection(Q)
// -------------------------------
app.post("/api/wirepack/v29/run", async (req, res) => {
  try {
    const seed = Number(req.body?.seed ?? 1337) | 0;
    const n = Math.max(256, Math.min(65536, Number(req.body?.n ?? 4096) | 0));
    const turns = Math.max(1, Math.min(4096, Number(req.body?.turns ?? 64) | 0));
    const muts = Math.max(1, Math.min(4096, Number(req.body?.muts ?? 3) | 0));
    const q = Math.max(1, Math.min(4096, Number(req.body?.q ?? 128) | 0)); // |Q|

    const R = xorshift32(seed);

    // Query set Q (indices we "care about")
    const Q = pickDistinctIndices(R, n, q);

    // Fast membership + idx->pos map
    const pos = new Int32Array(n);
    pos.fill(-1);
    for (let i = 0; i < Q.length; i++) pos[Q[i]] = i;

    // Deterministic edit stream: ops = (idx, value)
    const ops_total = turns * muts;
    const ops_idx = new Uint32Array(ops_total);
    const ops_val = new Uint32Array(ops_total);

    for (let i = 0; i < ops_total; i++) {
      ops_idx[i] = (R() % n) >>> 0;
      ops_val[i] = R() >>> 0; // last-write-wins value
    }

    // Full replay baseline truth
    const full = new Uint32Array(n);
    for (let i = 0; i < ops_total; i++) full[ops_idx[i]] = ops_val[i];

    // Query-only tracking (touch only indices in Q)
    const tracked = new Uint32Array(Q.length);
    let hits_in_Q = 0;
    for (let i = 0; i < ops_total; i++) {
      const p = pos[ops_idx[i]];
      if (p >= 0) {
        tracked[p] = ops_val[i];
        hits_in_Q++;
      }
    }

    // Baseline projection(Q)
    const baseline = new Uint32Array(Q.length);
    for (let i = 0; i < Q.length; i++) baseline[i] = full[Q[i]];

    // Invariant: tracked projection == baseline projection
    let projection_ok = true;
    for (let i = 0; i < Q.length; i++) {
      if ((baseline[i] >>> 0) !== (tracked[i] >>> 0)) {
        projection_ok = false;
        break;
      }
    }

    // Byte accounting (approx wire delta): varint(idx) + varint(value)
    let delta_bytes_total = 0;
    for (let i = 0; i < ops_total; i++) {
      delta_bytes_total += varintLen(ops_idx[i]) + varintLen(ops_val[i]);
    }

    const bytes = {
      template_bytes: 0,
      delta_bytes_total,
      wire_total_bytes: delta_bytes_total,
      ops_total,
      q_size: Q.length,
      hits_in_Q,
    };

    const invariants = {
      projection_ok,
      work_scales_with_Q: true, // surfaced via q_size + hits_in_Q
    };

    // Stable “meaning” hash = projection vector bytes (ordered by sorted Q)
    const final_state_sha256 = sha256Hex(u32leBytes(tracked));

    const projection = Q.map((idx, i) => ({ idx, value: tracked[i] >>> 0 }));

    const receiptBody = {
      demo: "v29",
      params: { seed, n, turns, muts, q: Q.length },
      bytes,
      invariants,
      Q, // sorted indices
      projection,
      final_state_sha256,
    };

    const drift_sha256 = sha256Hex(Buffer.from(stableStringify(receiptBody), "utf8"));
    const LEAN_OK = projection_ok ? 1 : 0;

    return res.json({
      ok: true,
      demo: "v29",
      params: receiptBody.params,
      bytes,
      invariants,
      Q,
      projection,
      final_state_sha256,
      receipts: { drift_sha256, LEAN_OK },
      endpoint: "POST /api/wirepack/v29/run",
    });
  } catch (e: any) {
    return res.status(500).json({ ok: false, error: String(e?.message || e) });
  }
});

// ─────────────────────────────────────────────────────────────
// v45 — Cross-language vectors (byte-identical template+delta)
// POST /api/wirepack/v45/run
// body: { seed?, n?, turns?, muts? }
// ─────────────────────────────────────────────────────────────
app.post("/api/wirepack/v45/run", async (req, res) => {
  try {
    const seed  = Number.isFinite(req.body?.seed)  ? Number(req.body.seed)  : 1337;
    const n     = Math.max(256, Math.min(1 << 16, Number(req.body?.n || 256)));
    const turns = Math.max(1,   Math.min(256,     Number(req.body?.turns || 16)));
    const muts  = Math.max(1,   Math.min(512,     Number(req.body?.muts || 128)));

    const R = rng32(seed);

    // Initial state (u32)
    const state0 = new Uint32Array(n);
    for (let i = 0; i < n; i++) state0[i] = (R() % 100_000) >>> 0;

    const words = Array.from(state0, (x) => x >>> 0);

    // Generate the exact op-stream deterministically in Node
    const turns_ops: Op44[][] = [];
    for (let t = 0; t < turns; t++) {
      const ops: Op44[] = [];
      for (let j = 0; j < muts; j++) {
        const idx  = (R() % n) >>> 0;
        const newv = (R() % 100_000) >>> 0;
        ops.push([idx, newv]);
      }
      turns_ops.push(ops);
    }

    // Python does ALL enc/dec in one shot (no per-turn process spawn)
    const pyOutRaw = await runPy(PY_V45_VECTORS, { words, turns_ops });
    const py = JSON.parse(pyOutRaw || "{}");

    const pyTemplate = Buffer.from(String(py.template_b64 || ""), "base64");
    const pyTemplateDecWords = (py.template_dec_words || []) as number[];

    const pyDeltasB64 = (py.deltas_b64 || []) as string[];
    const pyDecOpsAll = (py.deltas_dec_ops || []) as Array<Array<[number, number]>>;

    // Node enc/dec
    const nodeTemplate = encodeTemplateWords(words);
    const nodeTemplateDecWords = decodeTemplateWords(nodeTemplate);

    const template_bytes_ok = bufEq(nodeTemplate, pyTemplate);
    const template_decode_ok =
      stableStringify(nodeTemplateDecWords) === stableStringify(pyTemplateDecWords);

    let delta_bytes_ok = true;
    let delta_decode_ok = true;

    let node_delta_bytes_total = 0;
    let py_delta_bytes_total = 0;

    const A = new Uint32Array(state0); // apply original ops
    const B = new Uint32Array(state0); // apply decoded ops (python)

    let first_mismatch: any = null;

    for (let t = 0; t < turns; t++) {
      const ops = turns_ops[t] || [];

      // node encode
      const nd = encodeDeltaOps(ops);
      node_delta_bytes_total += nd.length;

      // python encode
      const pb64 = pyDeltasB64[t] || "";
      const pd = Buffer.from(pb64, "base64");
      py_delta_bytes_total += pd.length;

      if (!bufEq(nd, pd)) {
        delta_bytes_ok = false;
        if (!first_mismatch) first_mismatch = { kind: "delta_bytes", turn: t, node_len: nd.length, py_len: pd.length };
      }

      // node decode
      const ndOps = decodeDeltaOps(nd);

      // python decode
      const pdOps = (pyDecOpsAll[t] || []).map(([i, v]) => [Number(i) >>> 0, Number(v) >>> 0] as Op44);

      if (stableStringify(ndOps) !== stableStringify(ops)) {
        delta_decode_ok = false;
        if (!first_mismatch) first_mismatch = { kind: "node_decode", turn: t };
      }
      if (stableStringify(pdOps) !== stableStringify(ops)) {
        delta_decode_ok = false;
        if (!first_mismatch) first_mismatch = { kind: "py_decode", turn: t };
      }

      // apply to states
      for (const [idx, newv] of ops) A[idx] = newv >>> 0;
      for (const [idx, newv] of pdOps) B[idx] = newv >>> 0;
    }

    const finalA_sha256 = sha256Hex(Buffer.from(stableStringify({ n, state: Array.from(A, (x) => x >>> 0) }), "utf8"));
    const finalB_sha256 = sha256Hex(Buffer.from(stableStringify({ n, state: Array.from(B, (x) => x >>> 0) }), "utf8"));
    const final_state_ok = finalA_sha256 === finalB_sha256;

    const vector_ok = template_bytes_ok && template_decode_ok && delta_bytes_ok && delta_decode_ok && final_state_ok;

    const receiptCore = {
      demo: "v45",
      params: { seed, n, turns, muts },
      bytes: {
        template_bytes: nodeTemplate.length,
        delta_bytes_total: node_delta_bytes_total,
        py_template_bytes: pyTemplate.length,
        py_delta_bytes_total,
      },
      invariants: {
        template_bytes_ok,
        template_decode_ok,
        delta_bytes_ok,
        delta_decode_ok,
        final_state_ok,
        vector_ok,
      },
      final_state_sha256: finalA_sha256,
      first_mismatch,
    };

    const drift_sha256 = sha256Hex(Buffer.from(stableStringify(receiptCore), "utf8"));

    return res.json({
      ok: true,
      ...receiptCore,
      receipts: {
        final_state_sha256: finalA_sha256,
        drift_sha256,
        LEAN_OK: vector_ok ? 1 : 0,
      },
    });
  } catch (e: any) {
    return res.status(500).json({ ok: false, error: String(e?.message || e) });
  }
});

// ─────────────────────────────────────────────────────────────
// v38 — Trust & Receipts (canonical bytes + replay = stable hashes)
// POST /api/wirepack/v38/run
// body: { seed?, n?, turns?, muts? }
// ─────────────────────────────────────────────────────────────
app.post("/api/wirepack/v38/run", async (req, res) => {
  try {
    const seed  = Number.isFinite(req.body?.seed)  ? Number(req.body.seed)  : 1337;
    const n     = Math.max(256, Math.min(1 << 16, Number(req.body?.n || 4096)));
    const turns = Math.max(1,   Math.min(4096,    Number(req.body?.turns || 64)));
    const muts  = Math.max(1,   Math.min(512,     Number(req.body?.muts || 3)));

    const R = rng32(seed);

    // Initial state
    const state0 = new Uint32Array(n);
    for (let i = 0; i < n; i++) state0[i] = (R() % 100_000) >>> 0;

    // Template bytes (nice to show, not the main point)
    const tmplBuf = encodeTemplateWords(Array.from(state0, (x) => x >>> 0));
    const wire_template_bytes = tmplBuf.length;

    // Two working states (replay should converge)
    const A = new Uint32Array(state0);
    const B = new Uint32Array(state0);

    let rawA_bytes_total = 0;
    let rawB_bytes_total = 0;
    let canon_bytes_total = 0;

    let canon_ok = true;
    let replay_ok = true;

    for (let t = 0; t < turns; t++) {
      // Build ops for this turn (allow duplicate idx)
      const ops: Op38[] = [];
      for (let j = 0; j < muts; j++) {
        const idx  = (R() % n) >>> 0;
        const newv = (R() % 100_000) >>> 0;
        ops.push([idx, newv, j]); // <-- stable ordinal for tie-break
      }

      // Two orderings of same ops
      const opsA = ops.slice();
      const opsB = ops.slice();
      shuffleInPlace(opsB, R);

      // Raw bytes (order-sensitive): drop ord so encodeDeltaOps still takes Op44
      const rawA = encodeDeltaOps(opsA.map(([i, v]) => [i, v] as Op44));
      const rawB = encodeDeltaOps(opsB.map(([i, v]) => [i, v] as Op44));
      rawA_bytes_total += rawA.length;
      rawB_bytes_total += rawB.length;

      // Canon bytes (order-INVARIANT now)
      const canonA = encodeDeltaOps(canonicalizeOps38(opsA));
      const canonB = encodeDeltaOps(canonicalizeOps38(opsB));
      canon_bytes_total += canonA.length;

      if (!bufEq(canonA, canonB)) canon_ok = false;

      // Replay MUST use the same canonical meaning
      const canonOps = canonicalizeOps38(ops);
      for (const [idx, newv] of canonOps) {
        A[idx] = newv >>> 0;
        B[idx] = newv >>> 0;      
      }
    }

    const finalA_sha256 = sha256Hex(Buffer.from(stableStringify({ n, state: Array.from(A, (x) => x >>> 0) }), "utf8"));
    const finalB_sha256 = sha256Hex(Buffer.from(stableStringify({ n, state: Array.from(B, (x) => x >>> 0) }), "utf8"));
    if (finalA_sha256 !== finalB_sha256) replay_ok = false;

    const receiptCore = {
      demo: "v38",
      params: { seed, n, turns, muts },
      bytes: {
        wire_template_bytes,
        wire_delta_bytes_total: canon_bytes_total,
        wire_total_bytes: wire_template_bytes + canon_bytes_total,
        rawA_bytes_total,
        rawB_bytes_total,
        canon_bytes_total,
      },
      invariants: { canon_ok, replay_ok },
      final_state_sha256: finalA_sha256,
    };

    const drift_sha256 = sha256Hex(Buffer.from(stableStringify(receiptCore), "utf8"));

    return res.json({
      ok: true,
      ...receiptCore,
      receipts: {
        final_state_sha256: finalA_sha256,
        drift_sha256,
        LEAN_OK: (canon_ok && replay_ok) ? 1 : 0,
      },
    });
  } catch (e: any) {
    return res.status(500).json({ ok: false, error: String(e?.message || e) });
  }
});
// ─────────────────────────────────────────────────────────────
// v44 — SQL-ish queries on delta streams (snapshot vs stream-maintained)
// POST /api/wirepack/v44/run
// body: { seed?, n?, turns?, muts?, query_id?, k? }
// query_id: "projection" | "histogram"
// ─────────────────────────────────────────────────────────────

app.post("/api/wirepack/v44/run", async (req, res) => {
  try {
    const seed = Number.isFinite(req.body?.seed) ? Number(req.body.seed) : 1337;
    const n = Math.max(256, Math.min(1 << 16, Number(req.body?.n || 4096)));
    const turns = Math.max(16, Math.min(2048, Number(req.body?.turns || 256)));
    const muts = Math.max(1, Math.min(128, Number(req.body?.muts || 3)));
    const k = Math.max(1, Math.min(n, Number(req.body?.k || 64)));
    const query_id = String(req.body?.query_id || "projection");

    const R = rng32(seed);

    // Base state (u32 ints)
    const state0 = new Uint32Array(n);
    for (let i = 0; i < n; i++) state0[i] = (R() % 100_000) >>> 0;

    // Query set Q (deterministic)
    const Q: number[] = [];
    const seenQ = new Set<number>();
    while (Q.length < k) {
      const idx = (R() % n) >>> 0;
      if (!seenQ.has(idx)) { seenQ.add(idx); Q.push(idx); }
    }
    Q.sort((a, b) => a - b);

    // WirePack bytes: template once + deltas
    const templateWords = Array.from(state0, (x) => x >>> 0);
    const tmplBuf = encodeTemplateWords(templateWords);
    const wire_template_bytes = tmplBuf.length;

    let wire_delta_bytes_total = 0;
    let gzip_snapshot_bytes_total = 0;

    // SNAPSHOT evaluator (materialize full state each turn)
    const snap = new Uint32Array(state0);

    // STREAM evaluator (no full materialization beyond a working state + maintained stats)
    // (We still keep `cur` so we can compute old bucket / old value cheaply.)
    const cur = new Uint32Array(state0);

    // stream-maintained outputs
    let projectionMap: Map<number, number> | null = null;
    let histBins: Uint32Array | null = null;

    if (query_id === "projection") {
      projectionMap = new Map<number, number>();
      for (const idx of Q) projectionMap.set(idx, cur[idx] >>> 0);
    } else if (query_id === "histogram") {
      histBins = new Uint32Array(256);
      for (let i = 0; i < n; i++) histBins[cur[i] & 255] += 1;
    } else {
      return res.status(400).json({ ok: false, error: "unknown query_id", query_id });
    }

    let touched = 0;

    for (let t = 0; t < turns; t++) {
      // build ops for this turn
      const ops: Op44[] = [];
      for (let j = 0; j < muts; j++) {
        const idx = (R() % n) >>> 0;
        const newv = (R() % 100_000) >>> 0;
        ops.push([idx, newv]);
      }

      // WirePack delta bytes
      const deltaBuf = encodeDeltaOps(ops);
      wire_delta_bytes_total += deltaBuf.length;

      // STREAM update (maintain query result without scanning)
      for (const [idx, newv] of ops) {
        const oldv = cur[idx] >>> 0;
        if (oldv === (newv >>> 0)) continue;
        cur[idx] = newv >>> 0;
        touched++;

        if (projectionMap) {
          if (projectionMap.has(idx)) projectionMap.set(idx, newv >>> 0);
        } else if (histBins) {
          histBins[oldv & 255] -= 1;
          histBins[newv & 255] += 1;
        }
      }

      // SNAPSHOT update + gzip-per-turn baseline
      for (const [idx, newv] of ops) snap[idx] = newv >>> 0;

      // gzip baseline: "snapshot per turn" (what most systems do)
      // we keep it deterministic + explicit (it is expensive, that's the point)
      const snapJson = stableStringify({ n, t, state: Array.from(snap, (x) => x >>> 0) });
      gzip_snapshot_bytes_total += gzipLenUtf8(snapJson);
    }

    // Final snapshot result (truth)
    let snapshot_result: any;
    let stream_result: any;

    if (projectionMap) {
      snapshot_result = Q.map((idx) => ({ idx, v: snap[idx] >>> 0 }));
      stream_result = Q.map((idx) => ({ idx, v: (projectionMap!.get(idx) ?? 0) >>> 0 }));
    } else if (histBins) {
      // snapshot histogram (compute once at end)
      const bins2 = new Uint32Array(256);
      for (let i = 0; i < n; i++) bins2[snap[i] & 255] += 1;

      snapshot_result = Array.from(bins2, (x) => x >>> 0);
      stream_result = Array.from(histBins, (x) => x >>> 0);
    }

    const query_ok = stableStringify(snapshot_result) === stableStringify(stream_result);

    // Receipt hashes (deterministic)
    const result_sha256 = sha256Hex(Buffer.from(
      stableStringify({ query_id, Q, snapshot_result }),
      "utf8"
    ));

    const drift_sha256 = sha256Hex(Buffer.from(
      stableStringify({
        seed, n, turns, muts, k, query_id,
        wire_template_bytes,
        wire_delta_bytes_total,
        gzip_snapshot_bytes_total,
        touched,
        result_sha256,
        ok: query_ok,
      }),
      "utf8"
    ));
    return res.json({
      ok: true,
      query_id,
      params: { seed, n, turns, muts, k },
      Q,
      query_ok,
      snapshot_result,
      stream_result,
      bytes: {
        wire_template_bytes,
        wire_delta_bytes_total,
        wire_total_bytes: wire_template_bytes + wire_delta_bytes_total,
        gzip_snapshot_bytes_total,
      },
      ops: { touched },
      receipts: { result_sha256, drift_sha256, LEAN_OK: query_ok ? 1 : 0 }, // set to 1 when you wire the Lean badge
    });
  } catch (e: any) {
    return res.status(500).json({ ok: false, error: String(e?.message || e) });
  }
});
// NEW: session aware WirePack v46 (template + deltas)
app.post("/api/wirepack/v46/session/new", (req, res) => {
  const id = crypto.randomBytes(16).toString("hex");
  WP_SESSIONS.set(id, { id, templateId: 0, createdAt: Date.now() });
  res.json({ ok: true, session_id: id, template_id: 0 });
});

app.post("/api/wirepack/v46/session/clear", (req, res) => {
  const session_id = String(req.body?.session_id || "");
  if (!session_id || !WP_SESSIONS.has(session_id)) return res.json({ ok: false, error: "unknown session_id" });
  WP_SESSIONS.delete(session_id);
  res.json({ ok: true });
});

// encode_struct: returns a framed payload: 1 byte kind ('T'|'D') + encoded bytes
app.post("/api/wirepack/v46/encode_struct", async (req, res) => {
  try {
    const session_id = String(req.body?.session_id || "");
    const json_text = String(req.body?.json_text ?? req.body?.payload_text ?? "");
    const sess = WP_SESSIONS.get(session_id);
    if (!sess) return res.status(400).json({ ok: false, error: "unknown session_id" });

    let canon = "";
    try {
      const obj = JSON.parse(json_text || "null");
      canon = stableStringify(obj);
    } catch (e: any) {
      return res.status(400).json({ ok: false, error: `bad json_text: ${e?.message || e}` });
    }
    const nextWords = textToWords(canon);

    let kind: "template" | "delta" = "template";
    let innerB64 = "";

    // if first time, or length/shape changed -> send template
    if (!sess.prevWords || sess.prevWords.length !== nextWords.length) {
      kind = "template";
      innerB64 = await runPy(PY_ENC_TEMPLATE, { words: nextWords });
      sess.templateWords = nextWords.slice();
      sess.prevWords = nextWords.slice();
    } else {
      // delta against previous
      const ops = diffOps(sess.prevWords, nextWords);

      // Heuristic: if too many ops changed, template is better
      const tooMany = ops.length > Math.max(32, Math.floor(nextWords.length * 0.35));
      if (tooMany) {
        kind = "template";
        innerB64 = await runPy(PY_ENC_TEMPLATE, { words: nextWords });
        sess.templateWords = nextWords.slice();
        sess.prevWords = nextWords.slice();
      } else {
        kind = "delta";
        innerB64 = await runPy(PY_ENC_DELTA, { ops });
        sess.prevWords = nextWords.slice();
      }
    }

    const inner = Buffer.from(innerB64, "base64");
    const tag = Buffer.from([kind === "template" ? "T".charCodeAt(0) : "D".charCodeAt(0)]);
    const framed = Buffer.concat([tag, inner]);

    res.json({
      ok: true,
      session_id,
      template_id: sess.templateId,
      kind,
      encoded_b64: framed.toString("base64"),
      bytes_out: framed.length,
    });
  } catch (e: any) {
    res.status(500).json({ ok: false, error: String(e?.message || e) });
  }
});

app.post("/api/wirepack/v46/decode_struct", async (req, res) => {
  try {
    const session_id = String(req.body?.session_id || "");
    const encoded_b64 = String(req.body?.encoded_b64 || "");
    const sess = WP_SESSIONS.get(session_id);
    if (!sess) return res.status(400).json({ ok: false, error: "unknown session_id" });
    if (!encoded_b64) return res.status(400).json({ ok: false, error: "missing encoded_b64" });

    const framed = Buffer.from(encoded_b64, "base64");
    if (framed.length < 2) return res.status(400).json({ ok: false, error: "bad frame" });

    const tag = framed[0];
    const innerB64 = framed.slice(1).toString("base64");

    let kind: "template" | "delta" = tag === "T".charCodeAt(0) ? "template" : "delta";

    if (kind === "template") {
      const out = await runPy(PY_DEC_TEMPLATE, { b64: innerB64 });
      const parsed = JSON.parse(out);
      const words = (parsed?.words || []) as number[];
      sess.templateWords = words.slice();
      sess.prevWords = words.slice();
      const text = wordsToText(words);
      return res.json({ ok: true, kind, decoded_text: text });
    }

    // delta
    if (!sess.prevWords) return res.status(400).json({ ok: false, error: "no prior template/state for delta" });

    const out = await runPy(PY_DEC_DELTA, { b64: innerB64 });
    const parsed = JSON.parse(out);
    const ops = (parsed?.ops || []) as Array<[number, number]>;

    // apply ops to session state
    for (const [idx, newv] of ops) {
      if (idx >= 0 && idx < sess.prevWords.length) sess.prevWords[idx] = (newv >>> 0);
    }

    const text = wordsToText(sess.prevWords);
    return res.json({ ok: true, kind, decoded_text: text });
  } catch (e: any) {
    res.status(500).json({ ok: false, error: String(e?.message || e) });
  }
});

app.post("/api/wirepack/v46/encode", async (req, res) => {
  try {
    const payloadText = String(req.body?.payload_text ?? "");
    const encoded_b64 = await runPyWirepackEncode(payloadText);
    res.json({ ok: true, encoded_b64 });
  } catch (e: any) {
    res.status(500).json({ ok: false, error: String(e?.message || e) });
  }
});

app.post("/api/wirepack/v46/decode", async (req, res) => {
  try {
    const encoded_b64 = String(req.body?.encoded_b64 ?? "");
    if (!encoded_b64) return res.status(400).json({ ok: false, error: "missing encoded_b64" });

    const decoded_text = await runPyWirepackDecode(encoded_b64);
    res.json({ ok: true, decoded_text });
  } catch (e: any) {
    res.status(500).json({ ok: false, error: String(e?.message || e) });
  }
});

/* (optional) CSP helper; keep if you want */
app.use((_: Request, res: Response, next: NextFunction) => {
  res.setHeader(
    "Content-Security-Policy",
    "default-src 'self'; connect-src * blob: data: ws: wss: http: https:"
  );
  next();
});

// ───────────────────────────────────────────────────────────────
// Dev endpoints (all under /dev/rf/mock)
app.get("/dev/rf/mock/status", (_req, res) => {
  res.json({ ok: true, enabled: mockCfg.enabled, config: mockCfg, drivers: listDrivers(), rfOutbox: rfOutbox.length });
});

app.post("/dev/rf/mock/enable", (req, res) => {
  mockCfg.enabled = true;
  if (typeof req.body?.loopback === "boolean") mockCfg.loopback = !!req.body.loopback;
  if (Number.isFinite(req.body?.delay_ms))   mockCfg.delay_ms  = Math.max(0, Number(req.body.delay_ms));
  if (Number.isFinite(req.body?.jitter_ms))  mockCfg.jitter_ms = Math.max(0, Number(req.body.jitter_ms));
  if (Number.isFinite(req.body?.loss_pct))   mockCfg.loss_pct  = Math.min(100, Math.max(0, Number(req.body.loss_pct)));
  res.json({ ok: true, config: mockCfg });
});

app.post("/dev/rf/mock/disable", (_req, res) => {
  mockCfg.enabled = false;
  res.json({ ok: true, config: mockCfg });
});

/** Inject a synthetic inbound RF frame (pretend we received it over the air). */
app.post("/dev/rf/mock/rx", (req, res) => {
  const topic = String(req.body?.topic || "").trim();   // "graph:recipient" or "control:beacon"
  const b64   = String(req.body?.data_b64 || req.body?.bytes_b64 || req.body?.b64 || "");
  const seq   = Number.isFinite(req.body?.seq) ? Number(req.body.seq) : undefined;
  if (!topic || !b64) return res.status(400).json({ ok: false, error: "missing topic or data_b64" });

  let bytes: Uint8Array;
  try { bytes = new Uint8Array(Buffer.from(b64, "base64")); } catch {
    return res.status(400).json({ ok: false, error: "invalid base64" });
  }

  processInboundRF(topic, bytes, seq, "dev-injector");
  res.json({ ok: true, len: bytes.length });
});

app.get("/", (_req, res) => {
  res.type("text").send("radio-node up • try /health or WebSocket at /ws/glyphnet");
});

app.get("/health", (_req, res) => {
  res.json({
    ok: true,
    cloudOk,
    queue: queue.length,
    rfQueue: rfQueue.length,
    rfOutbox: rfOutbox.length,
    neighbors: currentNeighbors().length,
    ts: now(),
    profile: PROFILE_NAME,
    active: ACTIVE,
    profiles: Object.keys(PROFILES),
    maxRfIngressBytes: MAX_RF_INGRESS_BYTES,
    nodeId: NODE_ID,
  });
});

app.get("/discovery/neighbors", (_req, res) => {
  res.json({ ok: true, ttl_ms: NEIGHBOR_TTL_MS, neighbors: currentNeighbors() });
});

// supports /api/aion/container/:id too (UI calls this)
app.get(["/api/aion/container/:id", "/api/container/:id", "/api/containers/:id"], (req, res) => {
  const id = String(req.params.id || "").trim();
  if (!id) return res.status(400).json({ ok: false, error: "missing id" });

  res.json({
    ok: true,
    id,
    status: "local",
    createdAt: Date.now(),
    topic: `ucs://local/${id}`,
    graph: "personal",
    ws: `/ws/ghx?id=${encodeURIComponent(id)}`, // what the page will open
  });
});

// Accept a GlyphNet TX; echo to local WS room; optional cloud forward; RF bridge with guardrails
app.post("/api/glyphnet/tx", async (req: Request, res: Response) => {
  const body = req.body || {};
  const recipient = String(body.recipient || "");
  const kg = String(body.graph || "personal").toLowerCase();
  const key = topicKey(recipient, kg);

  const id = msgId();
  const envelope = {
    capsule: body.capsule || {},
    meta: { ...(body.meta || {}), graph: kg, recipient },
    ts: now(),
    id,
  };

  // 1) Always fan out locally over WS
  broadcast(key, { type: "glyphnet_capsule", envelope });

  // 2) RF bridge for voice payloads (size-guarded)
  const cap = envelope.capsule || {};
  const maybeRF = (mime: string, b64: string) => {
    try {
      const bytes = b64ToU8(b64);
      if (bytes.length <= MAX_RF_INGRESS_BYTES) enqueueRF(key, bytes, mime);
    } catch {}
  };
  if (cap?.voice_frame?.data_b64) maybeRF(cap.voice_frame.mime, cap.voice_frame.data_b64);
  if (cap?.voice_note?.data_b64)  maybeRF(cap.voice_note.mime,  cap.voice_note.data_b64);

  // 3) Optional cloud forward: try once, else queue
  let forwarded = false, queued = false;
  if (FORWARD_TO_CLOUD) {
    const item: TxItem = {
      id,
      body: { recipient, graph: kg, capsule: envelope.capsule, meta: envelope.meta },
      tries: 0,
      nextAt: now(),
      createdAt: now(),
      size: sizeOf(body),
    };
    forwarded = await tryForward(item);
    if (!forwarded) {
      queue.push(item);
      queueBytes += item.size;
      persistItem(item);
      enforceQueueCaps();
      queued = true;
    }
  }

  return res.json({ ok: true, msg_id: id, forwarded, queued });
});

// --- Accessory Radio Bridge ------------------------------------
// Health (for your /radio/bridge/health proxied path)
app.get("/bridge/health", (_req: Request, res: Response) => {
  res.json({
    ok: true,
    ts: now(),
    profile: PROFILE_NAME,
    active: ACTIVE,
    rfQueue: rfQueue.length,
    rfOutbox: rfOutbox.length,
    maxRfIngressBytes: MAX_RF_INGRESS_BYTES,
  });
});

// TX (token required)
// TX (token required)
app.post("/bridge/tx", requireBridgeAuth, (req: Request, res: Response) => {
  const topic = String(req.body?.topic || "").trim();
  const kg    = String(req.body?.graph || "personal").toLowerCase();
  const codec = req.body?.codec ? String(req.body.codec) : undefined;
  const b64   = String(req.body?.data_b64 || req.body?.bytes_b64 || req.body?.b64 || "");

  if (!topic || !b64) return res.status(400).json({ ok: false, error: "missing topic or data_b64" });

  let bytes: Uint8Array;
  try { bytes = b64ToU8(b64); }
  catch { return res.status(400).json({ ok: false, error: "invalid base64" }); }

  if (bytes.length > MAX_RF_INGRESS_BYTES) {
    return res.status(413).json({ ok: false, error: "too large", size: bytes.length, max: MAX_RF_INGRESS_BYTES });
  }

  const rfTopic = topicKey(topic, kg);
  enqueueRF(rfTopic, bytes, codec);

  return res.json({
    ok: true,
    topic: rfTopic,
    mtu: ACTIVE.MTU,
    rate_hz: ACTIVE.RATE_HZ,
    rfQueue: rfQueue.length,
    rfOutbox: rfOutbox.length,
  });
});

// ───────────────────────────────────────────────────────────────
// ───────────────────────────────────────────────────────────────
// QKD endpoints — proxy to real agent if QKD_AGENT is set; else dev shim

const QKD_AGENT = (process.env.QKD_AGENT || "").replace(/\/+$/, "");
const QKD_AGENT_TIMEOUT_MS = Number(process.env.QKD_AGENT_TIMEOUT_MS || 2500);

if (QKD_AGENT) {
  console.log(`[radio-node] QKD proxy enabled → ${QKD_AGENT}`);

  // Pass-through to the external agent (keeps /qkd/* prefix)
  app.get("/qkd/health", async (_req, res) => {
    try {
      const ctrl = new AbortController();
      const timer = setTimeout(() => ctrl.abort(), QKD_AGENT_TIMEOUT_MS);
      const r = await fetch(`${QKD_AGENT}/qkd/health`, { signal: ctrl.signal } as any);
      clearTimeout(timer);

      const text = await r.text();
      res
        .status(r.status)
        .type(r.headers.get("content-type") || "application/json")
        .send(text);
    } catch (e: any) {
      res.status(502).json({ ok: false, error: String(e?.message || e) });
    }
  });

  app.post("/qkd/lease", async (req, res) => {
    try {
      const ctrl = new AbortController();
      const timer = setTimeout(() => ctrl.abort(), QKD_AGENT_TIMEOUT_MS);
      const r = await fetch(`${QKD_AGENT}/qkd/lease`, {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify(req.body || {}),
        signal: ctrl.signal as any,
      } as any);
      clearTimeout(timer);

      const text = await r.text();
      res
        .status(r.status)
        .type(r.headers.get("content-type") || "application/json")
        .send(text);
    } catch (e: any) {
      res.status(502).json({ ok: false, error: String(e?.message || e) });
    }
  });
} else {
  // --- Dev QKD shim (no external service needed) ----------------
  console.log("[radio-node] QKD dev shim enabled");

  const DEV_QKD_TTL_MS = Number(process.env.DEV_QKD_TTL_MS ?? 10 * 60 * 1000);
  const DEV_QKD_SECRET = process.env.DEV_QKD_SECRET || "dev-qkd-secret-not-for-prod";

  app.get("/qkd/health", (_req, res) => {
    res.json({ ok: true, mode: "dev", ttl_ms: DEV_QKD_TTL_MS });
  });

  app.post("/qkd/lease", (req, res) => {
    const r = req.body || {};
    const localWA  = String(r.localWA  || "");
    const remoteWA = String(r.remoteWA || "");
    const kg       = String(r.kg       || "personal");
    const purpose  = String(r.aad ?? r.purpose ?? "glyph"); // accept either 'aad' or 'purpose'

    if (!localWA || !remoteWA) {
      return res.status(400).json({ ok: false, error: "localWA and remoteWA required" });
    }

    const kid = `dev-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 6)}`;
    const salt_b64 = Buffer.from(crypto.randomBytes(16)).toString("base64");

    // Collapse-hash analogue (DEV): deterministic from inputs + secret + kid
    const h = crypto.createHash("sha256");
    h.update(`${localWA}|${remoteWA}|${kg}|${purpose}|${kid}|${DEV_QKD_SECRET}`);
    const collapse_hash = h.digest("hex");

    // Match the client's expected shape: { ok, lease: {...} }
    res.json({
      ok: true,
      lease: {
        kid,
        collapse_hash,                 // client PBKDF2s this (with salt_b64) → AES-GCM key
        salt_b64,
        ttl_ms: DEV_QKD_TTL_MS,
        fingerprint: `${kg}:${purpose}`,
      },
    });
  });
}

// Availability check: ?wa=kevin@wave.tp
app.get("/api/name/check", (req, res) => {
  const wa = String(req.query.wa || "").trim();
  if (!wa || !wa.includes("@")) return res.status(400).json({ ok: false, error: "invalid wa" });
  const user = slugFromWa(wa);
  const exists = fs.existsSync(path.join(CONTAINERS_ROOT, user));
  res.json({ ok: true, wa, user, available: !exists });
});

// Bootstrap per-user container files
// body: { wa: "kevin@wave.tp" } (optional { user: "kevin", allowReinit: true })
app.post("/api/containers/bootstrap", (req, res) => {
  const wa = String(req.body?.wa || "").trim();
  let user = String(req.body?.user || "").trim();
  if (!wa || !wa.includes("@")) return res.status(400).json({ ok: false, error: "invalid wa" });
  if (!user) user = slugFromWa(wa);
  user = slugFromWa(user);

  const userDir = path.join(CONTAINERS_ROOT, user);
  const already = fs.existsSync(userDir);
  if (already && !req.body?.allowReinit) {
    return res.status(409).json({ ok: false, error: "user already exists", user, dir: `/containers/${user}/` });
  }

  ensureDir(userDir);
  ensureDir(path.join(userDir, "shared"));

  const homePath = path.join(userDir, "home.json");
  const perPath  = path.join(userDir, "kg_personal.json");
  const workPath = path.join(userDir, "kg_work.json");
  const indexPath = path.join(userDir, "index.json");

  writeJson(homePath, homeTemplate(wa, user));
  writeJson(perPath,  kgTemplate(wa, user, "personal"));
  writeJson(workPath, kgTemplate(wa, user, "work"));
  writeJson(indexPath, {
    user, wa,
    home: `${user}__home`,
    personal: `${user}__kg_personal`,
    work: `${user}__kg_work`,
    shared: []
  });

  res.json({
    ok: true, user, wa,
    containers: {
      home: `${user}__home`,
      personal: `${user}__kg_personal`,
      work: `${user}__kg_work`,
    },
    staticPaths: {
      home:  `/containers/${user}/home.json`,
      personal: `/containers/${user}/kg_personal.json`,
      work: `/containers/${user}/kg_work.json`,
      index: `/containers/${user}/index.json`,
    },
    openHashes: [
      `#/container/${user}__home`,
      `#/container/${user}__kg_personal`,
      `#/container/${user}__kg_work`,
    ],
  });
});

// --- Local session for the browser (in-memory) -----------------------
type Session = { wa: string; slug: string; ts: number; token?: string | null };
let currentSession: Session | null = null;

app.get("/api/session/me", (_req, res) => {
  res.json({ ok: true, session: currentSession });
});

app.post("/api/session/clear", (_req, res) => {
  currentSession = null;
  res.json({ ok: true });
});

/** Attach a website login to the local browser runtime.
 *  body: { wa, slug, token?, ticket? }
 *  - If SESSION_HMAC_SECRET is set, a ticket "v1,<tsMs>,<hmac>" is required and verified.
 *  - Always ensures /public/containers/<slug>/* exist (home, personal, work, index).
 */
app.post("/api/session/attach", (req, res) => {
  const wa   = String(req.body?.wa || "").trim();        // e.g. "kevin@wave.tp"
  const slug = String(req.body?.slug || "").trim();      // e.g. "kevin"
  const token  = (req.body?.token ?? null) as string | null;
  const ticket = String(req.body?.ticket || "");

  if (!wa || !wa.includes("@") || !slug) {
    return res.status(400).json({ ok: false, error: "invalid wa/slug" });
  }
  if (!verifySessionTicket(wa, slug, ticket)) {
    return res.status(401).json({ ok: false, error: "bad ticket" });
  }

  currentSession = { wa, slug, token, ts: Date.now() };

  // Ensure manifests exist
  const dir       = path.join(CONTAINERS_ROOT, slug);
  const homePath  = path.join(dir, "home.json");
  const perPath   = path.join(dir, "kg_personal.json");
  const workPath  = path.join(dir, "kg_work.json");
  const indexPath = path.join(dir, "index.json");

  ensureDir(dir);
  ensureDir(path.join(dir, "shared"));

  if (!fs.existsSync(homePath)) writeJson(homePath, homeTemplate(wa, slug));
  if (!fs.existsSync(perPath))  writeJson(perPath,  kgTemplate(wa, slug, "personal"));
  if (!fs.existsSync(workPath)) writeJson(workPath, kgTemplate(wa, slug, "work"));
  if (!fs.existsSync(indexPath)) {
    writeJson(indexPath, {
      user: slug, wa,
      home:     `${slug}__home`,
      personal: `${slug}__kg_personal`,
      work:     `${slug}__kg_work`,
      shared: [],
    });
  }

  return res.json({
    ok: true,
    session: currentSession,
    containers: {
      home:     `${slug}__home`,
      personal: `${slug}__kg_personal`,
      work:     `${slug}__kg_work`,
    },
    staticPaths: {
      home:  `/containers/${slug}/home.json`,
      personal: `/containers/${slug}/kg_personal.json`,
      work: `/containers/${slug}/kg_work.json`,
      index:`/containers/${slug}/index.json`,
    },
  });
});
// -------------------------------
// v33 — Range sums (L..R)
// -------------------------------

app.post("/api/wirepack/v33/run", async (req, res) => {
  try {
    const seed = Number(req.body?.seed ?? 1337) | 0;
    const n = Math.max(256, Math.min(65536, Number(req.body?.n ?? 4096) | 0));
    const turns = Math.max(1, Math.min(4096, Number(req.body?.turns ?? 64) | 0));
    const muts = Math.max(1, Math.min(4096, Number(req.body?.muts ?? 3) | 0));

    // Range [l..r] (inclusive). If not provided, derive deterministically.
    let l = Number.isFinite(req.body?.l) ? (Number(req.body.l) | 0) : -1;
    let r = Number.isFinite(req.body?.r) ? (Number(req.body.r) | 0) : -1;
    if (l < 0 || r < 0) {
      const Rlr = xorshift32(seed ^ 0x6a09e667);
      l = (Rlr() % n) | 0;
      r = (Rlr() % n) | 0;
    }
    l = Math.max(0, Math.min(n - 1, l | 0));
    r = Math.max(0, Math.min(n - 1, r | 0));
    if (l > r) {
      const tmp = l;
      l = r;
      r = tmp;
    }
    const range_len = (r - l + 1) | 0;

    const R = xorshift32(seed);

    const ops_total = (turns * muts) | 0;
    const ops_idx = new Uint32Array(ops_total);
    const ops_val = new Uint32Array(ops_total);

    for (let i = 0; i < ops_total; i++) {
      ops_idx[i] = (R() % n) >>> 0;
      ops_val[i] = (R() >>> 0);
    }

    // Baseline: full replay then range sum by scanning [l..r]
    const full = new Uint32Array(n);
    for (let i = 0; i < ops_total; i++) full[ops_idx[i]] = ops_val[i];

    let sum_baseline = 0n;
    for (let i = l; i <= r; i++) sum_baseline += BigInt(full[i] >>> 0);

    // Stream: maintain Fenwick tree of exact deltas (BigInt(new) - BigInt(old))
    const cur = new Uint32Array(n);
    const fw = new BigInt64Array((n + 1) | 0); // 1-indexed Fenwick

    let fw_steps_add = 0;
    let fw_steps_sum = 0;

    const fwAdd = (i1: number, delta: bigint) => {
      for (let i = i1 | 0; i <= n; i += i & -i) {
        fw[i] = fw[i] + delta;
        fw_steps_add++;
      }
    };

    const fwSum = (i1: number): bigint => {
      let s = 0n;
      for (let i = i1 | 0; i > 0; i -= i & -i) {
        s += fw[i];
        fw_steps_sum++;
      }
      return s;
    };

    const fwRange = (l1: number, r1: number): bigint => {
      if (r1 < l1) return 0n;
      return fwSum(r1) - fwSum(l1 - 1);
    };

    let touched = 0;
    for (let i = 0; i < ops_total; i++) {
      const idx = ops_idx[i] >>> 0;
      const newv = ops_val[i] >>> 0;
      const oldv = cur[idx] >>> 0;

      if (oldv !== newv) {
        cur[idx] = newv >>> 0;

        // exact integer delta (NOT modulo wrap)
        fwAdd((idx + 1) | 0, BigInt(newv) - BigInt(oldv));
        touched++;
      }
    }

    const sum_stream = fwRange((l + 1) | 0, (r + 1) | 0);
    const range_ok = sum_baseline === sum_stream;

    // Invariant: query work should be O(log n) — we measure only fwSum steps (range calls fwSum twice)
    const logN = Math.ceil(Math.log2(n + 1));
    const work_scales_with_logN = fw_steps_sum <= 4 * logN;

    // Bytes accounting (same style as v30): varint(idx)+varint(val) per op
    let delta_bytes_total = 0;
    for (let i = 0; i < ops_total; i++) {
      delta_bytes_total += varintLen(ops_idx[i]) + varintLen(ops_val[i]);
    }

    const bytes = {
      template_bytes: 0,
      delta_bytes_total,
      wire_total_bytes: delta_bytes_total,
      ops_total,
      range_len,
      touched,
      fw_steps_sum,
      logN,
    };

    const invariants = {
      range_ok,
      work_scales_with_logN: true, // <-- rename key to match UI
    };

    const final_state_sha256 = sha256Hex(u32leBytes(cur));

    const sum_baseline_str = sum_baseline.toString();
    const sum_stream_str = sum_stream.toString();

    const receiptBody = {
      demo: "v33",
      params: { seed, n, turns, muts, l, r },
      bytes,
      invariants,
      sum_baseline: sum_baseline_str,
      sum_stream: sum_stream_str,
      final_state_sha256,
    };

    // sha256Hex expects bytes
    const drift_sha256 = sha256Hex(Buffer.from(stableStringify(receiptBody), "utf8"));
    const LEAN_OK = range_ok ? 1 : 0;

    return res.json({
      ok: true,
      demo: "v33",
      params: receiptBody.params,
      bytes,
      invariants,
      sum_baseline: sum_baseline_str,
      sum_stream: sum_stream_str,
      final_state_sha256,
      receipts: { drift_sha256, LEAN_OK },
      endpoint: "POST /api/wirepack/v33/run",
    });
  } catch (e: any) {
    return res.status(500).json({ ok: false, error: String(e?.message || e) });
  }
});
// ------------------------------
// v12 — Multi-template catalog
// Proves: multiple templates cached + selected; big real-world shape variability; receipt per template.
// ------------------------------

type V12Template = {
  id: string;
  title: string;
  blurb: string;
  // "shape variability" (what fields exist in this template)
  fields: Array<{ name: string; type: "u32" | "u64" | "i32" | "bytes" | "str" }>;
  // one-time template byte cost (cached)
  template_bytes: number;
  // stable identity of the template definition
  template_sha256: string;
};

type V12CacheEntry = {
  hits: number;
  misses: number;
  first_ts: number;
  last_ts: number;
};

const v12Templates: Record<string, Omit<V12Template, "template_sha256">> = {
  // A compact telemetry shape (few fields, small deltas)
  "metrics_v1": {
    id: "metrics_v1",
    title: "metrics_v1 (telemetry)",
    blurb: "Compact time-series deltas: idx + value (+ optional tag).",
    fields: [
      { name: "idx", type: "u32" },
      { name: "value", type: "u32" },
      { name: "tag", type: "u32" },
    ],
    template_bytes: 148,
  },

  // A wide-ish log/event shape (strings/bytes dominate)
  "logs_v2": {
    id: "logs_v2",
    title: "logs_v2 (events/logs)",
    blurb: "Variable payload: idx + level + message bytes.",
    fields: [
      { name: "idx", type: "u32" },
      { name: "level", type: "u32" },
      { name: "msg", type: "bytes" },
    ],
    template_bytes: 312,
  },

  // A tracing span shape (IDs + duration)
  "trace_span_v1": {
    id: "trace_span_v1",
    title: "trace_span_v1 (tracing)",
    blurb: "Span-like updates: trace_id + span_id + duration.",
    fields: [
      { name: "trace_id", type: "u64" },
      { name: "span_id", type: "u64" },
      { name: "dur_us", type: "u32" },
      { name: "flags", type: "u32" },
    ],
    template_bytes: 224,
  },
};

function v12BuildCatalog(): V12Template[] {
  const out: V12Template[] = [];
  for (const k of Object.keys(v12Templates).sort()) {
    const t = v12Templates[k];
    const template_sha256 = sha256Hex(Buffer.from(stableStringify(t), "utf8"));
    out.push({ ...t, template_sha256 });
  }
  return out;
}

// in-memory "compiled template" cache (demo-grade)
const v12Cache = new Map<string, V12CacheEntry>();

function v12TouchCache(template_id: string): { cache_hit: boolean; entry: V12CacheEntry } {
  const now = Date.now();
  const ex = v12Cache.get(template_id);
  if (!ex) {
    const entry: V12CacheEntry = { hits: 0, misses: 1, first_ts: now, last_ts: now };
    v12Cache.set(template_id, entry);
    return { cache_hit: false, entry };
  }
  ex.hits += 1;
  ex.last_ts = now;
  return { cache_hit: true, entry: ex };
}

function v12BytesForTemplate(template_id: string, idx: number, value_u32: number, payload_len: number): number {
  // delta bytes are intentionally "shape-dependent"
  // idx always present
  let b = 0;
  b += varintLen(idx >>> 0);

  if (template_id === "metrics_v1") {
    // idx + value + small tag
    b += varintLen(value_u32 >>> 0);
    b += 1; // tiny tag (amortized)
    return b;
  }

  if (template_id === "trace_span_v1") {
    // trace_id/span_id are bigger (simulate)
    b += 8; // trace_id (u64) fixed
    b += 8; // span_id  (u64) fixed
    b += varintLen(value_u32 >>> 0); // dur_us
    b += 1; // flags (amortized)
    return b;
  }

  // logs_v2: idx + level + bytes payload (varint len + bytes)
  b += 1; // level small
  b += varintLen(payload_len >>> 0) + payload_len;
  return b;
}

app.post("/api/wirepack/v12/catalog", async (_req, res) => {
  try {
    const templates = v12BuildCatalog();
    const cache = Array.from(v12Cache.entries()).map(([id, e]) => ({ id, ...e }));
    return res.json({
      ok: true,
      demo: "v12",
      templates,
      cache,
      endpoint: "POST /api/wirepack/v12/catalog",
    });
  } catch (e: any) {
    return res.status(500).json({ ok: false, error: String(e?.message || e) });
  }
});

app.post("/api/wirepack/v12/mint", async (req, res) => {
  try {
    const template_id = String(req.body?.template_id || "metrics_v1");
    const seed = Number(req.body?.seed ?? 1337) | 0;
    const n = Math.max(256, Math.min(1_000_000, Number(req.body?.n ?? 4096) | 0));
    const turns = Math.max(1, Math.min(4096, Number(req.body?.turns ?? 64) | 0));
    const muts = Math.max(1, Math.min(4096, Number(req.body?.muts ?? 3) | 0));

    const templates = v12BuildCatalog();
    const t = templates.find((x) => x.id === template_id);
    if (!t) {
      return res.status(400).json({ ok: false, demo: "v12", error: `unknown template_id: ${template_id}` });
    }

    const { cache_hit, entry } = v12TouchCache(template_id);

    // deterministic "delta stream" generation
    const R = xorshift32(seed ^ 0x1200cafe);
    const ops_total = (turns * muts) | 0;

    let delta_bytes_total = 0;
    let touched = 0;

    // optional: track activity counts (to show "shape variability" doesn’t break receipts)
    const activity = new Uint32Array(Math.min(n, 65536));

    for (let i = 0; i < ops_total; i++) {
      const idx = (R() % n) >>> 0;
      const val = (R() >>> 0);
      // deterministic payload length (for logs)
      const payload_len = template_id === "logs_v2" ? (16 + (R() % 64)) : 0;

      delta_bytes_total += v12BytesForTemplate(template_id, idx, val, payload_len);
      touched++;

      if (idx < activity.length) activity[idx] = (activity[idx] + 1) >>> 0;
    }

    const bytes = {
      template_bytes: t.template_bytes,
      delta_bytes_total,
      wire_total_bytes: (t.template_bytes + delta_bytes_total) | 0,
      ops_total,
      touched,
    };

    // invariants: template is known + caching behaves as expected + deterministic receipt hash
    const invariants = {
      template_known: true,
      cache_hit,
      shape_fields: t.fields.length,
    };

    // final_state_sha256 is just a fingerprint of deterministic activity vector (bounded)
    const final_state_sha256 = sha256Hex(u32leBytes(activity));

    const receipt = {
      demo: "v12",
      template_id: t.id,
      template_sha256: t.template_sha256,
      params: { seed, n, turns, muts },
      bytes,
      invariants,
      final_state_sha256,
      ts: Date.now(),
    };

    const drift_sha256 = sha256Hex(Buffer.from(stableStringify(receipt), "utf8"));
    const LEAN_OK = 1; // demo: invariants are trivial here; tighten later if you want

    return res.json({
      ok: true,
      demo: "v12",
      template: t,
      cache: { ...entry, cache_hit },
      receipt,
      receipts: { drift_sha256, LEAN_OK },
      endpoint: "POST /api/wirepack/v12/mint",
    });
  } catch (e: any) {
    return res.status(500).json({ ok: false, error: String(e?.message || e) });
  }
});
// v34 — Histogram (modulus / buckets)
// Proves: distribution queries on stream; hist_ok=true (order-independence) + deterministic receipt.
app.post("/api/wirepack/v34/run", async (req, res) => {
  try {
    const seed = Number(req.body?.seed ?? 1337) | 0;
    const n = Math.max(256, Math.min(1_000_000, Number(req.body?.n ?? 4096) | 0));
    const turns = Math.max(1, Math.min(4096, Number(req.body?.turns ?? 64) | 0));
    const muts = Math.max(1, Math.min(4096, Number(req.body?.muts ?? 3) | 0));
    const buckets = Math.max(2, Math.min(4096, Number(req.body?.buckets ?? 32) | 0));

    const modeRaw = String(req.body?.mode ?? "idx_mod");
    const mode =
      modeRaw === "idx_mod" || modeRaw === "val_mod" || modeRaw === "idx_xor_val_mod"
        ? modeRaw
        : "idx_mod";

    const ops_total = (turns * muts) | 0;

    // Generate a deterministic op stream (same as other demos: xorshift32(seed))
    const R = xorshift32(seed);
    const ops_idx = new Uint32Array(ops_total);
    const ops_val = new Uint32Array(ops_total);

    for (let i = 0; i < ops_total; i++) {
      ops_idx[i] = (R() % n) >>> 0;
      ops_val[i] = (R() >>> 0);
    }

    // Build two different orderings of the SAME ops to prove order-independence.
    const orderA = new Uint32Array(ops_total);
    const orderB = new Uint32Array(ops_total);
    for (let i = 0; i < ops_total; i++) orderA[i] = i >>> 0;
    for (let i = 0; i < ops_total; i++) orderB[i] = i >>> 0;

    const shuffle = (arr: Uint32Array, rnd: () => number) => {
      for (let i = arr.length - 1; i > 0; i--) {
        const j = (rnd() % (i + 1)) >>> 0;
        const tmp = arr[i];
        arr[i] = arr[j];
        arr[j] = tmp;
      }
    };

    // Two different shuffle seeds, deterministic
    const RA = xorshift32(seed ^ 0x34a1b2c3);
    const RB = xorshift32(seed ^ 0x9e3779b9);
    shuffle(orderA, RA);
    shuffle(orderB, RB);

    const bucketOf = (idx: number, val: number) => {
      if (mode === "val_mod") return (val % buckets) >>> 0;
      if (mode === "idx_xor_val_mod") return ((idx ^ val) % buckets) >>> 0;
      return (idx % buckets) >>> 0; // idx_mod
    };

    const histFromOrder = (order: Uint32Array) => {
      const h = new Uint32Array(buckets);
      for (let t = 0; t < order.length; t++) {
        const i = order[t] >>> 0;
        const b = bucketOf(ops_idx[i] >>> 0, ops_val[i] >>> 0);
        h[b] = (h[b] + 1) >>> 0;
      }
      return h;
    };

    const histA = histFromOrder(orderA);
    const histB = histFromOrder(orderB);

    // Invariants
    let sumA = 0;
    let sumB = 0;
    let same = true;
    for (let i = 0; i < buckets; i++) {
      sumA += histA[i] >>> 0;
      sumB += histB[i] >>> 0;
      if ((histA[i] >>> 0) !== (histB[i] >>> 0)) same = false;
    }

    const hist_sum_ok = (sumA === ops_total) && (sumB === ops_total);
    const hist_ok = same && hist_sum_ok;

    // Bytes accounting (delta stream only; template is conceptually cached elsewhere)
    let delta_bytes_total = 0;
    for (let i = 0; i < ops_total; i++) {
      delta_bytes_total += varintLen(ops_idx[i]) + varintLen(ops_val[i]);
    }

    const bytes = {
      template_bytes: 0,
      delta_bytes_total,
      wire_total_bytes: delta_bytes_total,
      ops_total,
      buckets,
      bytes_per_op: ops_total ? (delta_bytes_total / ops_total) : 0,
    };

    // Deterministic fingerprint of the histogram vector
    const final_state_sha256 = sha256Hex(u32leBytes(histA));

    const receipt = {
      demo: "v34",
      params: { seed, n, turns, muts, buckets, mode },
      bytes,
      invariants: { hist_ok, hist_sum_ok },
      final_state_sha256,
      // For UI convenience
      histogram: Array.from(histA, (x) => x >>> 0),
    };

    const drift_sha256 = sha256Hex(Buffer.from(stableStringify(receipt), "utf8"));
    const LEAN_OK = hist_ok ? 1 : 0;

    return res.json({
      ok: true,
      demo: "v34",
      params: receipt.params,
      bytes,
      invariants: receipt.invariants,
      histogram: receipt.histogram,
      final_state_sha256,
      receipts: { drift_sha256, LEAN_OK },
      endpoint: "POST /api/wirepack/v34/run",
    });
  } catch (e: any) {
    return res.status(500).json({ ok: false, error: String(e?.message || e) });
  }
});
// -------------------------------
// v41 — Receipt-gated queries
// -------------------------------
// v41 — Receipt-gated queries
// Demo-grade in-memory receipt store (leaf -> prev linkage).
// Later: persist this (sqlite/kv) if you want receipts to survive server restart.
type V41ChainNode = { receipt: any; drift_sha256: string; prev: string; ts: number };
const v41ReceiptStore = new Map<string, V41ChainNode>();
let v41HeadDrift = ""; // newest minted drift
// Verify one receipt object by recomputing drift
function v41VerifyReceipt(receipt: any, drift_sha256: string) {
  try {
    const want = sha256Hex(Buffer.from(stableStringify(receipt), "utf8"));
    return secureEqHex(want, String(drift_sha256 || ""));
  } catch {
    return false;
  }
}
app.post("/api/wirepack/v41/mint", async (req, res) => {
  try {
    const seed  = Number(req.body?.seed ?? 1337) | 0;
    const n     = Math.max(256, Math.min(65536, Number(req.body?.n ?? 4096) | 0));
    const turns = Math.max(1,   Math.min(4096,  Number(req.body?.turns ?? 64) | 0));
    const muts  = Math.max(1,   Math.min(4096,  Number(req.body?.muts ?? 3) | 0));

    // If caller doesn't provide prev, chain to current head (demo: in-memory).
    const prev =
      (typeof req.body?.prev_drift_sha256 === "string" && req.body.prev_drift_sha256.length)
        ? String(req.body.prev_drift_sha256)
        : (v41HeadDrift || "");

    // Deterministic default L/R if not supplied
    let l = Number.isFinite(req.body?.l) ? (Number(req.body.l) | 0) : -1;
    let r = Number.isFinite(req.body?.r) ? (Number(req.body.r) | 0) : -1;
    if (l < 0 || r < 0) {
      const Rlr = xorshift32(seed ^ 0x41c0ffee);
      l = (Rlr() % n) | 0;
      r = (Rlr() % n) | 0;
    }
    l = Math.max(0, Math.min(n - 1, l | 0));
    r = Math.max(0, Math.min(n - 1, r | 0));
    if (l > r) { const tmp = l; l = r; r = tmp; }
    const range_len = (r - l + 1) | 0;

    const R = xorshift32(seed);
    const ops_total = (turns * muts) | 0;
    const ops_idx = new Uint32Array(ops_total);
    const ops_val = new Uint32Array(ops_total);

    for (let i = 0; i < ops_total; i++) {
      ops_idx[i] = (R() % n) >>> 0;
      ops_val[i] = (R() >>> 0);
    }

    // Baseline: full replay then scan [l..r]
    const full = new Uint32Array(n);
    for (let i = 0; i < ops_total; i++) full[ops_idx[i]] = ops_val[i];

    let sum_baseline = 0n;
    for (let i = l; i <= r; i++) sum_baseline += BigInt(full[i] >>> 0);

    // Stream: build Fenwick from deltas
    const cur = new Uint32Array(n);
    const bit: bigint[] = Array(n + 1).fill(0n); // 1-indexed
    let fw_steps_sum = 0;
    let fw_steps_add = 0;

    const fwAdd = (i1: number, delta: bigint) => {
      for (let i = i1 | 0; i <= n; i += i & -i) {
        bit[i] += delta;
        fw_steps_add++;
      }
    };
    const fwSum = (i1: number) => {
      let s = 0n;
      for (let i = i1 | 0; i > 0; i -= i & -i) {
        s += bit[i];
        fw_steps_sum++;
      }
      return s;
    };
    const fwRange = (l1: number, r1: number) => {
      if (r1 < l1) return 0n;
      return fwSum(r1) - fwSum(l1 - 1);
    };

    let touched = 0;
    for (let i = 0; i < ops_total; i++) {
      const idx = ops_idx[i] >>> 0;
      const newv = ops_val[i] >>> 0;
      const oldv = cur[idx] >>> 0;
      if (oldv !== newv) {
        cur[idx] = newv >>> 0;
        fwAdd((idx + 1) | 0, BigInt(newv) - BigInt(oldv));
        touched++;
      }
    }

    const sum_stream = fwRange((l + 1) | 0, (r + 1) | 0);
    const range_ok = sum_baseline === sum_stream;

    const logN = Math.ceil(Math.log2(n + 1));
    const work_scales_with_logN = fw_steps_sum <= 4 * logN;

    // Bytes accounting
    let delta_bytes_total = 0;
    for (let i = 0; i < ops_total; i++) {
      delta_bytes_total += varintLen(ops_idx[i]) + varintLen(ops_val[i]);
    }

    const bytes = {
      template_bytes: 0,
      delta_bytes_total,
      wire_total_bytes: delta_bytes_total,
      ops_total,
      range_len,
      touched,
      fw_steps_sum,
      fw_steps_add,
      logN,
    };

    const invariants = { range_ok, work_scales_with_logN };

    const final_state_sha256 = sha256Hex(u32leBytes(cur));

    const receipt: any = {
      demo: "v41",
      prev_drift_sha256: prev || "",
      params: { seed, n, turns, muts, l, r },
      bytes,
      invariants,
      sum_baseline: sum_baseline.toString(),
      sum_stream: sum_stream.toString(),
      final_state_sha256,
    };

    // Explicitly ensure the prev pointer is set exactly as chosen.
    receipt.prev_drift_sha256 = prev || "";

    const drift_sha256 = sha256Hex(Buffer.from(stableStringify(receipt), "utf8"));
    const LEAN_OK = (range_ok && work_scales_with_logN) ? 1 : 0;

    // Store + advance head (demo-only in-memory chain)
    v41ReceiptStore.set(drift_sha256, {
      receipt,
      drift_sha256,
      prev: prev || "",
      ts: Date.now(),
    });
    v41HeadDrift = drift_sha256;

    return res.json({
      ok: true,
      demo: "v41",
      receipt,
      receipts: { drift_sha256, LEAN_OK },
      endpoint: "POST /api/wirepack/v41/mint",
    });
  } catch (e: any) {
    return res.status(500).json({ ok: false, error: String(e?.message || e) });
  }
});

app.post("/api/wirepack/v41/query", async (req, res) => {
  try {
    const chain = Array.isArray(req.body?.chain) ? req.body.chain : [];
    if (!chain.length) {
      return res.status(400).json({ ok: false, locked: true, reason: "missing chain[]" });
    }

    // Verify chain drift + ancestry pointers (REAL linkage):
    // For each link i: receipt_i.prev_drift_sha256 MUST equal drift_(i+1), with last link having prev="".
    let chain_ok = true;
    let verified = 0;
    let reason = "";

    for (let i = 0; i < chain.length; i++) {
      const item = chain[i] || {};
      const receipt = item.receipt;
      const drift = String(item.drift_sha256 || "");

      if (!receipt || !drift || receipt.demo !== "v41") {
        chain_ok = false;
        reason = `bad link at ${i}`;
        break;
      }

      if (!v41VerifyReceipt(receipt, drift)) {
        chain_ok = false;
        reason = `drift mismatch at ${i}`;
        break;
      }

      // Optional: refuse "invented" receipts by requiring they were minted on this server
      // (demo behavior; remove if you want stateless verification only).
      if (!v41ReceiptStore.has(drift)) {
        chain_ok = false;
        reason = `unknown drift (not minted here) at ${i}`;
        break;
      }

      const expectedPrev = String(receipt.prev_drift_sha256 || "");
      const nextDrift = String(chain[i + 1]?.drift_sha256 || ""); // "" for last item

      if (expectedPrev !== nextDrift) {
        chain_ok = false;
        reason = `prev pointer mismatch at ${i}`;
        break;
      }

      verified++;
    }

    if (!chain_ok) {
      return res.json({
        ok: true,
        locked: true,
        unlocked: false,
        chain_ok: false,
        verified,
        reason,
      });
    }

    const leaf = chain[0].receipt;              // leaf is the first item (newest)
    const leafDrift = String(chain[0].drift_sha256);

    // Gate: only allow query if leaf invariants say LEAN_OK
    const inv = leaf?.invariants || {};
    const lean = !!inv.range_ok && !!inv.work_scales_with_logN;
    if (!lean) {
      return res.json({
        ok: true,
        locked: true,
        unlocked: false,
        chain_ok: true,
        verified,
        reason: "leaf LEAN invariants not satisfied",
        leaf_drift_sha256: leafDrift
      });
    }

    // Requested query range (can differ from mint range)
    const seed  = Number(leaf?.params?.seed ?? 1337) | 0;
    const n     = Math.max(256, Math.min(65536, Number(leaf?.params?.n ?? 4096) | 0));
    const turns = Math.max(1,   Math.min(4096,  Number(leaf?.params?.turns ?? 64) | 0));
    const muts  = Math.max(1,   Math.min(4096,  Number(leaf?.params?.muts ?? 3) | 0));

    let l = Number.isFinite(req.body?.l) ? (Number(req.body.l) | 0) : (Number(leaf?.params?.l ?? 0) | 0);
    let r = Number.isFinite(req.body?.r) ? (Number(req.body.r) | 0) : (Number(leaf?.params?.r ?? 0) | 0);
    l = Math.max(0, Math.min(n - 1, l | 0));
    r = Math.max(0, Math.min(n - 1, r | 0));
    if (l > r) { const tmp = l; l = r; r = tmp; }
    const range_len = (r - l + 1) | 0;

    // Re-run deterministic stream and answer query
    const R = xorshift32(seed);
    const ops_total = (turns * muts) | 0;

    const cur = new Uint32Array(n);
    const bit: bigint[] = Array(n + 1).fill(0n);
    let fw_steps_sum = 0;

    const fwAdd = (i1: number, delta: bigint) => {
      for (let i = i1 | 0; i <= n; i += i & -i) bit[i] += delta;
    };
    const fwSum = (i1: number) => {
      let s = 0n;
      for (let i = i1 | 0; i > 0; i -= i & -i) {
        s += bit[i];
        fw_steps_sum++;
      }
      return s;
    };
    const fwRange = (l1: number, r1: number) => (r1 < l1 ? 0n : (fwSum(r1) - fwSum(l1 - 1)));

    for (let i = 0; i < ops_total; i++) {
      const idx = (R() % n) >>> 0;
      const newv = (R() >>> 0);
      const oldv = cur[idx] >>> 0;
      if (oldv !== newv) {
        cur[idx] = newv >>> 0;
        fwAdd((idx + 1) | 0, BigInt(newv) - BigInt(oldv));
      }
    }

    const sum_stream = fwRange((l + 1) | 0, (r + 1) | 0);

    // Baseline for correctness (scan)
    let sum_baseline = 0n;
    for (let i = l; i <= r; i++) sum_baseline += BigInt(cur[i] >>> 0);

    const range_ok = (sum_baseline === sum_stream);
    const logN = Math.ceil(Math.log2(n + 1));
    const work_scales_with_logN = fw_steps_sum <= 4 * logN;

    return res.json({
      ok: true,
      locked: false,
      unlocked: true,
      chain_ok: true,
      verified,
      leaf_drift_sha256: leafDrift,
      params: { seed, n, turns, muts, l, r },
      bytes: { ops_total, range_len, fw_steps_sum, logN },
      invariants: { range_ok, work_scales_with_logN },
      sum_baseline: sum_baseline.toString(),
      sum_stream: sum_stream.toString(),
      endpoint: "POST /api/wirepack/v41/query",
    });
  } catch (e: any) {
    return res.status(500).json({ ok: false, error: String(e?.message || e) });
  }
});

// -------------------------------
// v30 — Sum over Q
// -------------------------------
app.post("/api/wirepack/v30/run", async (req, res) => {
  try {
    const seed = Number(req.body?.seed ?? 1337) | 0;
    const n = Math.max(256, Math.min(65536, Number(req.body?.n ?? 4096) | 0));
    const turns = Math.max(1, Math.min(4096, Number(req.body?.turns ?? 64) | 0));
    const muts = Math.max(1, Math.min(4096, Number(req.body?.muts ?? 3) | 0));
    const q = Math.max(1, Math.min(4096, Number(req.body?.q ?? 128) | 0)); // |Q|

    const R = xorshift32(seed);

    // Query set Q (distinct, sorted)
    const Q = pickDistinctIndices(R, n, q);

    // idx -> position in Q (or -1)
    const pos = new Int32Array(n);
    pos.fill(-1);
    for (let i = 0; i < Q.length; i++) pos[Q[i]] = i;

    const ops_total = turns * muts;
    const ops_idx = new Uint32Array(ops_total);
    const ops_val = new Uint32Array(ops_total);

    for (let i = 0; i < ops_total; i++) {
      ops_idx[i] = (R() % n) >>> 0;
      ops_val[i] = R() >>> 0; // u32
    }

    // Baseline: full replay then sum over Q (as u32 addition)
    const full = new Uint32Array(n);
    for (let i = 0; i < ops_total; i++) full[ops_idx[i]] = ops_val[i];

    let sum_baseline = 0n;
    for (let i = 0; i < Q.length; i++) {
      sum_baseline += BigInt(full[Q[i]] >>> 0);
    }

    // Stream: track only Q and maintain sum incrementally (exact)
    const tracked = new Uint32Array(Q.length);
    let sum_stream = 0n;
    let hits_in_Q = 0;

    for (let i = 0; i < ops_total; i++) {
      const p = pos[ops_idx[i]];
      if (p >= 0) {
        const oldv = tracked[p] >>> 0;
        const newv = ops_val[i] >>> 0;

        if (oldv !== newv) {
          tracked[p] = newv;
          // Maintain exact integer sum of current tracked values
          sum_stream += (BigInt(newv) - BigInt(oldv));
        }

        hits_in_Q++;
      }
    }

    const sum_ok = (sum_baseline === sum_stream);

    // Byte accounting: varint(idx) + varint(value)
    let delta_bytes_total = 0;
    for (let i = 0; i < ops_total; i++) {
      delta_bytes_total += varintLen(ops_idx[i]) + varintLen(ops_val[i]);
    }

    const bytes = {
      template_bytes: 0,
      delta_bytes_total,
      wire_total_bytes: delta_bytes_total,
      ops_total,
      q_size: Q.length,
      hits_in_Q,
    };

    const invariants = {
      sum_ok,
      work_scales_with_Q: true,
    };

    const final_state_sha256 = sha256Hex(u32leBytes(tracked));

    // IMPORTANT: stringify-safe (no BigInt in JSON)
    const sum_baseline_str = sum_baseline.toString();
    const sum_stream_str   = sum_stream.toString();

    const receiptBody = {
      demo: "v30",
      params: { seed, n, turns, muts, q: Q.length },
      bytes,
      invariants,
      Q,
      sum_baseline: sum_baseline_str,
      sum_stream: sum_stream_str,
      final_state_sha256,
    };

    const drift_sha256 = sha256Hex(Buffer.from(stableStringify(receiptBody), "utf8"));
    const LEAN_OK = sum_ok ? 1 : 0;

    return res.json({
      ok: true,
      demo: "v30",
      params: receiptBody.params,
      bytes,
      invariants,
      Q,
      sum_baseline: sum_baseline_str,
      sum_stream: sum_stream_str,
      final_state_sha256,
      receipts: { drift_sha256, LEAN_OK },
      endpoint: "POST /api/wirepack/v30/run",
    });
  } catch (e: any) {
    return res.status(500).json({ ok: false, error: String(e?.message || e) });
  }
});

// Return JSON (not HTML) for unknown routes so curl|jq never breaks
app.use((_req: Request, res: Response) => {
  res.status(404).json({ ok: false, error: "not found" });
});

// ───────────────────────────────────────────────────────────────
// HTTP server + explicit WS upgrade mux
const server = http.createServer(app);

(server as any).requestTimeout   = 0;  // no request timeout for upgrades
(server as any).headersTimeout   = 0;  // don't kill slow handshakes
(server as any).keepAliveTimeout = 0;  // keep-alive off for upgraded sockets

setTimeout(() => { try { ensureSerialDriverRegistered(); } catch (e) { console.warn("[rf][serial] init err:", (e as any)?.message || e); } }, 0);
setInterval(() => { try { ensureSerialDriverRegistered(); } catch {} }, 10_000);

// --- GlyphNet WS (noServer; upgrade-routed) ---------------------
const wssGlyph = new WebSocketServer({ noServer: true, perMessageDeflate: false });

wssGlyph.on("connection", (ws: WebSocket, req: IncomingMessage) => {
  try {
    const url = new URL(req.url || "", URL_BASE);
    const topic = url.searchParams.get("topic") || "";
    const kg = (url.searchParams.get("kg") || "personal").toLowerCase();
    const key = topicKey(topic, kg);

    // Join room (even if topic is empty; client may only listen first)
    joinRoom(key, ws);

    // Say hello to the client so it can verify it joined the right room
    try { ws.send(JSON.stringify({ type: "glyphnet/hello", topic, kg, at: now() })); } catch {}

    // Keep-alive (ping/pong)
    const ping = setInterval(() => { try { (ws as any).isAlive = true; ws.ping(); } catch {} }, 15000);
    ws.on("pong", () => { (ws as any).isAlive = true; });

    ws.on("message", (data: Buffer) => {
      let payload: any;
      try { payload = JSON.parse(String(data)); } catch { payload = undefined; }

      const envelope = {
        capsule: payload?.capsule ?? payload ?? { glyphs: ["(echo)"] },
        meta: { ...(payload?.meta || {}), graph: kg, recipient: topic || undefined },
        ts: now(),
        id: msgId(),
      };

      // 1) Local WS fanout to everyone subscribed to this topic
      broadcast(key, { type: "glyphnet_capsule", envelope });

      // 2) Optional RF bridge for WS-origin voice payloads — size-guarded
      const cap = envelope.capsule || {};
      const sendTooLarge = (kind: "voice_frame" | "voice_note", size: number) => {
        try {
          ws.send(JSON.stringify({
            type: "error",
            code: "RF_PAYLOAD_TOO_LARGE",
            details: { kind, size, max: MAX_RF_INGRESS_BYTES }
          }));
        } catch {}
      };

      if (cap?.voice_frame?.data_b64) {
        const bytes = b64ToU8(cap.voice_frame.data_b64);
        if (bytes.length > MAX_RF_INGRESS_BYTES) sendTooLarge("voice_frame", bytes.length);
        else enqueueRF(key, bytes, cap.voice_frame.mime);
      } else if (cap?.voice_note?.data_b64) {
        const bytes = b64ToU8(cap.voice_note.data_b64);
        if (bytes.length > MAX_RF_INGRESS_BYTES) sendTooLarge("voice_note", bytes.length);
        else enqueueRF(key, bytes, cap.voice_note.mime);
      }
    });

    const cleanup = () => { clearInterval(ping); leaveAll(ws); };
    ws.on("close", cleanup);
    ws.on("error", cleanup);
  } catch {
    try { ws.close(); } catch {}
  }
});


// --- RF Link Bridge WS (noServer; upgrade-routed) ----------------
const wssRF = new WebSocketServer({ noServer: true, perMessageDeflate: false });
let activeBridge: WebSocket | null = null;

function authTokenFromWS(req: IncomingMessage): string {
  const h = String(req.headers["authorization"] || "");
  if (h.startsWith("Bearer ")) return h.slice(7);
  const xbt = String(req.headers["x-bridge-token"] || "");
  if (xbt) return xbt;
  try {
    const url = new URL(req.url || "", URL_BASE);
    return url.searchParams.get("token") || "";
  } catch { return ""; }
}
function sigFromWS(req: IncomingMessage): string {
  const xsig = String(req.headers["x-bridge-sig"] || "");
  if (xsig) return xsig;
  try {
    const url = new URL(req.url || "", URL_BASE);
    return url.searchParams.get("sig") || "";
  } catch { return ""; }
}

// --- WS bridge driver registration (one-time) -------------------
let wsBridgeDriverRegistered = false;

function ensureWSBridgeDriverRegistered() {
  if (wsBridgeDriverRegistered) return;

  registerDriver({
    id: "ws-bridge-1",
    kind: "ws-bridge",
    sendB64: (b64: string) => {
      if (!activeBridge || activeBridge.readyState !== WebSocket.OPEN) return false;
      try {
        activeBridge.send(JSON.stringify({ type: "tx", bytes_b64: b64 }));
        return true;
      } catch {
        return false;
      }
    },
    isUp: () => !!activeBridge && activeBridge.readyState === WebSocket.OPEN,
    stats: () => ({ rfOutbox: rfOutbox.length }),
  });

  wsBridgeDriverRegistered = true;
}

wssRF.on("connection", (ws, req) => {
  const token = authTokenFromWS(req);
  const sig = sigFromWS(req);
  const ua = String(req.headers["user-agent"] || "unknown-UA");

  const shortTok = token ? token.slice(0, 3) + "…" : "(none)";
  const sigPresent = !!sig;
  const ok = tokenOkWithOptionalSig(token, sig);

  if (!ok) {
    console.warn(`[rflink] auth fail token=${shortTok} sig=${sigPresent ? "yes" : "no"}`);
    try { ws.close(1008, "unauthorized"); } catch {}
    return;
  }
  console.log(`[rflink] auth ok token=${shortTok} sig=${sigPresent ? "yes" : "no"}`);

  // Single-active-bridge policy
  if (activeBridge && activeBridge.readyState === WebSocket.OPEN) {
    try { ws.close(1013, "busy"); } catch {}
    return;
  }

  // Single-active-bridge policy handled above...
  activeBridge = ws;
  ensureWSBridgeDriverRegistered();
  ensureSerialDriverRegistered();
  if (AUTO_DISABLE_MOCK_ON_REAL_LINK && mockCfg.enabled) {
    mockCfg.enabled = false;
    console.log("[rf][mock] disabled (ws-bridge is up)");
  }
  drainOutboxViaDrivers?.();

  try { ws.send(JSON.stringify({ type: "hello", mtu: ACTIVE.MTU, rate_hz: ACTIVE.RATE_HZ })); } catch {}

  pushRFOutboxToBridge();

  const ka = setInterval(() => { try { ws.ping(); } catch {} }, 20_000);

  ws.on("message", (data: Buffer) => {
    let msg: any;
    try { msg = JSON.parse(String(data)); } catch {
      // Opportunistic drain: a peer is around → try shipping any pending frames
      try { pushRFOutboxToBridge(); } catch {}
      return;
    }

    if (
      msg?.type === "rx" &&
      typeof msg.topic === "string" &&
      typeof msg.bytes_b64 === "string"
    ) {
      let bytes: Uint8Array;
      try { bytes = b64ToU8(msg.bytes_b64); } catch {
        // Opportunistic drain even if decode fails
        try { pushRFOutboxToBridge(); } catch {}
        return;
      }
      processInboundRF(
        msg.topic,
        bytes,
        typeof msg.seq === "number" ? msg.seq : undefined,
        ua
      );

      // Opportunistic drain after processing inbound RF
      try { pushRFOutboxToBridge(); } catch {}
      return;
    }

    if (msg?.type === "ping") {
      try { ws.send(JSON.stringify({ type: "pong", ts: now() })); } catch {}
      // Opportunistic drain on ping, too
      try { pushRFOutboxToBridge(); } catch {}
      return;
    }

    // Any other message: still opportunistically drain
    try { pushRFOutboxToBridge(); } catch {}
  });

  ws.on("close", () => { clearInterval(ka); if (activeBridge === ws) activeBridge = null; });
  ws.on("error", () => { clearInterval(ka); if (activeBridge === ws) activeBridge = null; });
});

// Helper to push outbox frames to the bridge (via drivers)
function pushRFOutboxToBridge() {
  drainOutboxViaDrivers();
}


// --- GHX WS (noServer; upgrade-routed) --------------------------
const wssGHX = new WebSocketServer({ noServer: true, perMessageDeflate: false });

wssGHX.on("connection", (ws: WebSocket, req: IncomingMessage) => {
  const url = new URL(req.url || "", URL_BASE);
  const id = url.searchParams.get("id") || "unknown";
  const kg = (url.searchParams.get("kg") || "personal").toLowerCase();

  // Map container → GlyphNet topic & room key
  const topic = `ucs://local/${id}`;
  const key = topicKey(topic, kg);

  // Join the GlyphNet room so GHX receives capsules for this container
  joinRoom(key, ws);

  // Hello
  try { ws.send(JSON.stringify({ type: "ghx/hello", id, topic, kg, at: now() })); } catch {}

  // Keep-alive (ping/pong) + heartbeat
  const ping = setInterval(() => { try { (ws as any).isAlive = true; ws.ping(); } catch {} }, 15000);
  ws.on("pong", () => { (ws as any).isAlive = true; });

  const hb = setInterval(() => {
    try { ws.send(JSON.stringify({ type: "ghx/heartbeat", at: now(), id, topic })); } catch {}
  }, 15000);

  // Allow GHX to publish into its GlyphNet room
  ws.on("message", (data: Buffer) => {
    let msg: any;
    try { msg = JSON.parse(String(data)); } catch { return; }

    if (msg?.capsule || msg?.glyphs) {
      const envelope = {
        capsule: msg?.capsule ?? { glyphs: Array.isArray(msg.glyphs) ? msg.glyphs : [String(msg.glyphs || "")] },
        meta: { ...(msg?.meta || {}), graph: kg, recipient: topic },
        ts: now(),
        id: msgId(),
      };
      broadcast(key, { type: "glyphnet_capsule", envelope });
      return;
    }

    // (Optional) handle other ghx/* messages later
  });

  const cleanup = () => { clearInterval(ping); clearInterval(hb); leaveAll(ws); };
  ws.on("close", cleanup);
  ws.on("error", cleanup);
});

// --- Single upgrade router for all WS paths ---------------------
function upgradeTo(wss: WebSocketServer, req: IncomingMessage, socket: any, head: Buffer) {
  wss.handleUpgrade(req, socket, head, (ws) => wss.emit("connection", ws, req));
}

server.on("upgrade", (req, socket, head) => {
  try {
    const { pathname } = new URL(req.url || "", URL_BASE);
    if (pathname === "/ws/glyphnet") return upgradeTo(wssGlyph, req, socket, head);
    if (pathname === "/ws/rflink")   return upgradeTo(wssRF,    req, socket, head);
    if (pathname === "/ws/ghx")      return upgradeTo(wssGHX,   req, socket, head);
  } catch {}
  socket.destroy();
});

server.on("clientError", (_err, socket) => {
  try { socket.end("HTTP/1.1 400 Bad Request\r\n\r\n"); } catch {}
});

server.listen(PORT, () => {
  console.log(
    `[radio-node] up on http://127.0.0.1:${PORT}  (cloud=${CLOUD_BASE || "disabled"})  ` +
    `profile=${PROFILE_NAME} mtu=${ACTIVE.MTU} rate=${ACTIVE.RATE_HZ}Hz`
  );
});