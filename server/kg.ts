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

function hashCookieValue(raw: string): string {
  try {
    return crypto.createHash("sha256").update(raw, "utf8").digest("hex");
  } catch {
    return raw;
  }
}

// ───────────────── Retention (A55/A57) ─────────────────

const MS_PER_DAY = 24 * 60 * 60 * 1000;

type KGRetentionConfig = {
  visitsDays?: number;
  cookiesDays?: number;
  // you can add messagesDays, filesDays later if you want
};

// Default per-graph retention (can be overridden via env)
const RETENTION_DEFAULTS: Record<KG, KGRetentionConfig> = {
  personal: {
    visitsDays: 30,  // auto-forget browser visits after ~30 days
    cookiesDays: 30, // auto-forget habit cookies after ~30 days
  },
  work: {
    visitsDays: 90,  // keep work browsing slightly longer
    cookiesDays: 90,
  },
};

// Optional per-graph "toggles" via env, e.g.
//   KG_PERSONAL_VISITS_RETENTION_DAYS=0   → disable visits cleanup for personal
//   KG_WORK_COOKIES_RETENTION_DAYS=14     → 2-week cookie retention for work
function getRetentionConfig(kg: KG): KGRetentionConfig {
  const base = RETENTION_DEFAULTS[kg] || {};

  function envInt(name: string): number | undefined {
    const raw = process.env[name];
    if (!raw) return undefined;
    const n = parseInt(raw, 10);
    return Number.isFinite(n) && n >= 0 ? n : undefined;
  }

  const prefix = kg === "personal" ? "KG_PERSONAL" : "KG_WORK";

  const visitsOverride  = envInt(`${prefix}_VISITS_RETENTION_DAYS`);
  const cookiesOverride = envInt(`${prefix}_COOKIES_RETENTION_DAYS`);

  return {
    visitsDays:
      visitsOverride !== undefined ? visitsOverride : base.visitsDays,
    cookiesDays:
      cookiesOverride !== undefined ? cookiesOverride : base.cookiesDays,
  };
}

// remember when we last ran cleanup per kg so we don't hammer sqlite
const lastRetentionRun: Record<KG, number> = {
  personal: 0,
  work: 0,
};

function applyRetentionIfDue(kg: KG) {
  const now = Date.now();
  const last = lastRetentionRun[kg] || 0;

  // Only run at most every 10 minutes per kg
  if (now - last < 10 * 60 * 1000) return;
  lastRetentionRun[kg] = now;

  const cfg = getRetentionConfig(kg);

  // ── Visits cleanup ────────────────────────────────────
  if (cfg.visitsDays && cfg.visitsDays > 0) {
    const cutoff = now - cfg.visitsDays * MS_PER_DAY;
    try {
      const stmt = db.prepare(
        `DELETE FROM kg_events
          WHERE kg = @kg
            AND type = 'visit'
            AND ts < @cutoff`
      );
      const info = stmt.run({ kg, cutoff });
      if (info.changes) {
        console.log(
          "[kg] retention: deleted %d old visits for kg=%s before %d",
          info.changes,
          kg,
          cutoff
        );
      }
    } catch (err) {
      console.warn("[kg] retention: visit cleanup failed", err);
    }
  }

  // ── Cookies cleanup ───────────────────────────────────
  if (cfg.cookiesDays && cfg.cookiesDays > 0) {
    const cutoff = now - cfg.cookiesDays * MS_PER_DAY;
    try {
      const stmt = db.prepare(
        `DELETE FROM kg_cookie
          WHERE kg = @kg
            AND updated_ts < @cutoff`
      );
      const info = stmt.run({ kg, cutoff });
      if (info.changes) {
        console.log(
          "[kg] retention: deleted %d old cookies for kg=%s before %d",
          info.changes,
          kg,
          cutoff
        );
      }
    } catch (err) {
      console.warn("[kg] retention: cookie cleanup failed", err);
    }
  }

  // NOTE: if you later want auto-forget messages/files, add similar blocks here.
}
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

// ───────────────── Topic upsert helper (A7) ─────────────────

// Cache prepared statement
let stmtUpsertTopic: any | null = null;

// Normalize WA: lowercase + strip trailing slashes
function canonTopicWa(raw: string | null | undefined): string {
  if (!raw) return "";
  return raw.trim().toLowerCase().replace(/\/+$/, "");
}

/**
 * Ensure a Topic row exists for this (kg, topic_wa).
 * Uses WA as the primary key; WN + label are optional and can be filled later.
 */
function ensureTopicRow(
  ns: { kg: KG; topic_wa: string | null },
  ev: KGEventInsert
) {
  const kg = ns.kg;
  if (!kg) return;

  const rawWa = ns.topic_wa || ev.topic_wa || null;
  const topic_wa = canonTopicWa(rawWa);
  if (!topic_wa) return;

  const topic_id = `topic:${topic_wa}`;

  // Optional: pull a human label / WN out of the payload if present
  const payload: any = ev.payload || {};
  const label =
    payload.topicLabel ??
    payload.label ??
    null;

  const topic_wn =
    payload.topic_wn ??
    payload.topicWn ??
    null;

  // For now, realm == kg (we can refine later when you add org/realms)
  const realm = kg;

  const now = Math.round(ev.ts ?? Date.now());

  if (!stmtUpsertTopic) {
    stmtUpsertTopic = db.prepare(`
      INSERT INTO kg_topic (
        kg, topic_wa, topic_wn, topic_id, label, realm, created_ts, updated_ts
      ) VALUES (
        @kg, @topic_wa, @topic_wn, @topic_id, @label, @realm, @now, @now
      )
      ON CONFLICT (kg, topic_id) DO UPDATE SET
        topic_wa   = excluded.topic_wa,
        topic_wn   = COALESCE(excluded.topic_wn, kg_topic.topic_wn),
        label      = COALESCE(excluded.label,    kg_topic.label),
        realm      = COALESCE(excluded.realm,    kg_topic.realm),
        updated_ts = excluded.updated_ts;
    `);
  }

  stmtUpsertTopic.run({
    kg,
    topic_wa,
    topic_wn,
    topic_id,
    label,
    realm,
    now,
  });
}

// ───────────────── Thread upsert helper (A8) ─────────────────
function insertHeldByEdge(kg: KG, e: KGEventInsert, ns: {
  kg: KG;
  owner_wa: string;
  thread_id: string | null;
  topic_wa: string | null;
}, eventId: string) {
  if (e.type !== "floor_lock") return;

  // Prefer explicit owner on the event payload, else fall back to ns.owner_wa
  const payload: any = e.payload ?? {};
  const owner = payload.owner || ns.owner_wa;
  if (!owner) return;

  insertEdge({
    kg,
    kind: "HELD_BY",
    src_type: "floor_lock",
    src_id: eventId,
    dst_type: "agent",
    dst_id: owner,
    created_ts: e.ts,
  });
}
// Cache prepared statement
let stmtUpsertThread: any | null = null;

// ────────────────────────────────────────────────────────────
// Cookie → OBSERVED_FOR edges (A25)
//   - Cookie node is the src (kg_cookie.id)
//   - Agent and/or Thread are dsts
// ────────────────────────────────────────────────────────────

function ensureCookieEdges(row: {
  kg: KG;
  id: string;
  agent_wa?: string | null;
  thread_id?: string | null;
  created_ts?: number;
}) {
  const ts = row.created_ts ?? Date.now();

  if (row.agent_wa) {
    insertEdge({
      kg: row.kg,
      kind: "OBSERVED_FOR",
      src_type: "cookie",
      src_id: row.id,
      dst_type: "agent",
      dst_id: row.agent_wa,
      created_ts: ts,
    });
  }

  if (row.thread_id) {
    insertEdge({
      kg: row.kg,
      kind: "OBSERVED_FOR",
      src_type: "cookie",
      src_id: row.id,
      dst_type: "thread",
      dst_id: row.thread_id,
      created_ts: ts,
    });
  }
}

// ────────────────────────────────────────────────────────────
// ContainerRef → ABOUT edges (A26)
//   - ContainerRef node is src (kg_container_ref.id)
//   - Thread and/or Topic are dsts
// ────────────────────────────────────────────────────────────

function ensureContainerRefEdges(row: {
  kg: KG;
  id: string;
  thread_id?: string | null;
  topic_wa?: string | null;
  created_ts?: number;
}) {
  const ts = row.created_ts ?? Date.now();

  if (row.thread_id) {
    insertEdge({
      kg: row.kg,
      kind: "ABOUT",
      src_type: "container_ref",
      src_id: row.id,
      dst_type: "thread",
      dst_id: row.thread_id,
      created_ts: ts,
    });
  }

  if (row.topic_wa) {
    insertEdge({
      kg: row.kg,
      kind: "ABOUT",
      src_type: "container_ref",
      src_id: row.id,
      dst_type: "topic",
      dst_id: row.topic_wa,
      created_ts: ts,
    });
  }
}

/**
 * Ensure a Thread row exists for this (kg, thread_id).
 * Uses the namespace-normalized thread_id + topic_wa from ensureNamespaceOnEvent.
 */
function ensureThreadRow(
  ns: { kg: KG; thread_id: string | null; topic_wa: string | null },
  ev: KGEventInsert
) {
  const kg = ns.kg;
  if (!kg) return;

  const thread_id = ns.thread_id;
  const topic_wa  = (ns.topic_wa || "").trim();
  if (!thread_id || !topic_wa) return;

  const payload: any = ev.payload || {};

  const topic_wn =
    payload.topic_wn ??
    payload.topicWn ??
    null;

  const now = Math.round(ev.ts ?? Date.now());

  if (!stmtUpsertThread) {
    stmtUpsertThread = db.prepare(`
      INSERT INTO kg_thread (
        kg, thread_id, topic_wa, topic_wn, created_ts, updated_ts, last_event_ts
      ) VALUES (
        @kg, @thread_id, @topic_wa, @topic_wn, @now, @now, @now
      )
      ON CONFLICT (kg, thread_id) DO UPDATE SET
        topic_wa      = excluded.topic_wa,
        topic_wn      = COALESCE(excluded.topic_wn, kg_thread.topic_wn),
        updated_ts    = excluded.updated_ts,
        last_event_ts = excluded.last_event_ts;
    `);
  }

  stmtUpsertThread.run({
    kg,
    thread_id,
    topic_wa,
    topic_wn,
    now,
  });
}

function newId(): string {
  return crypto.randomBytes(12).toString("hex");
}

const KG_VALUES = new Set<KG>(["personal", "work"]);

function normalizeKg(x: unknown): KG {
  const v = String(x || "").toLowerCase();
  return (KG_VALUES.has(v as KG) ? v : "personal") as KG;
}

function computeThreadId(kg: KG, topicWa?: string | null): string {
  const tRaw = topicWa && topicWa.trim()
    ? topicWa.trim()
    : "ucs://local/ucs_hub";

  const t = canonTopicWa(tRaw);
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

  // Canonical topic WA everywhere (matches kg_topic / kg_thread)
  const topicRaw = (base.topic_wa || "").trim();
  const topic_wa = topicRaw ? canonTopicWa(topicRaw) : null;

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

// Shared INSERT statement for kg_events
const insertStmt = db.prepare(`
  INSERT INTO kg_events (id,kg,owner_wa,thread_id,topic_wa,type,kind,ts,size,sha256,payload)
  VALUES (@id,@kg,@owner_wa,@thread_id,@topic_wa,@type,@kind,@ts,@size,@sha256,@payload)
`);

// ────────────────────────────────────────────────────────────
// Edge insert (generic) — used for SENT_BY / ON_TOPIC / IN_THREAD / HELD_BY / etc.
// ────────────────────────────────────────────────────────────

let insertEdgeStmt: any | null = null;

function insertEdge(params: {
  kg: KG;
  kind: string;       // 'SENT_BY' | 'ON_TOPIC' | 'IN_THREAD' | 'HELD_BY' | ...
  src_type: string;   // 'message' | 'ptt_session' | 'floor_lock' | ...
  src_id: string;     // event id (kg_events.id)
  dst_type: string;   // 'agent' | 'topic' | 'thread'
  dst_id: string;     // e.g. owner_wa, topic_wa, thread_id
  created_ts?: number;
}) {
  const { kg, kind, src_type, src_id, dst_type, dst_id } = params;
  if (!dst_id) return;           // don't insert dangling edges

  if (!insertEdgeStmt) {
    insertEdgeStmt = db.prepare(`
      INSERT OR IGNORE INTO kg_edge (
        kg, kind, src_type, src_id, dst_type, dst_id, created_ts
      ) VALUES (
        @kg, @kind, @src_type, @src_id, @dst_type, @dst_id, @created_ts
      )
    `);
  }

  insertEdgeStmt.run({
    kg,
    kind,
    src_type,
    src_id,
    dst_type,
    dst_id,
    created_ts: params.created_ts ?? Date.now(),
  });
}


// ────────────────────────────────────────────────────────────
// Helpers for A21: HAS_ATTACHMENT(Message→Attachment→File)
// ────────────────────────────────────────────────────────────

function approxBytesFromB64(b64: string): number {
  const len = b64.length;
  let padding = 0;
  if (b64.endsWith("==")) padding = 2;
  else if (b64.endsWith("=")) padding = 1;
  return Math.max(0, Math.floor(len * 0.75) - padding);
}

// ────────────────────────────────────────────────────────────
// ContainerRef helper: upsert kg_container_ref + ABOUT edges
// ────────────────────────────────────────────────────────────

let stmtUpsertContainerRef: any | null = null;

function ensureContainerRef(
  kg: KG,
  row: {
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
  },
  payload: any
) {
  // Only handle explicit container_ref events
  if (row.type !== "container_ref") return;

  const p = payload || {};

  const container_id: string | undefined =
    p.container_id || p.containerId || p.id;
  const kind: string | undefined =
    p.kind || p.type || "canvas";

  if (!container_id || !kind) return;

  const path: string | null =
    typeof p.path === "string" && p.path.trim() ? p.path.trim() : null;

  // Stable id per (kg, container_id, path)
  const key = path ? `${kg}|${container_id}#${path}` : `${kg}|${container_id}`;

  let id: string;
  if (typeof p.ref_id === "string" && p.ref_id.trim()) {
    id = p.ref_id.trim();
  } else {
    const h = crypto.createHash("sha256");
    h.update(key);
    id = "cont:" + h.digest("hex");
  }

  if (!stmtUpsertContainerRef) {
    stmtUpsertContainerRef = db.prepare(`
      INSERT INTO kg_container_ref (
        kg, id, container_id, kind, path, thread_id, topic_wa, created_ts, updated_ts, meta
      ) VALUES (
        @kg, @id, @container_id, @kind, @path, @thread_id, @topic_wa, @ts, @ts, @meta
      )
      ON CONFLICT(id) DO UPDATE SET
        container_id = excluded.container_id,
        kind        = excluded.kind,
        path        = excluded.path,
        thread_id   = COALESCE(excluded.thread_id, kg_container_ref.thread_id),
        topic_wa    = COALESCE(excluded.topic_wa, kg_container_ref.topic_wa),
        updated_ts  = excluded.updated_ts,
        meta        = CASE
                        WHEN excluded.meta IS NOT NULL THEN excluded.meta
                        ELSE kg_container_ref.meta
                      END
    `);
  }

  const ts = row.ts || Date.now();
  const meta = p.meta ? JSON.stringify(p.meta) : null;

  stmtUpsertContainerRef.run({
    kg,
    id,
    container_id,
    kind,
    path,
    thread_id: row.thread_id || null,
    topic_wa: row.topic_wa || null,
    ts,
    meta,
  });

  // ABOUT(ContainerRef→Thread)
  if (row.thread_id) {
    insertEdge({
      kg,
      kind: "ABOUT",
      src_type: "container_ref",
      src_id: id,
      dst_type: "thread",
      dst_id: row.thread_id,
      created_ts: ts,
    });
  }

  // ABOUT(ContainerRef→Topic)
  if (row.topic_wa) {
    insertEdge({
      kg,
      kind: "ABOUT",
      src_type: "container_ref",
      src_id: id,
      dst_type: "topic",
      dst_id: row.topic_wa,
      created_ts: ts,
    });
  }
}

// Prepared statements for file + attachment tables
// Prepared statements for file + attachment tables
let stmtFindFileBySha: any | null = null;
let stmtInsertFile: any | null = null;
let stmtInsertAttachment: any | null = null;

function ensureFileAttachmentForEvent(
  kg: KG,
  row: {
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
  },
  payload: any
) {
  // For now: only treat message events with binary/fingerprint as attachments
  if (row.type !== "message") return;

  const p = payload || {};

  const mime: string = p.mime || p.type || "";
  const data_b64: string | undefined = p.data_b64 || p.data;
  const data_fp: string | undefined = p.data_fp;

  // If we don't even know the mime, nothing useful to store
  if (!mime) return;

  // If we have neither raw bytes nor a fingerprint, skip
  if (
    typeof data_b64 !== "string" &&
    typeof data_fp !== "string" &&
    row.size == null &&
    p.size == null
  ) {
    return;
  }

  // 1) Ensure we have a sha256 (use event.sha256 if present, else compute)
  let sha = row.sha256 || p.sha256 || null;

  if (!sha) {
    try {
      const h = crypto.createHash("sha256");

      if (typeof data_b64 === "string" && data_b64.length) {
        // hash real bytes if we have them
        const buf = Buffer.from(data_b64, "base64");
        h.update(buf);
      } else if (typeof data_fp === "string" && data_fp.length) {
        // otherwise hash the fingerprint string (size:head..tail)
        h.update(data_fp);
      } else {
        // last-ditch: derive from event metadata so it's at least stable
        h.update(`${row.id}:${row.type}:${mime}:${row.ts}`);
      }

      sha = h.digest("hex");
    } catch (e) {
      console.warn("[kg] ensureFileAttachmentForEvent: sha256 failed", e);
      return;
    }
  }

  // 2) Prepare stmts if needed
  if (!stmtFindFileBySha) {
    stmtFindFileBySha = db.prepare(
      "SELECT file_id FROM kg_file WHERE kg = @kg AND sha256 = @sha LIMIT 1"
    );
  }
  if (!stmtInsertFile) {
    stmtInsertFile = db.prepare(`
      INSERT INTO kg_file (
        kg, file_id, name, mime, size, sha256, location, version, created_ts, updated_ts
      ) VALUES (
        @kg, @file_id, @name, @mime, @size, @sha256, @location, @version, @ts, @ts
      )
    `);
  }
  if (!stmtInsertAttachment) {
    stmtInsertAttachment = db.prepare(`
      INSERT INTO kg_attachment (
        id, kg, event_id, thread_id, topic_wa, file_id, mime, size, sha256, created_ts
      ) VALUES (
        @id, @kg, @event_id, @thread_id, @topic_wa, @file_id, @mime, @size, @sha256, @created_ts
      )
    `);
  }

  // 3) Find or create file row (kg_file)
  let fileId: string;
  const existing = stmtFindFileBySha.get({ kg, sha }) as { file_id: string } | undefined;

  if (existing && existing.file_id) {
    fileId = existing.file_id;
  } else {
    fileId = `file:${sha}`;

    // Try to recover size from event/inline/fingerprint
    let fpSize: number | null = null;
    if (typeof data_fp === "string" && data_fp.length) {
      const idx = data_fp.indexOf(":");
      if (idx > 0) {
        const raw = data_fp.slice(0, idx);
        const n = Number(raw);
        if (Number.isFinite(n) && n >= 0) fpSize = n;
      }
    }

    const sizeGuess =
      row.size ??
      p.size ??
      fpSize ??
      (typeof data_b64 === "string" ? approxBytesFromB64(data_b64) : null);

    const name: string =
      p.name ||
      (mime.startsWith("audio/") ? "voice-note" :
       mime.startsWith("image/") ? "image" :
       mime.startsWith("application/pdf") ? "document" :
       "file");

    const ts = row.ts || Date.now();

    stmtInsertFile.run({
      kg,
      file_id: fileId,
      name,
      mime,
      size: sizeGuess ?? null,
      sha256: sha,
      location: null,   // we can add 'rf://...' or 's3://...' later
      version: 1,
      ts,
    });
  }

  // 4) Create attachment row (kg_attachment)
  const attId = `att:${newId()}`;

  let fpSize2: number | null = null;
  if (typeof data_fp === "string" && data_fp.length) {
    const idx = data_fp.indexOf(":");
    if (idx > 0) {
      const raw = data_fp.slice(0, idx);
      const n = Number(raw);
      if (Number.isFinite(n) && n >= 0) fpSize2 = n;
    }
  }

  const attSize =
    row.size ??
    p.size ??
    fpSize2 ??
    (typeof data_b64 === "string" ? approxBytesFromB64(data_b64) : null);

  stmtInsertAttachment.run({
    id: attId,
    kg,
    event_id: row.id,
    thread_id: row.thread_id || null,
    topic_wa: row.topic_wa || null,
    file_id: fileId,
    mime,
    size: attSize ?? null,
    sha256: sha,
    created_ts: row.ts || Date.now(),
  });

  // 5) Edge: HAS_ATTACHMENT(Message→Attachment)
  insertEdge({
    kg,
    kind: "HAS_ATTACHMENT",
    src_type: "message",
    src_id: row.id,
    dst_type: "attachment",
    dst_id: attId,
    created_ts: row.ts || Date.now(),
  });
}

// ────────────────────────────────────────────────────────────
// Cookies: upsert + OBSERVED_FOR edges (A25)
// ────────────────────────────────────────────────────────────

type CookieScope = "agent" | "thread" | "topic" | "global";

let stmtSelectCookie: any | null = null;
let stmtInsertCookie: any | null = null;
let stmtUpdateCookie: any | null = null;

type UpsertCookieOpts = {
  kg: KG;
  scope: CookieScope | string;
  key: string;
  agent_wa?: string | null;
  thread_id?: string | null;
  topic_wa?: string | null;
  value_hash: string;
  policy?: string | null;
  meta?: any;
  now?: number;
  ttlMs?: number;
};

/**
 * Upsert a cookie row and return its id (or null on no-op).
 * Identity = (kg, scope, key, agent_wa, thread_id, topic_wa).
 */
function upsertCookie(opts: UpsertCookieOpts): string | null {
  const now = opts.now ?? Date.now();
  const expires_ts = opts.ttlMs ? now + opts.ttlMs : null;
  const metaStr = opts.meta !== undefined ? JSON.stringify(opts.meta) : null;

  if (!opts.kg || !opts.scope || !opts.key) return null;

  if (!stmtSelectCookie) {
    stmtSelectCookie = db.prepare(`
      SELECT id
        FROM kg_cookie
       WHERE kg = @kg
         AND scope = @scope
         AND key = @key
         AND IFNULL(agent_wa,'')  = IFNULL(@agent_wa,'')
         AND IFNULL(thread_id,'') = IFNULL(@thread_id,'')
         AND IFNULL(topic_wa,'')  = IFNULL(@topic_wa,'')
       LIMIT 1
    `);
  }

  if (!stmtInsertCookie) {
    stmtInsertCookie = db.prepare(`
      INSERT INTO kg_cookie (
        kg, id, scope, agent_wa, thread_id, topic_wa,
        key, value_hash, policy,
        created_ts, updated_ts, expires_ts, meta
      ) VALUES (
        @kg, @id, @scope, @agent_wa, @thread_id, @topic_wa,
        @key, @value_hash, @policy,
        @now, @now, @expires_ts, @meta
      )
    `);
  }

  if (!stmtUpdateCookie) {
    stmtUpdateCookie = db.prepare(`
      UPDATE kg_cookie
         SET value_hash = @value_hash,
             policy     = @policy,
             meta       = @meta,
             updated_ts = @now,
             expires_ts = @expires_ts
       WHERE id = @id
    `);
  }

  const params = {
    kg: opts.kg,
    scope: String(opts.scope),
    key: opts.key,
    agent_wa: opts.agent_wa ?? null,
    thread_id: opts.thread_id ?? null,
    topic_wa: opts.topic_wa ?? null,
  };

  const existing = stmtSelectCookie.get(params) as { id: string } | undefined;

  if (existing && existing.id) {
    stmtUpdateCookie.run({
      id: existing.id,
      ...params,
      value_hash: opts.value_hash,
      policy: opts.policy ?? null,
      meta: metaStr,
      now,
      expires_ts,
    });
    return existing.id;
  }

  const id = `cookie:${newId()}`;
  stmtInsertCookie.run({
    id,
    ...params,
    value_hash: opts.value_hash,
    policy: opts.policy ?? null,
    meta: metaStr,
    now,
    expires_ts,
  });

  return id;
}

/**
 * OBSERVED_FOR edges: Cookie -> Agent / Thread
 */
function ensureCookieObservedFor(
  kg: KG,
  cookieId: string,
  opts: { agent_wa?: string | null; thread_id?: string | null; ts: number }
) {
  if (!cookieId) return;
  const ts = opts.ts || Date.now();

  if (opts.agent_wa) {
    insertEdge({
      kg,
      kind: "OBSERVED_FOR",
      src_type: "cookie",
      src_id: cookieId,
      dst_type: "agent",
      dst_id: opts.agent_wa,
      created_ts: ts,
    });
  }

  if (opts.thread_id) {
    insertEdge({
      kg,
      kind: "OBSERVED_FOR",
      src_type: "cookie",
      src_id: cookieId,
      dst_type: "thread",
      dst_id: opts.thread_id,
      created_ts: ts,
    });
  }
}

// SENT_BY(Message→Agent)
function insertSentByEdge(
  kg: KG,
  ev: KGEventInsert,
  ns: { kg: KG; owner_wa: string; thread_id: string | null; topic_wa: string | null },
  eventId: string
) {
  if (ev.type !== "message") return;

  const payload: any = ev.payload || {};
  const agentWaRaw =
    payload.agentId ||
    payload.agent_wa ||
    payload.from ||
    ns.owner_wa;

  const agent_wa = String(agentWaRaw || "").trim();
  if (!agent_wa) return;

  insertEdge({
    kg,
    kind: "SENT_BY",
    src_type: "message",
    src_id: eventId,
    dst_type: "agent",
    dst_id: agent_wa,
  });
}

// ON_TOPIC(Event→Topic)
function insertOnTopicEdge(
  kg: KG,
  ev: KGEventInsert,
  ns: { kg: KG; owner_wa: string; thread_id: string | null; topic_wa: string | null },
  eventId: string
) {
  const topicWa = ns.topic_wa;
  if (!topicWa) return;

  insertEdge({
    kg,
    kind: "ON_TOPIC",
    src_type: ev.type,
    src_id: eventId,
    dst_type: "topic",
    dst_id: topicWa,     // you can later swap to topic_id if you prefer
  });
}

// IN_THREAD(Event→Thread)
function insertInThreadEdge(
  kg: KG,
  ev: KGEventInsert,
  ns: { kg: KG; owner_wa: string; thread_id: string | null; topic_wa: string | null },
  eventId: string
) {
  const threadId = ns.thread_id;
  if (!threadId) return;

  insertEdge({
    kg,
    kind: "IN_THREAD",
    src_type: ev.type,
    src_id: eventId,
    dst_type: "thread",
    dst_id: threadId,
  });
}
function insertVisitedByEdge(
  kg: KG,
  e: KGEventInsert,
  ns: {
    kg: KG;
    owner_wa: string;
    thread_id: string | null;
    topic_wa: string | null;
  },
  eventId: string
) {
  // Only care about visit events
  if (e.type !== "visit") return;

  // For visits, "who visited" is just the owner WA from the event namespace
  const agentWa = ns.owner_wa;
  if (!agentWa) return;

  insertEdge({
    kg,
    kind: "VISITED_BY",
    src_type: "visit",
    src_id: eventId,
    dst_type: "agent",
    dst_id: agentWa,
    created_ts: e.ts,
  });
}

function insertPartOfEdge(
  kg: KG,
  e: KGEventInsert,
  ns: {
    kg: KG;
    owner_wa: string;
    thread_id: string | null;
    topic_wa: string | null;
  },
  eventId: string
) {
  // Only care about call events
  if (e.type !== "call") return;

  const threadId = ns.thread_id;
  if (!threadId) return;

  insertEdge({
    kg,
    kind: "PART_OF",
    src_type: "call",
    src_id: eventId,
    dst_type: "thread",
    dst_id: threadId,
    created_ts: e.ts,
  });
}

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

      // 👇 payload into a variable so helpers can see it
      const payload = e.payload ?? {};

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
        payload: JSON.stringify(payload),
      };

      // 1) Write the event row
      insertStmt.run(row);
      lastId = id;

      // 2) Satellite helpers (no-op if type doesn’t match)
      //    - Files + attachments (A21)
      //    - ContainerRef + ABOUT edges (A26)
      ensureFileAttachmentForEvent(ns.kg, row, payload);
      ensureContainerRef(ns.kg, row, payload);

      // 3) Core edges (SENT_BY / ON_TOPIC / IN_THREAD)
      insertSentByEdge(ns.kg, e, ns, id);    // Message→Agent
      insertOnTopicEdge(ns.kg, e, ns, id);   // Event→Topic
      insertInThreadEdge(ns.kg, e, ns, id);  // Event→Thread

      // 5) COOKIES (A25): useful cookies + OBSERVED_FOR edges (with hashed values)
      if (row.type === "message") {
        const nowTs = row.ts || Date.now();

        // 5a) Agent-scoped: last_active_topic
        if (row.owner_wa && (row.topic_wa || row.thread_id)) {
          const rawValue = row.topic_wa || row.thread_id || "";
          const valueHash = hashCookieValue(rawValue);

          const cookieId = upsertCookie({
            kg: ns.kg,
            scope: "agent",
            key: "last_active_topic",
            agent_wa: row.owner_wa,
            thread_id: null,
            topic_wa: null,
            value_hash: valueHash,       // 🔐 hashed, not raw
            policy: "habit",
            meta: {
              topic_wa: row.topic_wa || null,  // 👈 human-readable lives here
              thread_id: row.thread_id || null,
            },
            now: nowTs,
            ttlMs: 30 * 24 * 60 * 60 * 1000, // ~30 days
          });

          if (cookieId) {
            ensureCookieObservedFor(ns.kg, cookieId, {
              agent_wa: row.owner_wa,
              thread_id: null,
              ts: nowTs,
            });
          }
        }

        // 5b) Thread-scoped: last_message_ts
        if (row.thread_id) {
          const rawTs = String(nowTs);
          const valueHash = hashCookieValue(rawTs);

          const cookieId2 = upsertCookie({
            kg: ns.kg,
            scope: "thread",
            key: "last_message_ts",
            agent_wa: null,
            thread_id: row.thread_id,
            topic_wa: row.topic_wa || null,
            value_hash: valueHash,        // 🔐 hashed timestamp
            policy: "analytics",
            meta: {
              last_ts: nowTs,             // 👈 real value lives in meta
              owner_wa: row.owner_wa || null,
            },
            now: nowTs,
            ttlMs: 7 * 24 * 60 * 60 * 1000, // ~7 days
          });

          if (cookieId2) {
            ensureCookieObservedFor(ns.kg, cookieId2, {
              agent_wa: row.owner_wa || null,
              thread_id: row.thread_id,
              ts: nowTs,
            });
          }
        }
      }

      // 6) Per-type extras

      // VISITED_BY(Visit→Agent)
      if (row.type === "visit") {
        const p: any = payload || {};
        const who =
          p.agent_wa ||
          p.ownerWa ||
          p.owner_wa ||
          row.owner_wa ||
          owner;

        if (who) {
          insertEdge({
            kg: ns.kg,
            kind: "VISITED_BY",
            src_type: "visit",
            src_id: row.id,
            dst_type: "agent",
            dst_id: who,
            created_ts: row.ts,
          });
        }
      }

      // PART_OF(Call→Thread)
      if (row.type === "call" && row.thread_id) {
        insertEdge({
          kg: ns.kg,
          kind: "PART_OF",
          src_type: "call",
          src_id: row.id,
          dst_type: "thread",
          dst_id: row.thread_id,
          created_ts: row.ts,
        });
      }

      // HELD_BY(FloorLock→Agent) + extra IN_THREAD/ON_TOPIC for floor_lock
      if (row.type === "floor_lock") {
        const p: any = payload || {};
        const lockOwnerWa =
          p.ownerWa ||
          p.owner_wa ||
          row.owner_wa ||
          owner;

        if (row.thread_id) {
          insertEdge({
            kg: ns.kg,
            kind: "IN_THREAD",
            src_type: "floor_lock",
            src_id: row.id,
            dst_type: "thread",
            dst_id: row.thread_id,
            created_ts: row.ts,
          });
        }

        if (row.topic_wa) {
          insertEdge({
            kg: ns.kg,
            kind: "ON_TOPIC",
            src_type: "floor_lock",
            src_id: row.id,
            dst_type: "topic",
            dst_id: row.topic_wa,
            created_ts: row.ts,
          });
        }

        if (lockOwnerWa) {
          insertEdge({
            kg: ns.kg,
            kind: "HELD_BY",
            src_type: "floor_lock",
            src_id: row.id,
            dst_type: "agent",
            dst_id: lockOwnerWa,
            created_ts: row.ts,
          });
        }
      }

      // ENTANGLEMENT: ContainerRef ↔ ContainerRef
      // Comes from KnowledgeGraphWriter.write_entanglement_entry(...) via inject_glyph(...)
      if (row.type === "entanglement") {
        const p: any = payload || {};
        const meta: any = p.metadata || {};

        const a = meta.from || meta.container_a || null;
        const b = meta.to   || meta.container_b || null;

        if (a && b) {
          insertEdge({
            kg: ns.kg,
            kind: "ENTANGLEMENT",
            src_type: "container_ref",
            src_id: a,
            dst_type: "container_ref",
            dst_id: b,
            created_ts: row.ts,
          });
        }
      }
    }
  });

  tx(events);

  // ── Apply per-graph retention (A55/A57) ─────────────────────────────
  applyRetentionIfDue(kg);

  return {
    applied: events.length,
    last_event_id: lastId,
  };
}

// ────────────────────────────────────────────────────────────
// GET /api/kg/search
// Cross-thread search over Message(text), Visit(uri/title/host), File.name
// Example:
//   /api/kg/search?kg=personal&q=alice
//   /api/kg/search?kg=work&q=wave&scope=message,file&limit=50
// ────────────────────────────────────────────────────────────
app.get("/api/kg/search", (req: Request, res: Response) => {
  try {
    const kg = normalizeKg(req.query.kg);
    const qRaw = String(req.query.q || "").trim();
    if (!qRaw) {
      return res.status(400).json({ ok: false, error: "missing_query" });
    }

    // limit 1..200
    const limit = Math.max(
      1,
      Math.min(200, parseInt(String(req.query.limit || "50"), 10) || 50)
    );

    // scope controls which buckets we search: message|visit|file
    const scopeRaw = String(req.query.scope || "message,visit,file").toLowerCase();
    const wantMessages = scopeRaw.includes("message");
    const wantVisits   = scopeRaw.includes("visit");
    const wantFiles    = scopeRaw.includes("file");

    // Generic LIKE pattern for messages / visits
    const pat = `%${qRaw}%`;

    // File-specific pattern: strip leading dots so ".pdf" matches "application/pdf"
    const filePat = qRaw.startsWith(".")
      ? `%${qRaw.replace(/^\.+/, "")}%`
      : pat;

    const result: {
      ok: boolean;
      kg: KG;
      q: string;
      messages: any[];
      visits: any[];
      files: any[];
    } = {
      ok: true,
      kg,
      q: qRaw,
      messages: [],
      visits: [],
      files: [],
    };

    // ── Messages: text only (kind='text') ────────────────────
    if (wantMessages) {
      const sqlMessages = `
        SELECT
          id,
          thread_id,
          topic_wa,
          ts,
          kind,
          json_extract(payload,'$.text') AS text,
          json_extract(payload,'$.from') AS from_wa,
          json_extract(payload,'$.to')   AS to_wa
        FROM kg_events
        WHERE kg = @kg
          AND type = 'message'
          AND kind = 'text'
          AND json_extract(payload,'$.text') LIKE @pat
        ORDER BY ts DESC, id DESC
        LIMIT @limit
      `;

      const rows = db.prepare(sqlMessages).all({ kg, pat, limit }) as any[];
      result.messages = rows.map(r => ({
        id:        r.id,
        thread_id: r.thread_id,
        topic_wa:  r.topic_wa,
        ts:        r.ts,
        text:      r.text,
        from:      r.from_wa,
        to:        r.to_wa,
      }));
    }

    // ── Visits: title / uri / host ───────────────────────────
    if (wantVisits) {
      const sqlVisits = `
        SELECT
          id,
          thread_id,
          topic_wa,
          ts,
          json_extract(payload,'$.uri')    AS uri,
          json_extract(payload,'$.href')   AS href,
          json_extract(payload,'$.host')   AS host,
          json_extract(payload,'$.title')  AS title,
          json_extract(payload,'$.referrer') AS referrer
        FROM kg_events
        WHERE kg = @kg
          AND type = 'visit'
          AND (
            json_extract(payload,'$.title') LIKE @pat OR
            json_extract(payload,'$.uri')   LIKE @pat OR
            json_extract(payload,'$.href')  LIKE @pat OR
            json_extract(payload,'$.host')  LIKE @pat
          )
        ORDER BY ts DESC, id DESC
        LIMIT @limit
      `;

      const rows = db.prepare(sqlVisits).all({ kg, pat, limit }) as any[];
      result.visits = rows.map(r => ({
        id:        r.id,
        thread_id: r.thread_id,
        topic_wa:  r.topic_wa,
        ts:        r.ts,
        uri:       r.uri || r.href || null,
        host:      r.host,
        title:     r.title,
        referrer:  r.referrer,
      }));
    }

    // ── Files: name / mime / sha256 LIKE pattern (joined via kg_attachment when possible) ───
    if (wantFiles) {
      const sqlFiles = `
        SELECT
          f.kg,
          f.file_id,
          f.name,
          f.mime,
          f.size,
          f.sha256,
          f.created_ts,
          a.event_id,
          a.thread_id,
          a.topic_wa
        FROM kg_file AS f
        LEFT JOIN kg_attachment AS a
          ON a.kg = f.kg
         AND a.file_id = f.file_id
        WHERE f.kg = @kg
          AND (
            (f.name   IS NOT NULL AND f.name   LIKE @filePat) OR
            (f.mime   IS NOT NULL AND f.mime   LIKE @filePat) OR
            (f.sha256 IS NOT NULL AND f.sha256 LIKE @filePat)
          )
        ORDER BY f.created_ts DESC
        LIMIT @limit
      `;

      const rows = db.prepare(sqlFiles).all({ kg, filePat, limit }) as any[];
      result.files = rows.map(r => ({
        file_id:    r.file_id,
        name:       r.name,
        mime:       r.mime,
        size:       r.size,
        sha256:     r.sha256,
        created_ts: r.created_ts,
        // linkage back into the graph if the attachment exists
        event_id:   r.event_id || null,
        thread_id:  r.thread_id || null,
        topic_wa:   r.topic_wa || null,
      }));
    }

    return res.json(result);
  } catch (e: any) {
    console.error("[/api/kg/search] error", e);
    return res.status(500).json({ ok: false, error: "db_error" });
  }
});

// ────────────────────────────────────────────────────────────
// GET /api/kg/view/memory
// AION memory views:
//   /api/kg/view/memory?kg=personal&scope=habits
//   /api/kg/view/memory?kg=personal&scope=topics
//   /api/kg/view/memory?kg=personal&scope=people
// Returns a small JSON summary the AI can consume.
// ────────────────────────────────────────────────────────────
app.get("/api/kg/view/memory", (req: Request, res: Response) => {
  try {
    const kg = normalizeKg(req.query.kg);
    const scope = String(req.query.scope || "habits").toLowerCase();

    const out: any = { ok: true, kg, scope };

    // ── habits: cookies / last-active / last-message ─────────
    if (scope === "habits") {
      // Agent-scoped "last_active_topic"
      const sqlAgentHabits = `
        SELECT
          id,
          scope,
          agent_wa,
          key,
          value_hash,
          created_ts,
          updated_ts,
          expires_ts,
          meta
        FROM kg_cookie
        WHERE kg = @kg
          AND scope = 'agent'
          AND key   = 'last_active_topic'
        ORDER BY updated_ts DESC
        LIMIT 200
      `;

      const agentRows = db.prepare(sqlAgentHabits).all({ kg }) as any[];
      const agents = agentRows.map(r => {
        let meta: any = null;
        try { meta = r.meta ? JSON.parse(r.meta) : null; } catch {}
        return {
          cookie_id:  r.id,
          agent_wa:   r.agent_wa,
          key:        r.key,
          last_value: r.value_hash,
          created_ts: r.created_ts,
          updated_ts: r.updated_ts,
          expires_ts: r.expires_ts,
          topic_wa:   meta?.topic_wa || null,
          thread_id:  meta?.thread_id || null,
        };
      });

      // Thread-scoped "last_message_ts"
      const sqlThreadHabits = `
        SELECT
          id,
          scope,
          thread_id,
          topic_wa,
          key,
          value_hash,
          created_ts,
          updated_ts,
          expires_ts,
          meta
        FROM kg_cookie
        WHERE kg = @kg
          AND scope = 'thread'
          AND key   = 'last_message_ts'
        ORDER BY updated_ts DESC
        LIMIT 500
      `;

      const threadRows = db.prepare(sqlThreadHabits).all({ kg }) as any[];
      const threads = threadRows.map(r => {
        let meta: any = null;
        try { meta = r.meta ? JSON.parse(r.meta) : null; } catch {}
        return {
          cookie_id:  r.id,
          thread_id:  r.thread_id,
          topic_wa:   r.topic_wa,
          key:        r.key,
          last_ts:    Number(r.value_hash || meta?.last_ts || 0),
          created_ts: r.created_ts,
          updated_ts: r.updated_ts,
          expires_ts: r.expires_ts,
          owner_wa:   meta?.owner_wa || null,
        };
      });

      out.habits = { agents, threads };
      return res.json(out);
    }

    // ── topics: label / wave number / realm ──────────────────
    if (scope === "topics") {
      const sqlTopics = `
        SELECT
          kg,
          topic_wa,
          topic_wn,
          topic_id,
          label,
          realm,
          created_ts,
          updated_ts
        FROM kg_topic
        WHERE kg = @kg
        ORDER BY updated_ts DESC
        LIMIT 500
      `;

      const rows = db.prepare(sqlTopics).all({ kg }) as any[];
      out.topics = rows.map(r => ({
        topic_wa:  r.topic_wa,
        topic_wn:  r.topic_wn,
        topic_id:  r.topic_id,
        label:     r.label,
        realm:     r.realm,
        created_ts: r.created_ts,
        updated_ts: r.updated_ts,
      }));
      return res.json(out);
    }

    // ── people: "topic" rows that look like people  ──────────
    // For now we treat any topic with a label as a "person/contact".
    if (scope === "people") {
      const sqlPeople = `
        SELECT
          kg,
          topic_wa,
          topic_wn,
          topic_id,
          label,
          realm,
          created_ts,
          updated_ts
        FROM kg_topic
        WHERE kg = @kg
          AND label IS NOT NULL
        ORDER BY updated_ts DESC
        LIMIT 500
      `;

      const rows = db.prepare(sqlPeople).all({ kg }) as any[];
      out.people = rows.map(r => ({
        topic_wa:  r.topic_wa,
        topic_wn:  r.topic_wn,
        topic_id:  r.topic_id,
        label:     r.label,
        realm:     r.realm,
        created_ts: r.created_ts,
        updated_ts: r.updated_ts,
      }));
      return res.json(out);
    }

    // Unknown scope → 400
    return res.status(400).json({ ok: false, error: "invalid_scope", scope });
  } catch (e: any) {
    console.error("[/api/kg/view/memory] error", e);
    return res.status(500).json({ ok: false, error: "db_error" });
  }
});

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
// POST /api/kg/upsert-entity  (A34)
//   - Upsert Topic or Thread rows in a kg-safe way
//   - Idempotent: safe to call multiple times
// ────────────────────────────────────────────────────────────
app.post("/api/kg/upsert-entity", (req: Request, res: Response) => {
  try {
    const body = (req.body || {}) as any;
    const kg = normalizeKg(body.kg);
    const entity = String(body.entity || body.type || "").toLowerCase();

    if (!kg) {
      return res.status(400).json({ ok: false, error: "missing_kg" });
    }
    if (!entity) {
      return res.status(400).json({ ok: false, error: "missing_entity" });
    }

    // ── upsert Topic ─────────────────────────────────────────
    if (entity === "topic") {
      const rawWa =
        body.topic_wa ||
        body.topicWa ||
        body.wa ||
        null;

      const topic_wa = canonTopicWa(rawWa);
      if (!topic_wa) {
        return res.status(400).json({ ok: false, error: "missing_topic_wa" });
      }

      const topic_id = `topic:${topic_wa}`;
      const topic_wn: string | null =
        body.topic_wn ||
        body.topicWn ||
        body.wn ||
        null;

      const label: string | null =
        body.label ||
        body.topicLabel ||
        null;

      const realm: string = body.realm || kg;
      const now = Date.now();

      // Insert-or-update into kg_topic
      db.prepare(`
        INSERT INTO kg_topic (
          kg, topic_wa, topic_wn, topic_id, label, realm, created_ts, updated_ts
        ) VALUES (
          @kg, @topic_wa, @topic_wn, @topic_id, @label, @realm, @now, @now
        )
        ON CONFLICT (kg, topic_id) DO UPDATE SET
          topic_wa   = excluded.topic_wa,
          topic_wn   = COALESCE(excluded.topic_wn, kg_topic.topic_wn),
          label      = COALESCE(excluded.label,    kg_topic.label),
          realm      = COALESCE(excluded.realm,    kg_topic.realm),
          updated_ts = excluded.updated_ts
      `).run({
        kg,
        topic_wa,
        topic_wn,
        topic_id,
        label,
        realm,
        now,
      });

      // Read back the fresh row
      const row = db.prepare(`
        SELECT kg, topic_wa, topic_wn, topic_id, label, realm, created_ts, updated_ts
          FROM kg_topic
         WHERE kg = @kg AND topic_id = @topic_id
      `).get({ kg, topic_id }) as any;

      return res.json({ ok: true, entity: "topic", topic: row });
    }

    // ── upsert Thread ────────────────────────────────────────
    if (entity === "thread") {
      const rawTopicWa =
        body.topic_wa ||
        body.topicWa ||
        body.topic ||
        null;

      const topic_wa = rawTopicWa ? canonTopicWa(rawTopicWa) : null;

      // Derive thread_id if not explicitly provided
      const thread_id: string =
        body.thread_id ||
        (topic_wa ? computeThreadId(kg, topic_wa) : "");

      if (!thread_id) {
        return res.status(400).json({ ok: false, error: "need_thread_id_or_topic_wa" });
      }

      const topic_wn: string | null =
        body.topic_wn ||
        body.topicWn ||
        body.wn ||
        null;

      const now = Date.now();

      // Upsert into kg_thread. We only touch the safe fields; everything else keeps its old value.
      db.prepare(`
        INSERT INTO kg_thread (
          kg, thread_id, topic_wa, topic_wn, created_ts, updated_ts, last_event_ts
        ) VALUES (
          @kg, @thread_id, @topic_wa, @topic_wn, @now, @now, @last_event_ts
        )
        ON CONFLICT (kg, thread_id) DO UPDATE SET
          topic_wa      = COALESCE(excluded.topic_wa, kg_thread.topic_wa),
          topic_wn      = COALESCE(excluded.topic_wn, kg_thread.topic_wn),
          updated_ts    = excluded.updated_ts,
          last_event_ts = COALESCE(kg_thread.last_event_ts, excluded.last_event_ts)
      `).run({
        kg,
        thread_id,
        topic_wa,
        topic_wn,
        now,
        last_event_ts: now,
      });

      const row = db.prepare(`
        SELECT kg, thread_id, topic_wa, topic_wn, created_ts, updated_ts, last_event_ts
          FROM kg_thread
         WHERE kg = @kg AND thread_id = @thread_id
      `).get({ kg, thread_id }) as any;

      return res.json({ ok: true, entity: "thread", thread: row });
    }

    return res.status(400).json({ ok: false, error: "unsupported_entity" });
  } catch (e: any) {
    console.error("[/api/kg/upsert-entity] error", e);
    return res.status(500).json({ ok: false, error: "server_error" });
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