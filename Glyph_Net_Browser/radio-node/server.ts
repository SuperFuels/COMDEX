// radio-node/server.ts
import express, { type Request, type Response, type NextFunction } from "express";
import http, { type IncomingMessage } from "http";
import cors from "cors";
import { WebSocketServer, WebSocket } from "ws";
import { Buffer } from "buffer";
import fs from "fs";
import path from "path";
import dotenv from "dotenv";

dotenv.config({ path: path.join(process.cwd(), ".env.local") });
dotenv.config(); // fallback to .env if present

// Optional YAML loader (fallback to defaults if not installed)
let YAML: any = null;
try { YAML = require("yaml"); } catch { /* optional */ }

// ───────────────────────────────────────────────────────────────
// Base64 → bytes
const b64ToU8 = (b64: string) => new Uint8Array(Buffer.from(b64, "base64"));

const BRIDGE_TOKEN = process.env.RADIO_BRIDGE_TOKEN || "dev-bridge";

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
  if (!BRIDGE_TOKEN) return res.status(501).json({ ok: false, error: "bridge token not configured" });
  const h = req.header("x-bridge-token") || req.header("authorization") || "";
  const token = h.startsWith("Bearer ") ? h.slice(7) : h;
  if (token !== BRIDGE_TOKEN) return res.status(401).json({ ok: false, error: "unauthorized" });
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

function startRFPacer() {
  if (rfTicker) { clearInterval(rfTicker); rfTicker = null; }
  const hz = Math.max(1, Math.floor(ACTIVE.RATE_HZ || 10));
  const intervalMs = Math.max(1, Math.round(1000 / hz));
  rfTicker = setInterval(() => {
    const frame = rfQueue.shift();
    if (frame) {
      // TODO: write to radio transport (UART/SPI/etc.)
      rfOutbox.push(frame);
    }
  }, intervalMs);
}

// ✅ call it once after ACTIVE is set up (not inside a handler)
startRFPacer();

// Enqueue with fragmentation to fit MTU (topic=graph:recipient)
function enqueueRF(rfTopic: string, payload: Uint8Array, codec?: string) {
  if (!payload?.length) return;
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
      ts: Date.now(),
      codec,
      bytes: slice,
    });
    rfQueue.push(frame);
  }
}

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

/* CORS (must be before routes & JSON parser) */
const corsMw = cors({
  origin: true, // reflect the request Origin
  credentials: true,
  methods: ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
  allowedHeaders: ["Content-Type", "X-Agent-Token", "X-Agent-Id", "X-Bridge-Token"],
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
    ts: now(),
    profile: PROFILE_NAME,
    active: ACTIVE,
    profiles: Object.keys(PROFILES),
    maxRfIngressBytes: MAX_RF_INGRESS_BYTES,
  });
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
    meta: { ...(body.meta || {}), graph: kg },
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
// HTTP server + explicit WS upgrade mux
const server = http.createServer(app);

(server as any).requestTimeout = 0;     // no request timeout for upgrades
(server as any).headersTimeout = 0;     // don't kill slow handshakes
(server as any).keepAliveTimeout = 0;   // keep-alive off for upgraded sockets

// --- GlyphNet WS (noServer; upgrade-routed) ---------------------
const wssGlyph = new WebSocketServer({ noServer: true });

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
// --- RF Link Bridge WS (path-bound) --------------------------------
const wssRF = new WebSocketServer({ noServer: true, perMessageDeflate: false });
let activeBridge: WebSocket | null = null;

function authTokenFromWS(req: IncomingMessage): string {
  const h = String(req.headers["authorization"] || "");
  const bearer = h.startsWith("Bearer ") ? h.slice(7) : "";
  if (bearer) return bearer;
  try {
    const url = new URL(req.url || "", "http://localhost");
    return url.searchParams.get("token") || "";
  } catch { return ""; }
}

wssRF.on("connection", (ws, req) => {
  const token = authTokenFromWS(req);
  const ua = String(req.headers["user-agent"] || "unknown-UA");

  if (token !== BRIDGE_TOKEN) {
    console.log("[rf-link] unauthorized connect from UA:", ua);
    try { ws.close(1008, "unauthorized"); } catch {}
    return;
  }

  // If a bridge is already up, refuse the newcomer (don't kill the current one)
  if (activeBridge && activeBridge.readyState === WebSocket.OPEN) {
    const ua = String(req.headers["user-agent"] || "unknown-UA");
    console.log("[rf-link] new connection refused (busy). UA:", ua);
    try { ws.close(1013, "busy"); } catch {}
    return;
  }

  activeBridge = ws;
  console.log("[rf-link] bridge connected. UA:", ua);
  try { ws.send(JSON.stringify({ type: "hello", mtu: ACTIVE.MTU, rate_hz: ACTIVE.RATE_HZ })); } catch {}

  // Drain queued frames
  pushRFOutboxToBridge();

  // Optional keepalive
 // No keepalive for now (wscat can be finicky behind some proxies).
// Add deep socket visibility instead.
  const sock = (ws as any)._socket;
  if (sock) {
    sock.on("end",   () => console.log("[rf-link] tcp end"));
    sock.on("close", () => console.log("[rf-link] tcp close (underlying)"));
    sock.on("error", (e: any) => console.log("[rf-link] tcp error:", e?.message || e));
    sock.on("timeout", () => console.log("[rf-link] tcp timeout"));
  }

  ws.on("message", (data) => {
    let msg: any;
    try { msg = JSON.parse(String(data)); } catch { return; }

    if (msg?.type === "rx" && typeof msg.topic === "string" && typeof msg.bytes_b64 === "string") {
      // optional de-dupe if you provide seq from device
      if (typeof msg.seq === "number") {
        const key = `${msg.topic}#${msg.seq}`;
        if (seen.has(key)) return;
        rememberRX(msg.topic, msg.seq);
      }
      let bytes: Uint8Array;
      try { bytes = b64ToU8(msg.bytes_b64); } catch { return; }
      const keyTopic = msg.topic; // "graph:recipient"
      const envelope = {
        capsule: { glyphs: ["(rf)"], rf_bytes_len: bytes.length },
        meta: { graph: keyTopic.split(":")[0] || "personal" },
        ts: now(),
        id: msgId(),
      };
      broadcast(keyTopic, { type: "glyphnet_capsule", envelope });
      return;
    }

    if (msg?.type === "ping") {
      try { ws.send(JSON.stringify({ type: "pong", ts: now() })); } catch {}
    }
  });

  ws.on("close", (code, reason) => {
    if (activeBridge === ws) activeBridge = null;
    console.log("[rf-link] bridge disconnected", code, String(reason || ""));
  });

  ws.on("error", (err) => {
    if (activeBridge === ws) activeBridge = null;
    console.warn("[rf-link] bridge error:", err?.message || err);
  });
});

// Helper to push outbox frames to the bridge (unchanged)
function pushRFOutboxToBridge() {
  if (!activeBridge || activeBridge.readyState !== WebSocket.OPEN) return;
  while (rfOutbox.length) {
    const frame = rfOutbox.shift()!;
    try {
      activeBridge.send(JSON.stringify({ type: "tx", bytes_b64: Buffer.from(frame).toString("base64") }));
    } catch {
      rfOutbox.unshift(frame);
      break;
    }
  }
}

// Replace the old RF ticker with one that also nudges the bridge
const _oldTicker = rfTicker;
if (_oldTicker) clearInterval(_oldTicker);
{
  const hz = Math.max(1, Math.floor(ACTIVE.RATE_HZ || 10));
  const intervalMs = Math.max(1, Math.round(1000 / hz));
  rfTicker = setInterval(() => {
    const frame = rfQueue.shift();
    if (frame) rfOutbox.push(frame);
    pushRFOutboxToBridge();
  }, intervalMs);
}

// --- GHX WS (noServer; upgrade-routed) --------------------------
const wssGHX = new WebSocketServer({ noServer: true });

wssGHX.on("connection", (ws: WebSocket, req: IncomingMessage) => {
  const url = new URL(req.url || "", URL_BASE);
  const container = url.searchParams.get("id") || "unknown";

  // simple heartbeat so UI shows connected
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

server.listen(PORT, () => {
  console.log(
    `[radio-node] up on http://127.0.0.1:${PORT}  (cloud=${CLOUD_BASE || "disabled"})  ` +
    `profile=${PROFILE_NAME} mtu=${ACTIVE.MTU} rate=${ACTIVE.RATE_HZ}Hz`
  );
});