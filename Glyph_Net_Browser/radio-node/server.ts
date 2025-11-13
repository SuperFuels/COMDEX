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

dotenv.config({ path: path.join(process.cwd(), ".env.local") });
dotenv.config(); // fallback to .env if present

// Optional YAML loader (fallback to defaults if not installed)
let YAML: any = null;
try { YAML = require("yaml"); } catch { /* optional */ }

// ───────────────────────────────────────────────────────────────
// Base64 → bytes
const b64ToU8 = (b64: string) => new Uint8Array(Buffer.from(b64, "base64"));

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

const BRIDGE_TOKEN = process.env.RADIO_BRIDGE_TOKEN || "dev-bridge";

// Optional rolling token for rotation
const BRIDGE_TOKEN_NEXT = process.env.RADIO_BRIDGE_TOKEN_NEXT || "";

// Constant-time string compare
function safeEq(a: string, b: string) {
  if (a.length !== b.length) return false;
  let r = 0;
  for (let i = 0; i < a.length; i++) r |= a.charCodeAt(i) ^ b.charCodeAt(i);
  return r === 0;
}

/** Validate X-Bridge-Sig: "v1,<tsMs>,<hmacHex>" where hmac = HMAC_SHA256(token, `ws-bridge|${tsMs}`) */
function validBridgeSig(sig: string, token: string): boolean {
  try {
    const [v, tsStr, mac] = String(sig).split(",");
    if (v !== "v1") return false;
    const ts = Number(tsStr);
    if (!Number.isFinite(ts)) return false;
    // 2-minute tolerance window
    if (Math.abs(Date.now() - ts) > 2 * 60_000) return false;
    const h = crypto.createHmac("sha256", token);
    h.update(`ws-bridge|${ts}`);
    const want = h.digest("hex");
    return safeEq(want, mac);
  } catch {
    return false;
  }
}

function tokenMatchesAny(tok: string) {
  return !!tok && (tok === BRIDGE_TOKEN || (BRIDGE_TOKEN_NEXT && tok === BRIDGE_TOKEN_NEXT));
}

function tokenOkWithOptionalSig(tok: string, sig?: string) {
  if (!tok) return false;
  // No signature → allow plain token (dev-friendly)
  if (!sig) return tokenMatchesAny(tok);
  // Signature present → must verify against the specific token used
  if (tok === BRIDGE_TOKEN && validBridgeSig(sig, BRIDGE_TOKEN)) return true;
  if (BRIDGE_TOKEN_NEXT && tok === BRIDGE_TOKEN_NEXT && validBridgeSig(sig, BRIDGE_TOKEN_NEXT)) return true;
  return false;
}

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

function ensureDir(p: string) { try { fs.mkdirSync(p, { recursive: true }); } catch {} }
ensureDir(RF_SPOOL_DIR);
ensureDir(RN_SPOOL_DIR);

// ───────────────────────────────────────────────────────────────
// Config
const PORT = Number(process.env.PORT || 8787);
const CLOUD_BASE = (process.env.CLOUD_BASE || "").replace(/\/+$/, "");
const FORWARD_TO_CLOUD = !!CLOUD_BASE;

function requireBridgeToken(req: Request, res: Response, next: NextFunction) {
  const raw = req.header("x-bridge-token") || req.header("authorization") || "";
  const tok = raw.startsWith("Bearer ") ? raw.slice(7) : raw;
  const sig = req.header("x-bridge-sig") || ""; // optional
  if (!tokenOkWithOptionalSig(tok, sig)) {
    return res.status(401).json({ ok: false, error: "unauthorized" });
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
  const key = rxKey(topic, seq);
  seen.set(key, Date.now());
  // write a tiny marker file so we reload on boot
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

const PROFILE_FILE = process.env.BAND_PROFILE_FILE
  || path.join(__dirname, "band_profile.yml");

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
  // De-dupe if a seq is supplied
  if (typeof seq === "number") {
    const key = `${topic}#${seq}`;
    if (seen.has(key)) return;
    rememberRX(topic, seq);
  }

  // Discovery beacons: update neighbor table; do not fanout as messages
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

async function tryForward(item: TxItem) {
  if (!FORWARD_TO_CLOUD) return true;
  try {
    const r = await fetch(`${CLOUD_BASE}/api/glyphnet/tx`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(item.body),
    });
    cloudOk = r.ok;
    return r.ok;
  } catch {
    cloudOk = false;
    return false;
  }
}

setInterval(async () => {
  const t = now();
  for (const it of queue.slice()) {
    if (it.nextAt > t) continue;
    const ok = await tryForward(it);
    if (ok) queue.splice(queue.findIndex(q => q.id === it.id), 1);
    else {
      it.tries += 1;
      const backoff = Math.min(15000, Math.floor(Math.pow(1.8, it.tries) * 700));
      it.nextAt = now() + backoff + Math.floor(Math.random() * 400);
    }
  }
}, 750);

// ───────────────────────────────────────────────────────────────
// HTTP server
const app = express();

/** DEBUG: confirm this file is the one running */
console.log("[radio-node] registering /bridge/transports route");

// Optional: simple status endpoint for transports (force strict JSON)
app.get("/bridge/transports", (_req, res) => {
  try {
    const body = {
      ok: true,
      drivers: listDrivers(),        // [{ id, kind, up, ...stats }]
      rfOutbox: rfOutbox.length,     // queued frames waiting for a link
    };
    res.setHeader("Content-Type", "application/json; charset=utf-8");
    res.end(JSON.stringify(body));
  } catch (e: any) {
    res
      .status(500)
      .json({ ok: false, error: String(e?.message || e) });
  }
});

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

/* CORS (must be before routes & JSON parser) */
const corsMw = cors({
  origin: true, // reflect the request Origin
  credentials: true,
  methods: ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
  // ⬇ add Authorization so browser can send Bearer headers when needed
  allowedHeaders: ["Content-Type", "Authorization", "X-Agent-Token", "X-Agent-Id", "X-Bridge-Token"],
});
app.use(corsMw);
app.options("*", corsMw);

/* JSON body parser (after CORS is fine) */
app.use(express.json({ limit: "5mb" }));

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

// --- GHX container info (local stub) -----------------------------
// supports both /api/container/:id and /api/containers/:id
app.get(["/api/container/:id", "/api/containers/:id"], (req, res) => {
  const id = String(req.params.id || "").trim();
  if (!id) return res.status(400).json({ ok: false, error: "missing id" });

  res.json({
    ok: true,
    id,
    status: "local",
    createdAt: Date.now(),
    topic: `ucs://local/${id}`,
    graph: "personal",
    ws: `/ws/ghx?id=${encodeURIComponent(id)}`, // what the page will try to open
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
app.post("/bridge/tx", requireBridgeToken, (req: Request, res: Response) => {
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

// ───────────────────────────────────────────────────────────────
// HTTP server + explicit WS upgrade mux
const server = http.createServer(app);

(server as any).requestTimeout   = 0;  // no request timeout for upgrades
(server as any).headersTimeout   = 0;  // don't kill slow handshakes
(server as any).keepAliveTimeout = 0;  // keep-alive off for upgraded sockets

// --- GlyphNet WS (noServer; upgrade-routed) ---------------------
const wssGlyph = new WebSocketServer({ noServer: true, perMessageDeflate: false });

wssGlyph.on("connection", (ws: WebSocket, req: IncomingMessage) => {
  try {
    const url = new URL(req.url || "", URL_BASE);
    const topic = url.searchParams.get("topic") || "";
    const kg = (url.searchParams.get("kg") || "personal").toLowerCase();
    const key = topicKey(topic, kg);
    joinRoom(key, ws);

    // keep-alive
    const ping = setInterval(() => {
      try { (ws as any).isAlive = true; ws.ping(); } catch {}
    }, 15000);
    ws.on("pong", () => { (ws as any).isAlive = true; });

    ws.on("message", (data: Buffer) => {
      let payload: any;
      try { payload = JSON.parse(String(data)); } catch { payload = undefined; }

      const envelope = {
        capsule: payload?.capsule ?? payload ?? { glyphs: ["(echo)"] },
        meta: payload?.meta ?? { graph: kg },
        ts: now(),
        id: msgId(),
      };

      // 1) local WS fanout
      broadcast(key, { type: "glyphnet_capsule", envelope });

      // 2) RF bridge for WS-origin voice payloads — size-guarded
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

    ws.on("close", () => { clearInterval(ping); leaveAll(ws); });
    ws.on("error", () => { clearInterval(ping); leaveAll(ws); });
  } catch {
    try { ws.close(); } catch {}
  }
});



// --- RF Link Bridge WS (noServer; upgrade-routed) ----------------
const wssRF = new WebSocketServer({ noServer: true, perMessageDeflate: false });
let activeBridge: WebSocket | null = null;

function authTokenFromWS(req: IncomingMessage): string {
  const h = String(req.headers["authorization"] || "");
  const bearer = h.startsWith("Bearer ") ? h.slice(7) : "";
  if (bearer) return bearer;

  const xbt = String((req.headers["x-bridge-token"] || "").toString());
  if (xbt) return xbt;

  try {
    const url = new URL(req.url || "", URL_BASE);
    return url.searchParams.get("token") || "";
  } catch { return ""; }
}

function sigFromWS(req: IncomingMessage): string {
  const h = String(req.headers["x-bridge-sig"] || "");
  if (h) return h;
  try {
    const url = new URL(req.url || "", URL_BASE);
    return url.searchParams.get("sig") || "";
  } catch { return ""; }
}

// Register the WS bridge as a LinkDriver (one-time)
let wsBridgeDriverRegistered = false;
function ensureWSBridgeDriverRegistered() {
  if (wsBridgeDriverRegistered) return;
  registerDriver({
    id: "ws-bridge-1",
    kind: "ws-bridge",
    sendB64: (b64: string) => {
      if (!activeBridge || activeBridge.readyState !== WebSocket.OPEN) return false;
      try { activeBridge.send(JSON.stringify({ type: "tx", bytes_b64: b64 })); return true; }
      catch { return false; }
    },
    isUp: () => !!activeBridge && activeBridge.readyState === WebSocket.OPEN,
    stats: () => ({ rfOutbox: rfOutbox.length }),
  });
  wsBridgeDriverRegistered = true;
}

wssRF.on("connection", (ws, req) => {
  const token = authTokenFromWS(req);
  const sig = sigFromWS(req); // new: optional signed auth
  const ua = String(req.headers["user-agent"] || "unknown-UA");

  if (!tokenOkWithOptionalSig(token, sig)) {
    try { ws.close(1008, "unauthorized"); } catch {}
    return;
  }

  // Single-active-bridge policy
  if (activeBridge && activeBridge.readyState === WebSocket.OPEN) {
    try { ws.close(1013, "busy"); } catch {}
    return;
  }

  activeBridge = ws;
  ensureWSBridgeDriverRegistered();

  try { ws.send(JSON.stringify({ type: "hello", mtu: ACTIVE.MTU, rate_hz: ACTIVE.RATE_HZ })); } catch {}

  // Drain any queued frames immediately
  pushRFOutboxToBridge();

  // keepalive
  const ka = setInterval(() => { try { ws.ping(); } catch {} }, 20_000);

  ws.on("message", (data: Buffer) => {
    let msg: any;
    try { msg = JSON.parse(String(data)); } catch { return; }

    // Inbound RF from the bridge
    if (msg?.type === "rx" && typeof msg.topic === "string" && typeof msg.bytes_b64 === "string") {
      let bytes: Uint8Array;
      try { bytes = b64ToU8(msg.bytes_b64); } catch { return; }
      processInboundRF(
        msg.topic,
        bytes,
        typeof msg.seq === "number" ? msg.seq : undefined,
        ua
      );
      return;
    }

    // Bridge ping → pong
    if (msg?.type === "ping") {
      try { ws.send(JSON.stringify({ type: "pong", ts: now() })); } catch {}
    }
  });

  ws.on("close", () => { clearInterval(ka); if (activeBridge === ws) activeBridge = null; });
  ws.on("error", () => { clearInterval(ka); if (activeBridge === ws) activeBridge = null; });
});

// Helper to push outbox frames to the bridge
function pushRFOutboxToBridge() {
  // Now uses the pluggable driver registry (WS bridge is one driver)
  drainOutboxViaDrivers();
}

// --- GHX WS (noServer; upgrade-routed) --------------------------
const wssGHX = new WebSocketServer({ noServer: true, perMessageDeflate: false });

wssGHX.on("connection", (ws: WebSocket, req: IncomingMessage) => {
  const url = new URL(req.url || "", URL_BASE);
  const container = url.searchParams.get("id") || "unknown";

  const timer = setInterval(() => {
    try { ws.send(JSON.stringify({ type: "ghx/heartbeat", at: Date.now(), container })); } catch {}
  }, 15000);

  ws.on("close", () => clearInterval(timer));
  ws.on("error", () => clearInterval(timer));
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