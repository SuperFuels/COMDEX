// server/kg.ts
import express, { Request, Response } from "express";
import Database from "better-sqlite3";
import crypto from "crypto";
import fs from "fs";
import path from "path";

type KG = "personal" | "work";

type KGEventInsert = {
  id?: string;
  thread_id?: string | null;
  topic_wa?: string | null;
  type: string;
  kind?: string | null;
  ts?: number;
  size?: number | null;
  sha256?: string | null;
  payload?: unknown;
};

type KGEventRow = {
  id: string;
  kg: KG;
  owner_wa: string;
  thread_id: string | null;
  topic_wa: string | null;
  type: string;
  kind: string | null;
  ts: number;
  size: number | null;
  sha256: string | null;
  payload: string; // stored as JSON string in DB
};

// ────────────────────────────────────────────────────────────
// DB boot + migrations (run ALL *.sql in numeric order)
// ────────────────────────────────────────────────────────────
const ROOT = process.env.PROJECT_ROOT || process.cwd();
const DB_PATH  = process.env.KG_DB_PATH  || path.join(ROOT, "server/data/kg.db");
const MIGR_DIR = process.env.KG_MIGR_DIR || path.join(ROOT, "server/db/migrations");

fs.mkdirSync(path.dirname(DB_PATH), { recursive: true });
const db = new Database(DB_PATH);

fs.mkdirSync(MIGR_DIR, { recursive: true });
const migrFiles = fs
  .readdirSync(MIGR_DIR)
  .filter(f => f.endsWith(".sql"))
  .sort(); // 001_, 002_, …

for (const f of migrFiles) {
  const sql = fs.readFileSync(path.join(MIGR_DIR, f), "utf8");
  db.exec(sql);
}

const app = express();
app.use(express.json({ limit: "5mb" }));
app.get("/api/_health/kg", (_req, res) => {
  function flatten(appOrRouter: any, base = "", out: string[] = []) {
    const stack = appOrRouter && appOrRouter._router
      ? appOrRouter._router.stack
      : appOrRouter?.stack || [];

    for (const layer of stack || []) {
      if (layer.route) {
        const path = base + layer.route.path;
        for (const m of Object.keys(layer.route.methods || {})) {
          out.push(`${m.toUpperCase()} ${path}`);
        }
      } else if (layer.name === "router" && layer.handle) {
        const prefix = base + (layer.regexp?.fast_slash ? "" : (layer.path || layer.regexp?.source || ""));
        flatten(layer.handle, base, out);       // most Express versions
        flatten(layer.handle, prefix, out);     // fallback for some builds
      } else if (layer.handle?._router) {
        flatten(layer.handle, base, out);       // nested express() apps
      }
    }
    return out;
  }

  const routes = flatten(app);
  res.json({ ok: true, where: "kg.ts", routes });
});

// ───────── Retention sweeper (runs on boot + every 6h) ─────────
const HOUR_MS = 60 * 60 * 1000;
const DAY_MS  = 24 * HOUR_MS;

// Defaults per plan: 30d visits in personal; 90d in work (tweak via env)
const RETAIN_VISITS_PERSONAL_DAYS = Number(process.env.KG_RETAIN_VISITS_PERSONAL_DAYS ?? 30);
const RETAIN_VISITS_WORK_DAYS     = Number(process.env.KG_RETAIN_VISITS_WORK_DAYS ?? 90);
const SWEEP_EVERY_MS              = Number(process.env.KG_SWEEP_EVERY_MS ?? 6 * HOUR_MS);

// Retention sweep driven by kg_retention rules
function runRetentionSweep() {
  try {
    const rules = db.prepare(
      "SELECT kg, type, kind, days FROM kg_retention"
    ).all();

    if (!Array.isArray(rules) || rules.length === 0) {
      if (process.env.NODE_ENV !== "test") {
        console.log("[kg] retention sweep: no rules (kg_retention empty)");
      }
      return;
    }

    // NOTE: if rule.kind is NULL, we don't filter on kind at all (apply to all kinds)
    const del = db.prepare(`
      DELETE FROM kg_events
       WHERE kg = @kg
         AND type = @type
         AND ts < @cutoff
         AND ( @kind IS NULL OR IFNULL(kind, '') = IFNULL(@kind, '') )
    `);

    const now = Date.now();

    const deleted = db.transaction((rs: any[]) => {
      let total = 0;
      for (const r of rs) {
        const cutoff = now - Number(r.days) * 86400000; // days -> ms
        const info = del.run({
          kg: String(r.kg),
          type: String(r.type),
          kind: r.kind == null ? null : String(r.kind),
          cutoff,
        });
        total += info.changes;
      }
      return total;
    })(rules);

    try { db.exec("PRAGMA optimize"); } catch {}

    if (process.env.NODE_ENV !== "test") {
      console.log(`[kg] retention sweep: rules=${rules.length}, deleted=${deleted}`);
    }
  } catch (e) {
    console.warn("[kg] retention sweep error", e);
  }
}

// run once on boot + every 6h (does not keep the process alive)
runRetentionSweep();
const SIX_HOURS = 6 * 60 * 60 * 1000;
const t = setInterval(runRetentionSweep, SIX_HOURS);
(t as any).unref?.();

// Ensure we don't register multiple timers in dev/hot-reload
const SWEEPER_KEY = "__kg_retention_sweeper__";
if (!(globalThis as any)[SWEEPER_KEY]) {
  (globalThis as any)[SWEEPER_KEY] = setInterval(runRetentionSweep, SWEEP_EVERY_MS);
  // Run once on boot:
  runRetentionSweep();
}

// ────────────────────────────────────────────────────────────
// Helpers
// ────────────────────────────────────────────────────────────

function newId(): string {
  return crypto.randomBytes(12).toString("hex");
}

const KG_VALUES = new Set<KG>(["personal", "work"]);

function normalizeKg(x: unknown): KG {
  const v = String(x || "").toLowerCase();
  return (KG_VALUES.has(v as KG) ? v : "personal") as KG;
}

function computeThreadId(kg: KG, topicWa?: string | null): string {
  const t = (topicWa && topicWa.trim()) ? topicWa.trim() : "ucs://local/ucs_hub";
  return `kg:${kg}:${t}`;
}

function ensureNamespaceOnEvent(base: {
  kg?: KG | string | null;
  owner?: string | null;
  owner_wa?: string | null;
  thread_id?: string | null;
  topic_wa?: string | null;
}) {
  const kg = normalizeKg(base.kg);
  const owner_wa = (base.owner_wa || base.owner || "").trim();
  if (!owner_wa) throw new Error("owner_wa is required");

  const topic_wa = (base.topic_wa || "").trim() || null;
  const thread_id =
    base.thread_id && base.thread_id.startsWith(`kg:${kg}:`)
      ? base.thread_id
      : computeThreadId(kg, topic_wa || undefined);

  return { kg, owner_wa, topic_wa, thread_id };
}

function normalizeVisitEvent(it: KGEventInsert, req?: Request): KGEventInsert {
  if (!it || it.type !== "visit") return it;
  const p: any = (it as any).payload || {};
  let host = String(p.host || "");

  // Build an absolute href if possible (prefer payload.href, fallback to Referer/Origin)
  let href: string = String(p.href || p.uri || "");
  const ref = (req?.headers["referer"] as string) || (req?.headers["origin"] as string) || "";

  // If href isn't absolute, try to resolve it against Referer/Origin
  if (!/^https?:\/\//i.test(href)) {
    if (ref && /^https?:\/\//i.test(ref)) {
      try {
        href = new URL(href || "/", ref).toString();
      } catch {/* ignore */}
    }
  }

  // Compute host if missing
  if (!host) {
    try {
      const u = href && /^https?:\/\//i.test(href)
        ? new URL(href)
        : new URL(href || "/", "https://x.invalid");
      host = u.host || "";
    } catch {
      host = "";
    }
  }

  return { ...it, payload: { ...p, href, host } };
}

// Shared INSERT statement
const insertStmt = db.prepare(`
  INSERT INTO kg_events (id,kg,owner_wa,thread_id,topic_wa,type,kind,ts,size,sha256,payload)
  VALUES (@id,@kg,@owner_wa,@thread_id,@topic_wa,@type,@kind,@ts,@size,@sha256,@payload)
`);

function applyEvents(kg: KG, owner: string, events: KGEventInsert[]) {
  let lastId: string | null = null;

  const tx = db.transaction((rows: KGEventInsert[]) => {
    for (const e of rows) {
      const ns = ensureNamespaceOnEvent({
        kg,
        owner_wa: owner,
        thread_id: e.thread_id ?? null,
        topic_wa: e.topic_wa ?? null,
      });

      const id = e.id ?? newId();
      const row = {
        id,
        kg: ns.kg,
        owner_wa: ns.owner_wa,
        thread_id: ns.thread_id,
        topic_wa: ns.topic_wa,
        type: e.type,
        kind: e.kind ?? null,
        ts: Math.round(e.ts ?? Date.now()),
        size: e.size ?? null,
        sha256: e.sha256 ?? null,
        payload: JSON.stringify(e.payload ?? {}),
      };

      insertStmt.run(row);
      lastId = id;
    }
  });

  tx(events);

  return {
    applied: events.length,
    last_event_id: lastId,
  };
}

// ────────────────────────────────────────────────────────────
// POST /api/kg/events
// ────────────────────────────────────────────────────────────

app.post("/api/kg/events", (req: Request, res: Response) => {
  const body = (req.body || {}) as {
    kg?: KG;
    owner?: string;
    events?: KGEventInsert[];
  };

  const kg = normalizeKg(body.kg);
  const owner = String(body.owner || "").trim();
  const events = Array.isArray(body.events) ? body.events : [];

  // 👇 pass req so we can use Referer/Origin when needed
  const normalized = events.map(e => e?.type === "visit" ? normalizeVisitEvent(e, req) : e);

  if (!owner || normalized.length === 0) {
    return res.status(400).json({ ok: false, error: "bad_request" });
  }

  try {
    const result = applyEvents(kg, owner, normalized);
    return res.json({ ok: true, ...result });
  } catch (err) {
    console.error("[kg/events] fail", err);
    return res.status(500).json({ ok: false, error: "db_error" });
  }
});

// --- Thread hydrate (A52) -----------------------------------------------
// --- Thread hydrate (A52) -----------------------------------------------
// GET /api/kg/view/thread?kg=personal&topic_wa=ucs://...&limit=...&after=ts:id
app.get("/api/kg/view/thread", (req: Request, res: Response) => {
  try {
    const kg = String(req.query.kg || "personal").toLowerCase();
    if (kg !== "personal" && kg !== "work") {
      return res.status(400).json({ ok: false, error: "bad_kg" });
    }

    const topic_waQ = (req.query.topic_wa ? String(req.query.topic_wa) : "").trim();
    const thread_idQ = req.query.thread_id ? String(req.query.thread_id) : "";
    const thread_id = thread_idQ || (topic_waQ ? `kg:${kg}:${topic_waQ}` : "");
    if (!thread_id) {
      return res.status(400).json({ ok: false, error: "need topic_wa or thread_id" });
    }

    const limit = Math.max(1, Math.min(500, parseInt(String(req.query.limit || "200"), 10)));
    const after = (req.query.after ? String(req.query.after) : "").trim(); // "ts:id"
    let curTs = 0, curId = "";
    const useAfter = after.includes(":") ? 1 : 0;
    if (useAfter) {
      const [tsStr, idStr] = after.split(":");
      curTs = Math.max(0, parseInt(tsStr, 10) || 0);
      curId = idStr || "";
    }

    const sql = `
      SELECT id, kg, owner_wa, thread_id, topic_wa, type, kind, ts, size, sha256, payload
        FROM kg_events
       WHERE kg = @kg
         AND thread_id = @thread_id
         AND type IN ('message','file','call','ptt_session')
         AND ( @useAfter = 0 OR ts > @curTs OR (ts = @curTs AND id > @curId) )
       ORDER BY ts ASC, id ASC
       LIMIT @limit
    `;

    const rows = db.prepare(sql).all({ kg, thread_id, useAfter, curTs, curId, limit }) as any[];

    // Parse payloads safely (never crash on bad JSON)
    const items = rows.map(r => {
      let payload: any = {};
      try {
        payload = typeof r.payload === "string" ? JSON.parse(r.payload || "{}") : (r.payload ?? {});
      } catch { payload = {}; }
      return { ...r, payload };
    });

    // ---- Aggregates -----------------------------------------------------
    // Calls: summarize per call_id
    type CallFrame = { id: string; ts: number; kind?: string | null; payload: any };
    const callFrames: Record<string, CallFrame[]> = {};
    for (const it of items) {
      if (it.type === "call") {
        const cid = String(it?.payload?.call_id || "");
        if (!cid) continue;
        (callFrames[cid] ||= []).push({ id: it.id, ts: it.ts, kind: it.kind, payload: it.payload });
      }
    }
    const call_summaries = Object.entries(callFrames).map(([call_id, frames]) => {
      frames.sort((a, b) => a.ts - b.ts);
      const first = frames[0];
      const connected = frames.find(f => f.kind === "connected") || null;
      const end = frames.find(f => f.kind === "end")
             || frames.find(f => f.kind === "cancel" || f.kind === "reject")
             || null;
      const lastKind = frames.length ? frames[frames.length - 1].kind : undefined;
      const status = (end?.kind) || (connected ? "connected" : (lastKind || "open"));
      const secs = (end?.payload?.secs != null)
        ? Number(end.payload.secs)
        : (connected && end ? Math.max(0, Math.round((end.ts - connected.ts) / 1000)) : null);
      return {
        call_id,
        started_ts: first?.ts ?? null,
        connected_ts: connected?.ts ?? null,
        ended_ts: end?.ts ?? null,
        status,
        secs
      };
    });

    // PTT totals
    let ptt_total_ms = 0;
    let ptt_sessions = 0;
    for (const it of items) {
      if (it.type === "ptt_session") {
        const ms = Number(it?.payload?.talkMs || 0);
        if (Number.isFinite(ms)) ptt_total_ms += ms;
        ptt_sessions += 1;
      }
    }

    // Attachments: files + voice notes
    let attachments = 0;
    for (const it of items) {
      if (it.type === "file") attachments += 1;
      else if (it.type === "message" && it.kind === "voice") attachments += 1;
    }

    const last = items.length ? items[items.length - 1] : null;
    const next = last ? `${last.ts}:${last.id}` : null;

    return res.json({
      ok: true,
      items,
      aggregates: {
        call_summaries,
        ptt_total_ms,
        ptt_sessions,
        attachments
      },
      next_cursor: next
    });
  } catch (e: any) {
    console.error("[/api/kg/view/thread] error", e);
    return res.status(500).json({ ok: false, error: "db_error" });
  }
});

// --- Visits hydrate (A52) -----------------------------------------------
app.get("/api/kg/view/visits", (req: Request, res: Response) => {
  try {
    const kg = String(req.query.kg || "personal").toLowerCase();
    if (kg !== "personal" && kg !== "work") return res.status(400).json({ ok:false, error:"bad_kg" });

    const topic_wa = String(req.query.topic_wa || "");
    const thread_id = topic_wa ? `kg:${kg}:${topic_wa}` : String(req.query.thread_id || "");
    if (!topic_wa && !thread_id) return res.status(400).json({ ok:false, error:"need topic_wa or thread_id" });

    const limit = Math.max(1, Math.min(500, parseInt(String(req.query.limit || "200"), 10)));
    const after = String(req.query.after || "");

    let afterTs = 0, afterId = "";
    if (after && after.includes(":")) {
      const [tsStr, idStr] = after.split(":");
      afterTs = Math.max(0, parseInt(tsStr, 10) || 0);
      afterId = idStr || "";
    }

    const baseWhere = [
      "kg = @kg",
      "type = 'visit'",
      "(kind = 'page' OR kind = 'dwell')",
      thread_id ? "thread_id = @thread_id" : "topic_wa = @topic_wa",
      after ? "(ts > @afterTs OR (ts = @afterTs AND id > @afterId))" : "1=1",
    ].join(" AND ");

    const sql = `
      SELECT id, kg, topic_wa, thread_id, type, kind, ts,
             json_extract(payload,'$.uri')         AS uri,
             json_extract(payload,'$.href')        AS href,
             json_extract(payload,'$.host')        AS host,
             json_extract(payload,'$.title')       AS title,
             json_extract(payload,'$.referrer')    AS referrer,
             json_extract(payload,'$.duration_s')  AS duration_s,
             json_extract(payload,'$.origin_id')   AS origin_id
        FROM kg_events
       WHERE ${baseWhere}
       ORDER BY ts ASC, id ASC
       LIMIT @limit
    `;

    type VisitRow = {
      id:string; ts:number; uri?:string|null; href?:string|null; host?:string|null;
      title?:string|null; referrer?:string|null; duration_s?:number|null; origin_id?:string|null;
      kg:string; topic_wa:string|null; thread_id:string|null; type:string; kind:string|null
    };

    const rows = db.prepare(sql).all({
      kg, thread_id, topic_wa, afterTs, afterId, limit
    }) as VisitRow[];

    const last = rows.length ? rows[rows.length - 1] : null;
    const next = last ? `${last.ts}:${last.id}` : null;

    return res.json({ ok:true, items: rows, next_cursor: next });
  } catch (e:any) {
    console.error("[/kg/view/visits] error", e);
    return res.status(500).json({ ok:false, error:"db_error" });
  }
});

// --- Forget API (A56) ----------------------------------------------------
app.post("/api/kg/forget", (req: Request, res: Response) => {
  try {
    const { kg, scope="visits", host, topic_wa, from_ms, to_ms } = req.body || {};
    const KG = String(kg || "personal").toLowerCase();
    if (KG !== "personal" && KG !== "work") return res.status(400).json({ ok:false, error:"bad_kg" });

    const WHERE: string[] = ["kg = @kg"];
    const params: any = { kg: KG };

    if (scope === "visits") WHERE.push("type = 'visit'");
    if (host)      { WHERE.push("json_extract(payload,'$.host') = @host"); params.host = String(host); }
    if (topic_wa)  { WHERE.push("topic_wa = @topic_wa"); params.topic_wa = String(topic_wa); }
    if (Number.isFinite(from_ms)) { WHERE.push("ts >= @from_ms"); params.from_ms = Math.max(0, parseInt(String(from_ms), 10)); }
    if (Number.isFinite(to_ms))   { WHERE.push("ts < @to_ms");   params.to_ms   = Math.max(0, parseInt(String(to_ms), 10)); }

    if (WHERE.length === 1) return res.status(400).json({ ok:false, error:"too_broad" });

    const sql = `DELETE FROM kg_events WHERE ${WHERE.join(" AND ")}`;
    const info = db.prepare(sql).run(params);
    return res.json({ ok:true, deleted: info.changes });
  } catch (e:any) {
    console.error("[/kg/forget] error", e);
    return res.status(500).json({ ok:false, error:"db_error" });
  }
});

// ────────────────────────────────────────────────────────────
/** GET /api/kg/query
 *  Query by kg + optional thread_id/topic_wa, with cursor `after=ts:id`.
 */
// ────────────────────────────────────────────────────────────
app.get("/api/kg/query", (req: Request, res: Response) => {
  const kg = normalizeKg(req.query.kg);
  const thread_idQ = req.query.thread_id ? String(req.query.thread_id) : null;
  const topic_waQ  = req.query.topic_wa  ? String(req.query.topic_wa)  : null;
  const after      = req.query.after     ? String(req.query.after)     : null; // cursor "ts:id"
  const limit      = Math.min(Math.max(1, Number(req.query.limit || 200)), 500);

  let curTs = 0;
  let curId = "";
  if (after) {
    const [tsStr, idStr] = after.split(":");
    curTs = Number(tsStr || 0);
    curId = idStr || "";
  }

  const clauses: string[] = ["kg = @kg"];
  const params: Record<string, unknown> = { kg, limit, curTs, curId };

  // Prefer explicit thread_id; else derive from topic_wa for stable partition reads
  if (thread_idQ) {
    clauses.push("thread_id = @thread_id");
    (params as any).thread_id = thread_idQ;
  } else if (topic_waQ) {
    const derived = computeThreadId(kg, topic_waQ);
    clauses.push("thread_id = @thread_id");
    (params as any).thread_id = derived;
  }

  if (topic_waQ) {
    clauses.push("topic_wa = @topic_wa");
    (params as any).topic_wa = topic_waQ;
  }

  if (after) {
    clauses.push("(ts > @curTs OR (ts = @curTs AND id > @curId))");
  }

  const sql = `
    SELECT id,kg,owner_wa,thread_id,topic_wa,type,kind,ts,size,sha256,payload
    FROM kg_events
    WHERE ${clauses.join(" AND ")}
    ORDER BY ts ASC, id ASC
    LIMIT @limit
  `;

  try {
    const rows = db.prepare(sql).all(params) as KGEventRow[];
    const items = rows.map((r) => {
      let payload: any = {};
      try { payload = typeof r.payload === "string" ? JSON.parse(r.payload) : (r.payload ?? {}); }
      catch { payload = {}; }
      return { ...r, payload };
    });
    const lastItem = items.length ? items[items.length - 1] : undefined;
    const next_cursor = lastItem ? `${lastItem.ts}:${lastItem.id}` : null;
    res.json({ ok: true, items, next_cursor });
  } catch (err) {
    console.error("[kg/query] fail", err);
    res.status(500).json({ ok: false, error: "db_error" });
  }
});

// ────────────────────────────────────────────────────────────
// GET /api/kg/thread  (helper for ChatThread.tsx)
// Example: /api/kg/thread?kg=personal&topic=ucs://local/ucs_hub&owner=kevin@wave.tp
// ────────────────────────────────────────────────────────────
app.get("/api/kg/thread", (req: Request, res: Response) => {
  try {
    const kg = normalizeKg(req.query.kg);
    const topic_wa =
      String(req.query.topic || req.query.topic_wa || "ucs://local/ucs_hub").trim();
    const owner_wa = String(req.query.owner || req.query.owner_wa || "").trim();
    const thread_id = computeThreadId(kg, topic_wa || undefined);

    const thread = {
      kg,
      owner_wa,
      topic_wa,
      topic: topic_wa,
      thread_id,
      threadId: thread_id,
    };

    return res.json({
      ok: true,
      thread,
      // also spread for callers that don't expect nesting
      ...thread,
    });
  } catch (err) {
    console.error("[kg/thread] fail", err);
    return res.status(500).json({ ok: false, error: "server_error" });
  }
});

export default app;