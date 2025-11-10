// radio-node/server.ts
import express, { type Request, type Response, type NextFunction } from "express";
import http, { type IncomingMessage } from "http";
import cors from "cors";
import { WebSocketServer, WebSocket } from "ws";

// ---- config ---------------------------------------------------
const PORT = Number(process.env.PORT || 8787);
const CLOUD_BASE = (process.env.CLOUD_BASE || "").replace(/\/+$/, "");
const FORWARD_TO_CLOUD = !!CLOUD_BASE;

// ---- simple helpers -------------------------------------------
function now() { return Date.now(); }
function msgId() { return `loc-${now()}-${Math.random().toString(36).slice(2, 8)}`; }
function topicKey(topic: string, kg?: string) { return `${(kg || "personal").toLowerCase()}:${topic}`; }

// ---- WS room registry -----------------------------------------
const rooms = new Map<string, Set<WebSocket>>();
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
  for (const ws of set) if (ws.readyState === WebSocket.OPEN) try { ws.send(data); } catch {}
}

// ---- retry queue for cloud forwards ---------------------------
type TxItem = { id: string; body: any; tries: number; nextAt: number; };
const queue: TxItem[] = [];
let cloudOk = !FORWARD_TO_CLOUD;

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

// ---- HTTP server ----------------------------------------------
const app = express();
app.use(cors());
app.use(express.json({ limit: "5mb" }));

// Dev-friendly headers so WS works from the 8787 URL
app.use((_: Request, res: Response, next: NextFunction) => {
  res.setHeader("Access-Control-Allow-Origin", "*");
  res.setHeader("Access-Control-Allow-Headers", "Content-Type, X-Agent-Id, X-Agent-Token");
  res.setHeader("Content-Security-Policy", "default-src 'self'; connect-src * blob: data: ws: wss: http: https:");
  next();
});

app.get("/", (_req: Request, res: Response) => {
  res.type("text").send("radio-node up • try /health or WebSocket at /ws/glyphnet");
});

app.get("/health", (_req: Request, res: Response) => {
  res.json({ ok: true, cloudOk, queue: queue.length, ts: now() });
});

// Accept a GlyphNet TX; echo to local WS room; optionally forward to cloud (or queue)
app.post("/api/glyphnet/tx", async (req: Request, res: Response) => {
  const body = req.body || {};
  const recipient = String(body.recipient || "");
  const graph = String(body.graph || "personal").toLowerCase();
  const key = topicKey(recipient, graph);

  const id = msgId();

  const envelope = {
    capsule: body.capsule || {},
    meta: { ...(body.meta || {}), graph },
    ts: now(),
    id,
  };
  broadcast(key, { type: "glyphnet_capsule", envelope });

  let forwarded = false;
  if (FORWARD_TO_CLOUD) {
    const ok = await tryForward({ id, body, tries: 0, nextAt: 0 });
    forwarded = ok;
    if (!ok) queue.push({ id, body, tries: 0, nextAt: now() + 1000 });
  }

  res.json({ ok: true, msg_id: id, forwarded, queued: FORWARD_TO_CLOUD && !forwarded });
});

// ---- WS server -------------------------------------------------
const server = http.createServer(app);
const wss = new WebSocketServer({ server, path: "/ws/glyphnet" });

wss.on("connection", (ws: WebSocket, req: IncomingMessage) => {
  try {
    const url = new URL(req.url || "", `http://${req.headers.host}`);
    const topic = url.searchParams.get("topic") || "";
    const kg = (url.searchParams.get("kg") || "personal").toLowerCase();
    const key = topicKey(topic, kg);
    joinRoom(key, ws);

    const ping = setInterval(() => { try { (ws as any).isAlive = true; ws.ping(); } catch {} }, 15000);
    ws.on("pong", () => { (ws as any).isAlive = true; });

    ws.on("message", (data: Buffer) => {
      let payload: any;
      try { payload = JSON.parse(String(data)); } catch {}
      const envelope = {
        capsule: payload?.capsule ?? payload ?? { glyphs: ["(echo)"] },
        meta: payload?.meta ?? { graph: kg },
        ts: now(),
        id: msgId(),
      };
      broadcast(key, { type: "glyphnet_capsule", envelope });
    });

    ws.on("close", () => { clearInterval(ping); leaveAll(ws); });
    ws.on("error", () => { clearInterval(ping); leaveAll(ws); });
  } catch { ws.close(); }
});

server.listen(PORT, () => {
  console.log(`[radio-node] up on http://127.0.0.1:${PORT}  (cloud=${CLOUD_BASE || "disabled"})`);
});