// frontend/src/glyphnet/lib/addressBook.ts

import type { GraphKey } from "@glyphnet/utils/nameService";
import { saveBestLabel, getLabelForWA } from "@glyphnet/utils/nameService";

/* ──────────────────────────────
   Recents (v2) — per-graph entries
   ────────────────────────────── */

/**
 * NOTE: Some UI components (e.g. WaveOutbox) expect:
 *  - getRecent() items include `uses`
 *  - rememberTopic(topic, label) to be valid (graph optional)
 *
 * So we keep v2 fields but add compat fields.
 */
export type RecentItem = {
  topic: string; // WA (ucs://…)
  label?: string; // best-known display label at time of remember
  graph: GraphKey; // "personal" | "work"
  ts: number; // last-used timestamp (ms)

  // compat / UI fields
  uses: number; // how many times used (for chips + titles)
  lastUsedMs: number; // alias of ts for older/newer call-sites
};

const RECENTS_V2_KEY = "gnet:recents:v2"; // map<string, RecentItem>
const RECENTS_V1A = "gnet:recents"; // old array, maybe without graph/ts/uses
const RECENTS_V1B = "gnet:recent"; // another legacy name (array)

/* ──────────────────────────────
   Contacts book (label ↔ topics)
   ────────────────────────────── */
export type Contact = {
  label: string; // "Kevin"
  topics: Partial<Record<GraphKey, string>>; // { personal: "ucs://...", work: "ucs://..." }
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

function normalizeGraph(g: any): GraphKey {
  return g === "work" ? "work" : "personal";
}
function normalizeUses(u: any): number {
  const n = Number(u);
  return Number.isFinite(n) && n > 0 ? n : 0;
}
function normalizeTs(ts: any): number {
  const n = Number(ts);
  return Number.isFinite(n) && n > 0 ? n : Date.now();
}

/* v1 → v2 migration (runs lazily) */
function loadRecentsMap(): Record<string, RecentItem> {
  // Prefer v2 map
  const v2 = loadJSON<Record<string, RecentItem> | null>(RECENTS_V2_KEY, null);
  if (v2 && typeof v2 === "object") {
    // ensure compat fields exist (in case older v2 saved without them)
    const out: Record<string, RecentItem> = {};
    for (const [k, r] of Object.entries(v2)) {
      if (!r?.topic) continue;
      const ts = normalizeTs((r as any).ts ?? (r as any).lastUsedMs);
      const uses = normalizeUses((r as any).uses);
      const graph = normalizeGraph((r as any).graph);
      out[k] = {
        topic: String(r.topic),
        label: r.label ? String(r.label) : undefined,
        graph,
        ts,
        uses,
        lastUsedMs: ts,
      };
    }
    // optionally resave normalized map (safe)
    saveJSON(RECENTS_V2_KEY, out);
    return out;
  }

  // Otherwise migrate from either legacy array key
  const legacyA = loadJSON<any[]>(RECENTS_V1A, []);
  const legacyB = legacyA.length ? [] : loadJSON<any[]>(RECENTS_V1B, []);
  const legacy = legacyA.length ? legacyA : legacyB;

  const map: Record<string, RecentItem> = {};

  if (Array.isArray(legacy) && legacy.length) {
    for (const r of legacy) {
      const graph: GraphKey = normalizeGraph(r.graph ?? r.kg);
      const topic: string = String(r.topic || "").trim();
      if (!topic) continue;

      const ts: number = normalizeTs(r.ts ?? r.lastTs ?? r.lastUsedMs);
      const uses: number = normalizeUses(r.uses);

      const item: RecentItem = {
        topic,
        label: r.label ? String(r.label) : undefined,
        graph,
        ts,
        uses,
        lastUsedMs: ts,
      };

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

/**
 * Remember this WA in recents and update alias store/contact book.
 *
 * IMPORTANT: graph is OPTIONAL for compatibility with call-sites like:
 *   rememberTopic(topic, label)
 */
export function rememberTopic(topic: string, label?: string, graph: GraphKey = "personal") {
  const t = (topic || "").trim();
  if (!t) return;

  const g = normalizeGraph(graph);
  const map = loadRecentsMap();
  const now = Date.now();

  const key = `${g}:${t}`;
  const prev = map[key];

  const nextUses = (prev?.uses ?? 0) + 1;

  const item: RecentItem = {
    topic: t,
    label,
    graph: g,
    ts: now,
    uses: nextUses,
    lastUsedMs: now,
  };

  map[key] = item;

  // keep last 100 by ts
  const entries = Object.values(map).sort((a, b) => b.ts - a.ts).slice(0, 100);
  const next: Record<string, RecentItem> = {};
  for (const it of entries) next[`${it.graph}:${it.topic}`] = it;
  saveRecentsMap(next);

  // WA alias memory (best-known label) to reduce duplicates
  if (label && !label.startsWith("ucs://")) {
    rememberLabel(g, t, label);
  }

  // Also keep the simple contacts mapping for quick lookup
  if (label && !label.startsWith("ucs://")) {
    upsertContact(label, g, t);
  }
}

/**
 * Return most recent topics.
 * NOTE: items include `uses` for UI chips/tooltips.
 */
export function getRecent(limit = 20, graph?: GraphKey): RecentItem[] {
  const all = Object.values(loadRecentsMap()).sort((a, b) => b.ts - a.ts);
  const filtered = graph ? all.filter((r) => r.graph === graph) : all;
  return filtered.slice(0, limit);
}

/* Contacts */
function loadBook(): Record<string, Contact> {
  return loadJSON<Record<string, Contact>>(BOOK_KEY, {});
}
function saveBook(db: Record<string, Contact>) {
  saveJSON(BOOK_KEY, db);
}

/** Upsert a simple label→WA mapping in the address book (legacy helper). */
export function upsertContact(label: string, graph: GraphKey, topic: string) {
  const key = (label || "").trim().toLowerCase();
  if (!key) return;

  const db = loadBook();
  const c: Contact = db[key] || { label, topics: {} };
  c.label = label;
  c.topics[normalizeGraph(graph)] = topic;
  c.updatedAt = Date.now();
  c.uses = (c.uses ?? 0) + 1;
  db[key] = c;
  saveBook(db);
}

export function getContacts(): Contact[] {
  return Object.values(loadBook()).sort((a, b) => (b.updatedAt || 0) - (a.updatedAt || 0));
}

/**
 * Resolve a human address like "kevin" or "kevin@work" to a concrete topic (WA).
 * Falls back to the input if it already looks like a ucs:// topic or
 * there’s no contact match. (Kept for backward compat with older call sites.)
 */
export function resolveHumanAddress(
  input: string,
  preferredGraph: GraphKey = "personal",
): { topic: string; label?: string; graph: GraphKey } {
  const v = (input || "").trim();
  if (!v) return { topic: "", graph: preferredGraph };

  // Already a topic
  if (v.startsWith("ucs://")) return { topic: v, graph: preferredGraph };

  // Allow "label@work" / "label@personal"
  const m = v.match(/^(.+?)@(work|personal)$/i);
  const graph: GraphKey = normalizeGraph(m?.[2]?.toLowerCase());
  const label = (m?.[1] || v).trim();

  const book = loadBook();
  const c = book[label.toLowerCase()];
  if (c?.topics?.[graph]) {
    return { topic: c.topics[graph]!, label: c.label, graph };
  }

  // Fallback: treat the input as a topic if it’s not a known label
  return { topic: v, graph };
}

/* ──────────────────────────────
   Alias helpers (integrate with nameService)
   ────────────────────────────── */

/** Persist best-known label for WA to reduce duplicates across recents. */
export function rememberLabel(kg: GraphKey, wa: string, label: string) {
  try {
    saveBestLabel(kg, wa, label);
  } catch {}
}

/** Retrieve a friendly label for a WA (falls back to prettified WA). */
export function labelForWA(kg: GraphKey, wa: string): string {
  try {
    return getLabelForWA(kg, wa);
  } catch {
    return wa;
  }
}