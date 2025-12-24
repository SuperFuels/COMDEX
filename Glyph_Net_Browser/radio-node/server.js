// radio-node/server.ts
import express from "express";
import http from "http";
import cors from "cors";
import { WebSocketServer, WebSocket } from "ws";
import { Buffer } from "buffer";
import fs from "fs";
import path from "path";
import dotenv from "dotenv";
import crypto from "crypto";
import { fileURLToPath } from "url";
dotenv.config({ path: path.join(process.cwd(), ".env.local") });
dotenv.config(); // fallback to .env if present
// Optional YAML loader (fallback to defaults if not installed)
let YAML = null;
try {
    YAML = require("yaml");
}
catch { /* optional */ }
// ───────────────────────────────────────────────────────────────
// Base64 → bytes
const b64ToU8 = (b64) => new Uint8Array(Buffer.from(b64, "base64"));
const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
// String <-> bytes helpers
const u8ToStr = (u8) => new TextDecoder().decode(u8);
const strToU8 = (s) => new TextEncoder().encode(s);
// Unique node id (used by discovery beacons)
const NODE_ID = process.env.NODE_ID || `rn-${Math.random().toString(36).slice(2, 8)}`;
const NEIGHBOR_TTL_MS = Number(process.env.NEIGHBOR_TTL_MS ?? 60_000);
const neighbors = new Map();
function upsertNeighbor(n) {
    const prev = neighbors.get(n.id) || {};
    neighbors.set(n.id, { ...prev, ...n, seenAt: now() });
}
function currentNeighbors() {
    const out = [];
    const t = now();
    for (const [, n] of neighbors) {
        if (t - n.seenAt <= NEIGHBOR_TTL_MS)
            out.push(n);
        else
            neighbors.delete(n.id);
    }
    out.sort((a, b) => b.seenAt - a.seenAt);
    return out;
}
// Optional rolling token for rotation
const BRIDGE_TOKEN = process.env.RADIO_BRIDGE_TOKEN || "dev-bridge";
const BRIDGE_TOKEN_NEXT = process.env.RADIO_BRIDGE_TOKEN_NEXT || "";
// Toggle: require signed auth (token + X-Bridge-Sig) on HTTP endpoints
const REQUIRE_BRIDGE_SIG = String(process.env.REQUIRE_BRIDGE_SIG || "").toLowerCase() === "true";
// --- Serial Link (optional) -------------------------------------
// ---- Serial Link (optional, with auto-reconnect) ---------------
const RF_SERIAL_DEV = process.env.RF_SERIAL_DEV || "";
const RF_SERIAL_BAUD = Number(process.env.RF_SERIAL_BAUD || 115200);
// --- Serial Link (optional) -------------------------------------
let serialDriverRegistered = false;
const serialState = { port: null, rl: null, up: false, reconnectTimer: null };
// Stable driver id (sanitize path so it’s safe to print)
const serialDriverId = `serial:${RF_SERIAL_DEV.replace(/[^\w.-]/g, "_")}`;
function onSerialLine(line) {
    const s = (line || "").trim();
    if (!s)
        return;
    let topic = "personal:ucs://local/ucs_hub";
    let b64 = s;
    if (s.startsWith("{")) {
        try {
            const j = JSON.parse(s);
            if (typeof j.topic === "string")
                topic = j.topic;
            if (typeof j.bytes_b64 === "string")
                b64 = j.bytes_b64;
            else if (typeof j.data_b64 === "string")
                b64 = j.data_b64;
        }
        catch {
            // fall back to plain Base64
        }
    }
    if (!b64)
        return;
    try {
        const bytes = b64ToU8(b64);
        processInboundRF(topic, bytes, undefined, `serial:${RF_SERIAL_DEV}`);
    }
    catch (e) {
        console.warn("[rf][serial] bad inbound line:", e?.message || e);
    }
}
async function tryOpenSerial() {
    if (!RF_SERIAL_DEV)
        return;
    // If the device path doesn't exist yet, trigger backoff instead of crashing
    if (!fs.existsSync(RF_SERIAL_DEV)) {
        throw new Error(`${RF_SERIAL_DEV} not present`);
    }
    // ESM-safe lazy imports
    const spMod = await import("serialport");
    const rlMod = await import("node:readline");
    const SerialPort = spMod?.SerialPort ??
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
    const scheduleReconnect = (why, backoff = 1000) => {
        if (serialState.reconnectTimer) {
            clearTimeout(serialState.reconnectTimer);
            serialState.reconnectTimer = null;
        }
        try {
            serialState.rl?.removeAllListeners?.();
            serialState.rl?.close?.();
        }
        catch { }
        try {
            port.removeAllListeners?.();
            port.close?.();
        }
        catch { }
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
        try {
            drainOutboxViaDrivers();
        }
        catch { }
        // Create line reader only once the port is open
        const rl = rlMod.createInterface({ input: port });
        serialState.rl = rl;
        rl.on("line", onSerialLine);
    });
    port.on("error", (err) => scheduleReconnect(`error: ${err?.message || err}`));
    port.on("close", () => scheduleReconnect("closed"));
    port.open((err) => {
        if (err)
            scheduleReconnect(`open failed: ${err?.message || err}`);
    });
}
function connectSerial(initialDelay = 0) {
    if (!RF_SERIAL_DEV)
        return;
    if (serialState.reconnectTimer) {
        clearTimeout(serialState.reconnectTimer);
        serialState.reconnectTimer = null;
    }
    const attempt = async (delay) => {
        try {
            await tryOpenSerial();
        }
        catch (err) {
            const msg = err?.message || String(err);
            const next = Math.min(delay ? delay * 2 : 2000, 15_000);
            console.warn(`[rf][serial] init failed: ${msg}; retrying in ${next}ms`);
            serialState.reconnectTimer = setTimeout(() => attempt(next), next);
        }
    };
    if (initialDelay > 0) {
        serialState.reconnectTimer = setTimeout(() => attempt(initialDelay), initialDelay);
    }
    else {
        attempt(0);
    }
}
function ensureSerialDriverRegistered() {
    if (serialDriverRegistered || !RF_SERIAL_DEV)
        return;
    // Register driver once; connection state is managed by connectSerial()
    registerDriver({
        id: serialDriverId,
        kind: "serial",
        sendB64: (b64) => {
            const p = serialState.port;
            if (!p || !serialState.up)
                return false;
            try {
                p.write(b64 + "\n");
                return true;
            }
            catch {
                return false;
            }
        },
        isUp: () => !!serialState.up,
        stats: () => ({ rfOutbox: rfOutbox.length }),
    });
    serialDriverRegistered = true;
    connectSerial(0);
}
/** Validate X-Bridge-Sig: "v1,<tsMs>,<hmacHex>" where hmac = HMAC_SHA256(token, `ws-bridge|${tsMs}`) */
function validBridgeSig(sig, token) {
    try {
        const [v, tsStr, macHex] = String(sig).split(",");
        if (v !== "v1")
            return false;
        const ts = Number(tsStr);
        if (!Number.isFinite(ts))
            return false;
        if (Math.abs(Date.now() - ts) > BRIDGE_SIG_TOLERANCE_MS)
            return false; // uses your existing TOLERANCE var
        const want = crypto.createHmac("sha256", token).update(`ws-bridge|${ts}`).digest("hex");
        return secureEq(want, macHex);
    }
    catch {
        return false;
    }
}
function tokenMatchesAny(tok) {
    return !!tok && (secureEq(tok, BRIDGE_TOKEN) || (!!BRIDGE_TOKEN_NEXT && secureEq(tok, BRIDGE_TOKEN_NEXT)));
}
/** Validate token; if a signature is present it MUST verify against that specific token.
 *  If no signature is provided, allow plain token (dev/back-compat).
 *  Strict/lenient behavior is enforced by requireBridgeAuth via REQUIRE_BRIDGE_SIG.
 */
function tokenOkWithOptionalSig(tok, sig) {
    if (!tok)
        return false;
    if (sig) {
        return (secureEq(tok, BRIDGE_TOKEN) && validBridgeSig(sig, BRIDGE_TOKEN)) ||
            (!!BRIDGE_TOKEN_NEXT && secureEq(tok, BRIDGE_TOKEN_NEXT) && validBridgeSig(sig, BRIDGE_TOKEN_NEXT));
    }
    // No signature → plain token ok
    return tokenMatchesAny(tok);
}
// Pull token/signature from HTTP headers
function tokenFromReq(req) {
    const auth = String(req.header("authorization") || "");
    const bearer = auth.startsWith("Bearer ") ? auth.slice(7) : "";
    const xbt = String(req.header("x-bridge-token") || "");
    return bearer || xbt;
}
function sigFromReq(req) {
    return String(req.header("x-bridge-sig") || "");
}
// Constant-time compare helpers
function secureEq(a, b) {
    const A = Buffer.from(a, "utf8");
    const B = Buffer.from(b, "utf8");
    if (A.length !== B.length)
        return false;
    try {
        return crypto.timingSafeEqual(A, B);
    }
    catch {
        return false;
    }
}
function secureEqHex(aHex, bHex) {
    try {
        const A = Buffer.from(aHex, "hex");
        const B = Buffer.from(bHex, "hex");
        if (A.length !== B.length)
            return false;
        return crypto.timingSafeEqual(A, B);
    }
    catch {
        return false;
    }
}
// --- Session ticket HMAC (optional, dev works without) ----------------
function verifySessionTicket(wa, slug, ticket) {
    try {
        const secret = process.env.SESSION_HMAC_SECRET || "";
        if (!secret)
            return true; // dev mode: accept without ticket
        const [v, tsStr, macHex] = String(ticket || "").split(",");
        if (v !== "v1")
            return false;
        const ts = Number(tsStr);
        if (!Number.isFinite(ts) || Math.abs(Date.now() - ts) > 5 * 60_000)
            return false; // 5 min
        const want = crypto.createHmac("sha256", secret).update(`${ts}|${wa}|${slug}`).digest("hex");
        return secureEq(want, macHex);
    }
    catch {
        return false;
    }
}
const BRIDGE_SIG_TOLERANCE_MS = Number(process.env.RADIO_BRIDGE_SIG_TOLERANCE_MS ?? 2 * 60_000);
// ───────────────────────────────────────────────────────────────
// Spool configuration (two independent spools)
// (A) RF spool (for on-air path; opportunistic relay)
const RF_SPOOL_DIR = process.env.RF_SPOOL_DIR || path.join(process.cwd(), ".rf_spool");
const RF_SPOOL_TTL_SEC = Number(process.env.RF_SPOOL_TTL_SEC ?? 3 * 24 * 3600); // 3 days
const RF_SPOOL_MAX_BYTES = Number(process.env.RF_SPOOL_MAX_BYTES ?? 32 * 1024 * 1024); // 32 MB
// (B) Cloud-forward disk queue (store–carry–forward to CLOUD_BASE)
const RN_SPOOL_DIR = process.env.RN_SPOOL_DIR || path.join(process.cwd(), ".radio-spool");
const RN_QUEUE_MAX_ITEMS = Number(process.env.RN_QUEUE_MAX_ITEMS ?? 2000);
const RN_QUEUE_MAX_BYTES = Number(process.env.RN_QUEUE_MAX_BYTES ?? 100 * 1024 * 1024); // 100 MB
const RN_QUEUE_TTL_MS = Number(process.env.RN_QUEUE_TTL_MS ?? 7 * 24 * 3600 * 1000); // 7 days
// Auto-disable mock when a real link (serial/ws-bridge) comes up
const AUTO_DISABLE_MOCK_ON_REAL_LINK = String(process.env.AUTO_DISABLE_MOCK_ON_REAL_LINK ?? "1") === "1";
function ensureDir(p) { try {
    fs.mkdirSync(p, { recursive: true });
}
catch { } }
ensureDir(RF_SPOOL_DIR);
ensureDir(RN_SPOOL_DIR);
// ── Containers bootstrap (paths + helpers + static mapping)
// Files will be created under: radio-node/public/containers/<user>/...
const CONTAINERS_ROOT = path.join(process.cwd(), "public", "containers");
ensureDir(CONTAINERS_ROOT);
function writeJson(filePath, obj) {
    fs.writeFileSync(filePath, JSON.stringify(obj, null, 2) + "\n", "utf8");
}
function slugFromWa(wa) {
    const name = String(wa).split("@")[0] || wa;
    return name.toLowerCase().replace(/[^a-z0-9._-]/g, "-");
}
function homeTemplate(wa, user) {
    return {
        id: `${user}__home`,
        type: "container",
        meta: { title: `${user} — HQ`, ownerWA: wa, graph: "personal" },
        glyphs: [],
        dimensions: []
    };
}
function kgTemplate(wa, user, graph) {
    return {
        id: `${user}__kg_${graph}`,
        type: "container",
        meta: { title: `KG • ${user} (${graph})`, ownerWA: wa, graph, kind: "kg" },
        glyphs: [],
        dimensions: []
    };
}
// --- Containers: static + ID→file mapping (ORDER MATTERS) -----
export function registerContainerStaticRoutes(app) {
    const root = CONTAINERS_ROOT;
    // 1) ID → file mapping FIRST
    app.get(["/containers/:id.json", "/containers/:id/manifest.json"], (req, res) => {
        const id = String(req.params.id || "");
        const tries = [];
        // direct file: /containers/<id>.json
        tries.push(path.join(root, `${id}.json`));
        // split form "<user>__home|kg_personal|kg_work"
        if (id.includes("__")) {
            const [user, rest] = id.split("__");
            const fname = rest === "home" ? "home.json" :
                rest === "kg_personal" ? "kg_personal.json" :
                    rest === "kg_work" ? "kg_work.json" : "";
            if (fname)
                tries.push(path.join(root, user, fname));
        }
        for (const p of tries) {
            if (fs.existsSync(p)) {
                res.setHeader("Content-Type", "application/json; charset=utf-8");
                return res.send(fs.readFileSync(p, "utf8"));
            }
        }
        return res.status(404).json({ ok: false, error: "container manifest not found", id, tried: tries });
    });
    // 2) Raw static AFTER (so folder paths like /containers/kevin/home.json work)
    app.use("/containers", express.static(root, {
        index: false,
        fallthrough: true,
        setHeaders: (res, servedPath) => {
            if (String(servedPath).endsWith(".json")) {
                res.setHeader("Content-Type", "application/json; charset=utf-8");
            }
        },
    }));
}
// ───────────────────────────────────────────────────────────────
// Config
const PORT = Number(process.env.PORT || 8787);
const CLOUD_BASE = (process.env.CLOUD_BASE || "").replace(/\/+$/, "");
const FORWARD_TO_CLOUD = !!CLOUD_BASE;
function requireBridgeAuth(req, res, next) {
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
    }
    else {
        // Dev-friendly: accept either plain token or signed token
        if (sig) {
            if (!tokenOkWithOptionalSig(tok, sig)) {
                return res.status(401).json({ ok: false, error: "unauthorized" });
            }
        }
        else if (!tokenMatchesAny(tok)) {
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
const seen = new Map(); // key: `${topic}#${seq}` => ts
function rxKey(topic, seq) { return `${topic}#${seq}`; }
function rememberRX(topic, seq) {
    // ⛔ do not persist control:* (e.g., control:beacon) — avoids file explosion
    if (String(topic).startsWith("control:"))
        return;
    const key = rxKey(topic, seq);
    seen.set(key, Date.now());
    try {
        fs.writeFileSync(path.join(RF_RX_DIR, `${encodeURIComponent(key)}.json`), JSON.stringify({ topic, seq, ts: Date.now() }));
    }
    catch { }
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
                    try {
                        fs.unlinkSync(p);
                    }
                    catch { }
                    continue;
                }
                seen.set(rxKey(j.topic, j.seq), j.ts || now);
            }
            catch { }
        }
    }
    catch { }
}
loadSeenRX();
function haveSeen(topic, seq) {
    const key = rxKey(topic, seq);
    return seen.has(key);
}
const queue = [];
let queueBytes = 0;
let cloudOk = !FORWARD_TO_CLOUD; // ok=true when cloud forwarding is disabled
function sizeOf(obj) {
    try {
        return Buffer.byteLength(JSON.stringify(obj));
    }
    catch {
        return 0;
    }
}
function spoolPath(id) { return path.join(RN_SPOOL_DIR, `${id}.json`); }
function persistItem(it) {
    try {
        fs.writeFileSync(spoolPath(it.id), JSON.stringify(it));
    }
    catch { }
}
function removeItem(id) {
    try {
        fs.unlinkSync(spoolPath(id));
    }
    catch { }
}
/** Keep both item count and total bytes within RN_* caps (drop oldest first). */
function enforceSpoolCaps() {
    // Oldest first
    queue.sort((a, b) => (a.createdAt || 0) - (b.createdAt || 0));
    const overItems = () => RN_QUEUE_MAX_ITEMS > 0 && queue.length > RN_QUEUE_MAX_ITEMS;
    const overBytes = () => RN_QUEUE_MAX_BYTES > 0 && queueBytes > RN_QUEUE_MAX_BYTES;
    while ((overItems() || overBytes()) && queue.length) {
        const victim = queue.shift();
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
        const victim = queue.shift();
        queueBytes -= victim.size || sizeOf(victim.body);
        removeItem(victim.id);
    }
    // Item cap
    while (queue.length > RN_QUEUE_MAX_ITEMS) {
        const victim = queue.shift();
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
            let it = null;
            try {
                it = JSON.parse(fs.readFileSync(p, "utf8"));
            }
            catch {
                it = null;
            }
            if (!it?.id || !it?.body) {
                try {
                    fs.unlinkSync(p);
                }
                catch { }
                ;
                continue;
            }
            if (RN_QUEUE_TTL_MS && now - (it.createdAt || 0) > RN_QUEUE_TTL_MS) {
                try {
                    fs.unlinkSync(p);
                }
                catch { }
                ;
                continue;
            }
            if (queue.find(q => q.id === it.id)) {
                try {
                    fs.unlinkSync(p);
                }
                catch { }
                ;
                continue;
            }
            queue.push(it);
            queueBytes += it.size || sizeOf(it.body);
        }
        enforceQueueCaps();
        if (queue.length) {
            console.log(`[radio-node] loaded ${queue.length} queued cloud forwards (${queueBytes}B)`);
        }
    }
    catch (e) {
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
function topicKey(topic, kg) { return `${(kg || "personal").toLowerCase()}:${topic}`; }
const DEFAULT_PROFILES = {
    "NA-915": { MTU: 180, RATE_HZ: 10 },
    "EU-868": { MTU: 51, RATE_HZ: 6 },
    "ISM-2.4": { MTU: 200, RATE_HZ: 20 },
};
const PROFILE_FILE = process.env.BAND_PROFILE_FILE || path.join(__dirname, "band_profile.yml");
function loadProfiles() {
    try {
        const txt = fs.readFileSync(PROFILE_FILE, "utf8");
        if (!YAML)
            return DEFAULT_PROFILES; // yaml lib not present
        const parsed = YAML.parse(txt);
        // Expect top-level map: { PROFILE: { MTU, RATE_HZ }, ... }
        const out = {};
        for (const [k, v] of Object.entries(parsed || {})) {
            const p = v;
            const MTU = Number(p?.MTU);
            const RATE_HZ = Number(p?.RATE_HZ);
            if (Number.isFinite(MTU) && Number.isFinite(RATE_HZ))
                out[k] = { MTU, RATE_HZ };
        }
        return Object.keys(out).length ? out : DEFAULT_PROFILES;
    }
    catch {
        return DEFAULT_PROFILES;
    }
}
const PROFILES = loadProfiles();
const PROFILE_NAME = process.env.BAND_PROFILE || "NA-915";
let ACTIVE = PROFILES[PROFILE_NAME] || DEFAULT_PROFILES["NA-915"];
const seqByTopic = new Map();
function nextSeq(topic) {
    const n = (seqByTopic.get(topic) ?? 0) + 1;
    seqByTopic.set(topic, n);
    return n;
}
// [ver u8][seq u32][ts u64][codecLen u8][codec..][topicLen u8][topic..][payload..]
function encodeFrame(f) {
    const te = new TextEncoder();
    const codecBytes = te.encode(f.codec ?? "");
    const topicBytes = te.encode(f.topic);
    const headerLen = 1 + 4 + 8 + 1 + codecBytes.length + 1 + topicBytes.length;
    const out = new Uint8Array(headerLen + f.bytes.length);
    const dv = new DataView(out.buffer);
    let o = 0;
    out[o++] = 1; // ver
    dv.setUint32(o, f.seq >>> 0, false);
    o += 4;
    const hi = Math.floor(f.ts / 2 ** 32);
    const lo = f.ts >>> 0;
    dv.setUint32(o, hi >>> 0, false);
    o += 4;
    dv.setUint32(o, lo >>> 0, false);
    o += 4;
    out[o++] = codecBytes.length & 0xff;
    out.set(codecBytes, o);
    o += codecBytes.length;
    out[o++] = topicBytes.length & 0xff;
    out.set(topicBytes, o);
    o += topicBytes.length;
    out.set(f.bytes, o);
    return out;
}
function headerOverheadBytes(topic, codec) {
    // length with empty payload
    return encodeFrame({ topic, seq: 0, ts: 0, codec, bytes: new Uint8Array(0) }).length;
}
function maxPayloadBytes(topic, codec) {
    return Math.max(0, ACTIVE.MTU - headerOverheadBytes(topic, codec));
}
// ───────────────────────────────────────────────────────────────
// RF pacing queue (enforce RATE_HZ)
const rfOutbox = [];
const rfQueue = [];
let rfTicker = null;
const drivers = [];
function registerDriver(d) {
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
const mockCfg = {
    enabled: false,
    loopback: false,
    delay_ms: 0,
    jitter_ms: 0,
    loss_pct: 0,
};
// Decode RF frame that was produced by encodeFrame()
function decodeFrame(u8) {
    try {
        const dv = new DataView(u8.buffer, u8.byteOffset, u8.byteLength);
        let o = 0;
        const ver = dv.getUint8(o);
        o += 1;
        const seq = dv.getUint32(o, false);
        o += 4;
        const hi = dv.getUint32(o, false);
        o += 4;
        const lo = dv.getUint32(o, false);
        o += 4;
        const ts = (hi * 2 ** 32) + lo;
        const codecLen = dv.getUint8(o);
        o += 1;
        const codec = new TextDecoder().decode(u8.subarray(o, o + codecLen));
        o += codecLen;
        const topicLen = dv.getUint8(o);
        o += 1;
        const topic = new TextDecoder().decode(u8.subarray(o, o + topicLen));
        o += topicLen;
        const payload = u8.subarray(o);
        return { ver, seq, ts, codec, topic, payload };
    }
    catch {
        return null;
    }
}
/** Reusable inbound RF processor (used by WS bridge, mock driver, and dev injector). */
function processInboundRF(topic, bytes, seq, ua) {
    // De-dupe if a seq is supplied (but skip control:* from persistence)
    if (typeof seq === "number" && !String(topic).startsWith("control:")) {
        const key = `${topic}#${seq}`;
        if (seen.has(key))
            return;
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
        }
        catch { }
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
    if (mockDriverRegistered)
        return;
    registerDriver({
        id: "mock-1",
        kind: "mock",
        // Claim frames only when enabled; optionally loop them back after delay/jitter/loss.
        sendB64: (b64) => {
            if (!mockCfg.enabled)
                return false;
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
                    const base = Math.max(0, mockCfg.delay_ms | 0);
                    const jit = Math.max(0, mockCfg.jitter_ms | 0);
                    const delta = base + (jit ? Math.floor((Math.random() * 2 - 1) * jit) : 0);
                    setTimeout(() => {
                        try {
                            processInboundRF(dec.topic, dec.payload, dec.seq, "mock-loopback");
                        }
                        catch { }
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
    if (!drivers.length)
        return;
    while (rfOutbox.length) {
        const frame = rfOutbox.shift();
        const b64 = Buffer.from(frame).toString("base64");
        let delivered = false;
        for (const d of drivers) {
            try {
                delivered = d.sendB64(b64) || delivered;
            }
            catch { }
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
    if (frame)
        rfOutbox.push(frame);
    pushRFOutboxToBridge();
}
// Enqueue with fragmentation to fit MTU (topic=graph:recipient)
function enqueueRF(rfTopic, payload, codec) {
    if (!payload || payload.length === 0)
        return;
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
    try {
        kickRFStep();
    }
    catch { /* fallback if helper not present */
        try {
            pushRFOutboxToBridge();
        }
        catch { }
    }
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
    }
    catch { }
}, BEACON_INTERVAL_MS);
// ───────────────────────────────────────────────────────────────
// WS room registry
const rooms = new Map();
function joinRoom(key, ws) {
    let set = rooms.get(key);
    if (!set) {
        set = new Set();
        rooms.set(key, set);
    }
    set.add(ws);
}
function leaveAll(ws) { for (const [, set] of rooms)
    set.delete(ws); }
function broadcast(key, obj) {
    const set = rooms.get(key);
    if (!set || set.size === 0)
        return;
    const data = JSON.stringify(obj);
    for (const ws of set)
        if (ws.readyState === WebSocket.OPEN) {
            try {
                ws.send(data);
            }
            catch { }
        }
}
// ───────────────────────────────────────────────────────────────
// Cloud forward queue (store-carry-forward)
async function tryForward(item) {
    if (!FORWARD_TO_CLOUD)
        return true;
    try {
        const r = await fetch(`${CLOUD_BASE}/api/glyphnet/tx`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(item.body),
        });
        cloudOk = r.ok;
        return r.ok;
    }
    catch {
        cloudOk = false;
        return false;
    }
}
setInterval(async () => {
    const t = now();
    for (const it of queue.slice()) {
        if (it.nextAt > t)
            continue;
        const ok = await tryForward(it);
        if (ok)
            queue.splice(queue.findIndex(q => q.id === it.id), 1);
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
registerContainerStaticRoutes(app);
/** DEBUG: confirm this file is the one running */
console.log("[radio-node] registering /bridge/transports route");
// Optional: simple status endpoint for transports (force strict JSON)
app.get("/bridge/transports", (_req, res) => {
    try {
        const body = {
            ok: true,
            drivers: listDrivers(), // [{ id, kind, up, ...stats }]
            rfOutbox: rfOutbox.length, // queued frames waiting for a link
        };
        res.setHeader("Content-Type", "application/json; charset=utf-8");
        res.end(JSON.stringify(body));
    }
    catch (e) {
        res
            .status(500)
            .json({ ok: false, error: String(e?.message || e) });
    }
});
app.get("/__routes", (_req, res) => {
    const stack = app._router?.stack || [];
    const routes = stack
        .filter((l) => l.route && l.route.path)
        .map((l) => ({
        method: Object.keys(l.route.methods || {})[0]?.toUpperCase() || "GET",
        path: l.route.path,
    }));
    res.json({ ok: true, routes });
});
/* CORS (must be before routes & JSON parser) */
// replace your existing corsMw with this
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
        "X-Bridge-Sig", // ⬅ add this
    ],
});
app.use(corsMw);
app.options("*", corsMw);
/* JSON body parser (after CORS is fine) */
app.use(express.json({ limit: "5mb" }));
/* (optional) CSP helper; keep if you want */
app.use((_, res, next) => {
    res.setHeader("Content-Security-Policy", "default-src 'self'; connect-src * blob: data: ws: wss: http: https:");
    next();
});
// ───────────────────────────────────────────────────────────────
// Dev endpoints (all under /dev/rf/mock)
app.get("/dev/rf/mock/status", (_req, res) => {
    res.json({ ok: true, enabled: mockCfg.enabled, config: mockCfg, drivers: listDrivers(), rfOutbox: rfOutbox.length });
});
app.post("/dev/rf/mock/enable", (req, res) => {
    mockCfg.enabled = true;
    if (typeof req.body?.loopback === "boolean")
        mockCfg.loopback = !!req.body.loopback;
    if (Number.isFinite(req.body?.delay_ms))
        mockCfg.delay_ms = Math.max(0, Number(req.body.delay_ms));
    if (Number.isFinite(req.body?.jitter_ms))
        mockCfg.jitter_ms = Math.max(0, Number(req.body.jitter_ms));
    if (Number.isFinite(req.body?.loss_pct))
        mockCfg.loss_pct = Math.min(100, Math.max(0, Number(req.body.loss_pct)));
    res.json({ ok: true, config: mockCfg });
});
app.post("/dev/rf/mock/disable", (_req, res) => {
    mockCfg.enabled = false;
    res.json({ ok: true, config: mockCfg });
});
/** Inject a synthetic inbound RF frame (pretend we received it over the air). */
app.post("/dev/rf/mock/rx", (req, res) => {
    const topic = String(req.body?.topic || "").trim(); // "graph:recipient" or "control:beacon"
    const b64 = String(req.body?.data_b64 || req.body?.bytes_b64 || req.body?.b64 || "");
    const seq = Number.isFinite(req.body?.seq) ? Number(req.body.seq) : undefined;
    if (!topic || !b64)
        return res.status(400).json({ ok: false, error: "missing topic or data_b64" });
    let bytes;
    try {
        bytes = new Uint8Array(Buffer.from(b64, "base64"));
    }
    catch {
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
    if (!id)
        return res.status(400).json({ ok: false, error: "missing id" });
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
app.post("/api/glyphnet/tx", async (req, res) => {
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
    const maybeRF = (mime, b64) => {
        try {
            const bytes = b64ToU8(b64);
            if (bytes.length <= MAX_RF_INGRESS_BYTES)
                enqueueRF(key, bytes, mime);
        }
        catch { }
    };
    if (cap?.voice_frame?.data_b64)
        maybeRF(cap.voice_frame.mime, cap.voice_frame.data_b64);
    if (cap?.voice_note?.data_b64)
        maybeRF(cap.voice_note.mime, cap.voice_note.data_b64);
    // 3) Optional cloud forward: try once, else queue
    let forwarded = false, queued = false;
    if (FORWARD_TO_CLOUD) {
        const item = {
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
app.get("/bridge/health", (_req, res) => {
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
app.post("/bridge/tx", requireBridgeAuth, (req, res) => {
    const topic = String(req.body?.topic || "").trim();
    const kg = String(req.body?.graph || "personal").toLowerCase();
    const codec = req.body?.codec ? String(req.body.codec) : undefined;
    const b64 = String(req.body?.data_b64 || req.body?.bytes_b64 || req.body?.b64 || "");
    if (!topic || !b64)
        return res.status(400).json({ ok: false, error: "missing topic or data_b64" });
    let bytes;
    try {
        bytes = b64ToU8(b64);
    }
    catch {
        return res.status(400).json({ ok: false, error: "invalid base64" });
    }
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
            const r = await fetch(`${QKD_AGENT}/qkd/health`, { signal: ctrl.signal });
            clearTimeout(timer);
            const text = await r.text();
            res
                .status(r.status)
                .type(r.headers.get("content-type") || "application/json")
                .send(text);
        }
        catch (e) {
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
                signal: ctrl.signal,
            });
            clearTimeout(timer);
            const text = await r.text();
            res
                .status(r.status)
                .type(r.headers.get("content-type") || "application/json")
                .send(text);
        }
        catch (e) {
            res.status(502).json({ ok: false, error: String(e?.message || e) });
        }
    });
}
else {
    // --- Dev QKD shim (no external service needed) ----------------
    console.log("[radio-node] QKD dev shim enabled");
    const DEV_QKD_TTL_MS = Number(process.env.DEV_QKD_TTL_MS ?? 10 * 60 * 1000);
    const DEV_QKD_SECRET = process.env.DEV_QKD_SECRET || "dev-qkd-secret-not-for-prod";
    app.get("/qkd/health", (_req, res) => {
        res.json({ ok: true, mode: "dev", ttl_ms: DEV_QKD_TTL_MS });
    });
    app.post("/qkd/lease", (req, res) => {
        const r = req.body || {};
        const localWA = String(r.localWA || "");
        const remoteWA = String(r.remoteWA || "");
        const kg = String(r.kg || "personal");
        const purpose = String(r.aad ?? r.purpose ?? "glyph"); // accept either 'aad' or 'purpose'
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
                collapse_hash, // client PBKDF2s this (with salt_b64) → AES-GCM key
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
    if (!wa || !wa.includes("@"))
        return res.status(400).json({ ok: false, error: "invalid wa" });
    const user = slugFromWa(wa);
    const exists = fs.existsSync(path.join(CONTAINERS_ROOT, user));
    res.json({ ok: true, wa, user, available: !exists });
});
// Bootstrap per-user container files
// body: { wa: "kevin@wave.tp" } (optional { user: "kevin", allowReinit: true })
app.post("/api/containers/bootstrap", (req, res) => {
    const wa = String(req.body?.wa || "").trim();
    let user = String(req.body?.user || "").trim();
    if (!wa || !wa.includes("@"))
        return res.status(400).json({ ok: false, error: "invalid wa" });
    if (!user)
        user = slugFromWa(wa);
    user = slugFromWa(user);
    const userDir = path.join(CONTAINERS_ROOT, user);
    const already = fs.existsSync(userDir);
    if (already && !req.body?.allowReinit) {
        return res.status(409).json({ ok: false, error: "user already exists", user, dir: `/containers/${user}/` });
    }
    ensureDir(userDir);
    ensureDir(path.join(userDir, "shared"));
    const homePath = path.join(userDir, "home.json");
    const perPath = path.join(userDir, "kg_personal.json");
    const workPath = path.join(userDir, "kg_work.json");
    const indexPath = path.join(userDir, "index.json");
    writeJson(homePath, homeTemplate(wa, user));
    writeJson(perPath, kgTemplate(wa, user, "personal"));
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
            home: `/containers/${user}/home.json`,
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
let currentSession = null;
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
    const wa = String(req.body?.wa || "").trim(); // e.g. "kevin@wave.tp"
    const slug = String(req.body?.slug || "").trim(); // e.g. "kevin"
    const token = (req.body?.token ?? null);
    const ticket = String(req.body?.ticket || "");
    if (!wa || !wa.includes("@") || !slug) {
        return res.status(400).json({ ok: false, error: "invalid wa/slug" });
    }
    if (!verifySessionTicket(wa, slug, ticket)) {
        return res.status(401).json({ ok: false, error: "bad ticket" });
    }
    currentSession = { wa, slug, token, ts: Date.now() };
    // Ensure manifests exist
    const dir = path.join(CONTAINERS_ROOT, slug);
    const homePath = path.join(dir, "home.json");
    const perPath = path.join(dir, "kg_personal.json");
    const workPath = path.join(dir, "kg_work.json");
    const indexPath = path.join(dir, "index.json");
    ensureDir(dir);
    ensureDir(path.join(dir, "shared"));
    if (!fs.existsSync(homePath))
        writeJson(homePath, homeTemplate(wa, slug));
    if (!fs.existsSync(perPath))
        writeJson(perPath, kgTemplate(wa, slug, "personal"));
    if (!fs.existsSync(workPath))
        writeJson(workPath, kgTemplate(wa, slug, "work"));
    if (!fs.existsSync(indexPath)) {
        writeJson(indexPath, {
            user: slug, wa,
            home: `${slug}__home`,
            personal: `${slug}__kg_personal`,
            work: `${slug}__kg_work`,
            shared: [],
        });
    }
    return res.json({
        ok: true,
        session: currentSession,
        containers: {
            home: `${slug}__home`,
            personal: `${slug}__kg_personal`,
            work: `${slug}__kg_work`,
        },
        staticPaths: {
            home: `/containers/${slug}/home.json`,
            personal: `/containers/${slug}/kg_personal.json`,
            work: `/containers/${slug}/kg_work.json`,
            index: `/containers/${slug}/index.json`,
        },
    });
});
// ───────────────────────────────────────────────────────────────
// HTTP server + explicit WS upgrade mux
const server = http.createServer(app);
server.requestTimeout = 0; // no request timeout for upgrades
server.headersTimeout = 0; // don't kill slow handshakes
server.keepAliveTimeout = 0; // keep-alive off for upgraded sockets
setTimeout(() => { try {
    ensureSerialDriverRegistered();
}
catch (e) {
    console.warn("[rf][serial] init err:", e?.message || e);
} }, 0);
setInterval(() => { try {
    ensureSerialDriverRegistered();
}
catch { } }, 10_000);
// --- GlyphNet WS (noServer; upgrade-routed) ---------------------
const wssGlyph = new WebSocketServer({ noServer: true, perMessageDeflate: false });
wssGlyph.on("connection", (ws, req) => {
    try {
        const url = new URL(req.url || "", URL_BASE);
        const topic = url.searchParams.get("topic") || "";
        const kg = (url.searchParams.get("kg") || "personal").toLowerCase();
        const key = topicKey(topic, kg);
        // Join room (even if topic is empty; client may only listen first)
        joinRoom(key, ws);
        // Say hello to the client so it can verify it joined the right room
        try {
            ws.send(JSON.stringify({ type: "glyphnet/hello", topic, kg, at: now() }));
        }
        catch { }
        // Keep-alive (ping/pong)
        const ping = setInterval(() => { try {
            ws.isAlive = true;
            ws.ping();
        }
        catch { } }, 15000);
        ws.on("pong", () => { ws.isAlive = true; });
        ws.on("message", (data) => {
            let payload;
            try {
                payload = JSON.parse(String(data));
            }
            catch {
                payload = undefined;
            }
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
            const sendTooLarge = (kind, size) => {
                try {
                    ws.send(JSON.stringify({
                        type: "error",
                        code: "RF_PAYLOAD_TOO_LARGE",
                        details: { kind, size, max: MAX_RF_INGRESS_BYTES }
                    }));
                }
                catch { }
            };
            if (cap?.voice_frame?.data_b64) {
                const bytes = b64ToU8(cap.voice_frame.data_b64);
                if (bytes.length > MAX_RF_INGRESS_BYTES)
                    sendTooLarge("voice_frame", bytes.length);
                else
                    enqueueRF(key, bytes, cap.voice_frame.mime);
            }
            else if (cap?.voice_note?.data_b64) {
                const bytes = b64ToU8(cap.voice_note.data_b64);
                if (bytes.length > MAX_RF_INGRESS_BYTES)
                    sendTooLarge("voice_note", bytes.length);
                else
                    enqueueRF(key, bytes, cap.voice_note.mime);
            }
        });
        const cleanup = () => { clearInterval(ping); leaveAll(ws); };
        ws.on("close", cleanup);
        ws.on("error", cleanup);
    }
    catch {
        try {
            ws.close();
        }
        catch { }
    }
});
// --- RF Link Bridge WS (noServer; upgrade-routed) ----------------
const wssRF = new WebSocketServer({ noServer: true, perMessageDeflate: false });
let activeBridge = null;
function authTokenFromWS(req) {
    const h = String(req.headers["authorization"] || "");
    if (h.startsWith("Bearer "))
        return h.slice(7);
    const xbt = String(req.headers["x-bridge-token"] || "");
    if (xbt)
        return xbt;
    try {
        const url = new URL(req.url || "", URL_BASE);
        return url.searchParams.get("token") || "";
    }
    catch {
        return "";
    }
}
function sigFromWS(req) {
    const xsig = String(req.headers["x-bridge-sig"] || "");
    if (xsig)
        return xsig;
    try {
        const url = new URL(req.url || "", URL_BASE);
        return url.searchParams.get("sig") || "";
    }
    catch {
        return "";
    }
}
// --- WS bridge driver registration (one-time) -------------------
let wsBridgeDriverRegistered = false;
function ensureWSBridgeDriverRegistered() {
    if (wsBridgeDriverRegistered)
        return;
    registerDriver({
        id: "ws-bridge-1",
        kind: "ws-bridge",
        sendB64: (b64) => {
            if (!activeBridge || activeBridge.readyState !== WebSocket.OPEN)
                return false;
            try {
                activeBridge.send(JSON.stringify({ type: "tx", bytes_b64: b64 }));
                return true;
            }
            catch {
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
        try {
            ws.close(1008, "unauthorized");
        }
        catch { }
        return;
    }
    console.log(`[rflink] auth ok token=${shortTok} sig=${sigPresent ? "yes" : "no"}`);
    // Single-active-bridge policy
    if (activeBridge && activeBridge.readyState === WebSocket.OPEN) {
        try {
            ws.close(1013, "busy");
        }
        catch { }
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
    try {
        ws.send(JSON.stringify({ type: "hello", mtu: ACTIVE.MTU, rate_hz: ACTIVE.RATE_HZ }));
    }
    catch { }
    pushRFOutboxToBridge();
    const ka = setInterval(() => { try {
        ws.ping();
    }
    catch { } }, 20_000);
    ws.on("message", (data) => {
        let msg;
        try {
            msg = JSON.parse(String(data));
        }
        catch {
            // Opportunistic drain: a peer is around → try shipping any pending frames
            try {
                pushRFOutboxToBridge();
            }
            catch { }
            return;
        }
        if (msg?.type === "rx" &&
            typeof msg.topic === "string" &&
            typeof msg.bytes_b64 === "string") {
            let bytes;
            try {
                bytes = b64ToU8(msg.bytes_b64);
            }
            catch {
                // Opportunistic drain even if decode fails
                try {
                    pushRFOutboxToBridge();
                }
                catch { }
                return;
            }
            processInboundRF(msg.topic, bytes, typeof msg.seq === "number" ? msg.seq : undefined, ua);
            // Opportunistic drain after processing inbound RF
            try {
                pushRFOutboxToBridge();
            }
            catch { }
            return;
        }
        if (msg?.type === "ping") {
            try {
                ws.send(JSON.stringify({ type: "pong", ts: now() }));
            }
            catch { }
            // Opportunistic drain on ping, too
            try {
                pushRFOutboxToBridge();
            }
            catch { }
            return;
        }
        // Any other message: still opportunistically drain
        try {
            pushRFOutboxToBridge();
        }
        catch { }
    });
    ws.on("close", () => { clearInterval(ka); if (activeBridge === ws)
        activeBridge = null; });
    ws.on("error", () => { clearInterval(ka); if (activeBridge === ws)
        activeBridge = null; });
});
// Helper to push outbox frames to the bridge (via drivers)
function pushRFOutboxToBridge() {
    drainOutboxViaDrivers();
}
// --- GHX WS (noServer; upgrade-routed) --------------------------
const wssGHX = new WebSocketServer({ noServer: true, perMessageDeflate: false });
wssGHX.on("connection", (ws, req) => {
    const url = new URL(req.url || "", URL_BASE);
    const id = url.searchParams.get("id") || "unknown";
    const kg = (url.searchParams.get("kg") || "personal").toLowerCase();
    // Map container → GlyphNet topic & room key
    const topic = `ucs://local/${id}`;
    const key = topicKey(topic, kg);
    // Join the GlyphNet room so GHX receives capsules for this container
    joinRoom(key, ws);
    // Hello
    try {
        ws.send(JSON.stringify({ type: "ghx/hello", id, topic, kg, at: now() }));
    }
    catch { }
    // Keep-alive (ping/pong) + heartbeat
    const ping = setInterval(() => { try {
        ws.isAlive = true;
        ws.ping();
    }
    catch { } }, 15000);
    ws.on("pong", () => { ws.isAlive = true; });
    const hb = setInterval(() => {
        try {
            ws.send(JSON.stringify({ type: "ghx/heartbeat", at: now(), id, topic }));
        }
        catch { }
    }, 15000);
    // Allow GHX to publish into its GlyphNet room
    ws.on("message", (data) => {
        let msg;
        try {
            msg = JSON.parse(String(data));
        }
        catch {
            return;
        }
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
function upgradeTo(wss, req, socket, head) {
    wss.handleUpgrade(req, socket, head, (ws) => wss.emit("connection", ws, req));
}
server.on("upgrade", (req, socket, head) => {
    try {
        const { pathname } = new URL(req.url || "", URL_BASE);
        if (pathname === "/ws/glyphnet")
            return upgradeTo(wssGlyph, req, socket, head);
        if (pathname === "/ws/rflink")
            return upgradeTo(wssRF, req, socket, head);
        if (pathname === "/ws/ghx")
            return upgradeTo(wssGHX, req, socket, head);
    }
    catch { }
    socket.destroy();
});
server.on("clientError", (_err, socket) => {
    try {
        socket.end("HTTP/1.1 400 Bad Request\r\n\r\n");
    }
    catch { }
});
server.listen(PORT, () => {
    console.log(`[radio-node] up on http://127.0.0.1:${PORT}  (cloud=${CLOUD_BASE || "disabled"})  ` +
        `profile=${PROFILE_NAME} mtu=${ACTIVE.MTU} rate=${ACTIVE.RATE_HZ}Hz`);
});
