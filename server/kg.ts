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

const ROOT = process.env.PROJECT_ROOT || process.cwd();
const DB_PATH   = process.env.KG_DB_PATH   || path.join(ROOT, "server/data/kg.db");
const MIGR_PATH = process.env.KG_MIGR_PATH || path.join(ROOT, "server/db/migrations/001_kg.sql");

// Ensure data dir & run migration on boot
fs.mkdirSync(path.dirname(DB_PATH), { recursive: true });
const db = new Database(DB_PATH);
const schemaSql = fs.readFileSync(MIGR_PATH, "utf8");
db.exec(schemaSql); // creates tables/indexes if missing

const app = express();
app.use(express.json({ limit: "5mb" }));

function newId(): string {
  return crypto.randomBytes(12).toString("hex");
}
function isKG(x: unknown): x is KG {
  return x === "personal" || x === "work";
}

// ────────────────────────────────────────────────────────────
// Namespace helpers (hard graph boundary + stable thread_id)
// ────────────────────────────────────────────────────────────
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

// -------------------------
// POST /api/kg/events
// -------------------------
app.post("/api/kg/events", (req: Request, res: Response) => {
  const { kg, owner, events } = (req.body || {}) as {
    kg?: KG;
    owner?: string;
    events?: KGEventInsert[];
  };

  if (!isKG(kg) || !owner || !Array.isArray(events) || events.length === 0) {
    return res.status(400).json({ ok: false, error: "bad_request" });
  }

  const stmt = db.prepare(`
    INSERT INTO kg_events (id,kg,owner_wa,thread_id,topic_wa,type,kind,ts,size,sha256,payload)
    VALUES (@id,@kg,@owner_wa,@thread_id,@topic_wa,@type,@kind,@ts,@size,@sha256,@payload)
  `);

  const tx = db.transaction((rows: KGEventInsert[]) => {
    for (const e of rows) {
      const ns = ensureNamespaceOnEvent({
        kg,
        owner_wa: owner,
        thread_id: e.thread_id ?? null,
        topic_wa: e.topic_wa ?? null,
      });

      const row = {
        id: e.id || newId(),
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
      stmt.run(row);
    }
  });

  try {
    tx(events);
    const lastEvent = events.length ? events[events.length - 1] : null; // ← no .at()
    return res.json({
      ok: true,
      applied: events.length,
      last_event_id: lastEvent && lastEvent.id ? lastEvent.id : null,
    });
  } catch (err) {
    console.error("[kg/events] fail", err);
    return res.status(500).json({ ok: false, error: "db_error" });
  }
});

// -------------------------
// GET /api/kg/query
// -------------------------
app.get("/api/kg/query", (req: Request, res: Response) => {
  const kgQ = String(req.query.kg || "");
  if (!isKG(kgQ)) return res.status(400).json({ ok: false, error: "bad_kg" });
  const kg = normalizeKg(kgQ);

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
    const items = rows.map((r) => ({ ...r, payload: JSON.parse(r.payload) }));
    const lastItem = items.length ? items[items.length - 1] : undefined; // ← no .at()
    const next_cursor = lastItem ? `${lastItem.ts}:${lastItem.id}` : null;
    res.json({ ok: true, items, next_cursor });
  } catch (err) {
    console.error("[kg/query] fail", err);
    res.status(500).json({ ok: false, error: "db_error" });
  }
});

export default app;