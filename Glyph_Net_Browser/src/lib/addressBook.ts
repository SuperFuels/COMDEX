// src/lib/addressBook.ts

export type GraphKey = "personal" | "work";

/* ──────────────────────────────
   Recents (v2) — per-graph entries
   ────────────────────────────── */
export type RecentItem = {
  topic: string;
  label?: string;
  graph: GraphKey;
  ts: number;
};

const RECENTS_V2_KEY = "gnet:recents:v2";   // map<string, RecentItem>
const RECENTS_V1A    = "gnet:recents";      // old array, maybe without graph/ts
const RECENTS_V1B    = "gnet:recent";       // another legacy name (array)

/* ──────────────────────────────
   Contacts book (label ↔ topics)
   ────────────────────────────── */
export type Contact = {
  label: string;                                   // "Kevin"
  topics: Partial<Record<GraphKey, string>>;       // { personal: "ucs://...", work: "ucs://..." }
  uses?: number;
  updatedAt?: number;
};

const BOOK_KEY = "gnet:addrbook:v1";

/* utils */
function loadJSON<T>(k: string, fallback: T): T {
  try {
    const raw = localStorage.getItem(k);
    return raw ? (JSON.parse(raw) as T) : fallback;
  } catch {
    return fallback;
  }
}
function saveJSON(k: string, v: any) {
  try {
    localStorage.setItem(k, JSON.stringify(v));
  } catch {}
}

/* v1 → v2 migration (runs lazily) */
function loadRecentsMap(): Record<string, RecentItem> {
  // Prefer v2 map
  const v2 = loadJSON<Record<string, RecentItem> | null>(RECENTS_V2_KEY, null);
  if (v2 && typeof v2 === "object") return v2;

  // Otherwise migrate from either legacy array key
  const legacyA = loadJSON<any[]>(RECENTS_V1A, []);
  const legacyB = legacyA.length ? [] : loadJSON<any[]>(RECENTS_V1B, []);

  const legacy = legacyA.length ? legacyA : legacyB;
  const map: Record<string, RecentItem> = {};

  if (Array.isArray(legacy) && legacy.length) {
    for (const r of legacy) {
      const graph: GraphKey = r.graph === "work" ? "work" : r.kg === "work" ? "work" : "personal";
      const topic: string = r.topic || "";
      if (!topic) continue;
      const ts: number = typeof r.ts === "number" ? r.ts : (typeof r.lastTs === "number" ? r.lastTs : Date.now());
      const item: RecentItem = { topic, label: r.label, graph, ts };
      map[`${graph}:${topic}`] = item;
    }
    saveJSON(RECENTS_V2_KEY, map);
    return map;
  }

  // Nothing to migrate; start fresh
  return {};
}

function saveRecentsMap(map: Record<string, RecentItem>) {
  saveJSON(RECENTS_V2_KEY, map);
}

/* ──────────────────────────────
   Public API
   ────────────────────────────── */

export function rememberTopic(topic: string, label: string | undefined, graph: GraphKey) {
  const t = (topic || "").trim();
  if (!t) return;

  const map = loadRecentsMap();
  const now = Date.now();
  const item: RecentItem = { topic: t, label, graph, ts: now };
  map[`${graph}:${t}`] = item;

  // keep last 100 by ts
  const entries = Object.values(map).sort((a, b) => b.ts - a.ts).slice(0, 100);
  const next: Record<string, RecentItem> = {};
  for (const it of entries) next[`${it.graph}:${it.topic}`] = it;
  saveRecentsMap(next);

  // Learn contact mapping if it looks like a human label
  if (label && !label.startsWith("ucs://")) {
    upsertContact(label, graph, t);
  }
}

export function getRecent(limit = 20): RecentItem[] {
  return Object.values(loadRecentsMap()).sort((a, b) => b.ts - a.ts).slice(0, limit);
}

/* Contacts */
function loadBook(): Record<string, Contact> {
  return loadJSON<Record<string, Contact>>(BOOK_KEY, {});
}
function saveBook(db: Record<string, Contact>) {
  saveJSON(BOOK_KEY, db);
}

export function upsertContact(label: string, graph: GraphKey, topic: string) {
  const key = (label || "").trim().toLowerCase();
  if (!key) return;

  const db = loadBook();
  const c: Contact = db[key] || { label, topics: {} };
  c.label = label;
  c.topics[graph] = topic;
  c.updatedAt = Date.now();
  c.uses = (c.uses ?? 0) + 1;
  db[key] = c;
  saveBook(db);
}

export function getContacts(): Contact[] {
  return Object.values(loadBook()).sort((a, b) => (b.updatedAt || 0) - (a.updatedAt || 0));
}

/**
 * Resolve a human address like "kevin" or "kevin@work" to a concrete topic.
 * Falls back to the input if it already looks like a ucs:// topic or
 * there’s no contact match.
 */
export function resolveHumanAddress(
  input: string,
  preferredGraph: GraphKey = "personal"
): { topic: string; label?: string; graph: GraphKey } {
  const v = (input || "").trim();
  if (!v) return { topic: "", graph: preferredGraph };

  // Already a topic
  if (v.startsWith("ucs://")) return { topic: v, graph: preferredGraph };

  // Allow "label@work" / "label@personal"
  const m = v.match(/^(.+?)@(work|personal)$/i);
  const graph: GraphKey = (m?.[2]?.toLowerCase() as GraphKey) || preferredGraph;
  const label = (m?.[1] || v).trim();

  const book = loadBook();
  const c = book[label.toLowerCase()];
  if (c?.topics?.[graph]) {
    return { topic: c.topics[graph]!, label: c.label, graph };
  }

  // Fallback: treat the input as a topic if it’s not a known label
  return { topic: v, graph };
}