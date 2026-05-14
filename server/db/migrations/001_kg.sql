-- kg schema v1 (unchanged)
CREATE TABLE IF NOT EXISTS kg_events (
  id         TEXT PRIMARY KEY,         -- snowflake/uuid
  kg         TEXT NOT NULL,            -- 'personal' | 'work'
  owner_wa   TEXT NOT NULL,            -- e.g., 'kevin@wave.tp'
  thread_id  TEXT,                     -- stable synthetic for (kg, topic)
  topic_wa   TEXT,                     -- human-ish topic (ucs://... or handle)
  type       TEXT NOT NULL,            -- 'message'|'visit'|'file'|'call'|'ptt_session'|'floor_lock'
  kind       TEXT,                     -- subtype: 'text'|'voice'|'mail'|...
  ts         INTEGER NOT NULL,         -- ms epoch
  size       INTEGER,                  -- optional size bytes
  sha256     TEXT,                     -- for files/attachments
  payload    TEXT NOT NULL             -- compact JSON blob (stringified)
);

-- General-purpose indexes you already had
CREATE INDEX IF NOT EXISTS idx_kg_thread_ts ON kg_events (kg, thread_id, ts, id);
-- Replace the older (kg, topic_wa) with a cursor-friendly version:
DROP INDEX IF EXISTS idx_kg_topicwa;
CREATE INDEX IF NOT EXISTS idx_kg_topic_ts ON kg_events (kg, topic_wa, ts, id);
CREATE INDEX IF NOT EXISTS idx_kg_sha       ON kg_events (kg, sha256);

-- ── Visits-focused indexes (accelerate A52/A56/A55 and host rollups) ─────────

-- 1) Fast per-thread visit pagination (matches /api/kg/view/visits where type='visit')
CREATE INDEX IF NOT EXISTS idx_visit_thread_ts
  ON kg_events (kg, thread_id, ts, id)
  WHERE type='visit';

-- 2) Fast per-topic_wa visit pagination (when caller uses topic_wa instead of thread_id)
CREATE INDEX IF NOT EXISTS idx_visit_topic_ts
  ON kg_events (kg, topic_wa, ts, id)
  WHERE type='visit';

-- 3) Host lookups/retention filters (used by forget + analytics)
--    Prefix (kg, host) optimizes GROUP BY host and DELETE with host filter,
--    and (ts,id) suffix helps time-bounded sweeps.
CREATE INDEX IF NOT EXISTS idx_visit_host_ts
  ON kg_events (
    kg,
    json_extract(payload,'$.host'),
    ts,
    id
  )
  WHERE type='visit';

-- 4) Optional: host+uri rollups (if you frequently drill to per-URI stats)
CREATE INDEX IF NOT EXISTS idx_visit_host_uri_ts
  ON kg_events (
    kg,
    json_extract(payload,'$.host'),
    json_extract(payload,'$.uri'),
    ts,
    id
  )
  WHERE type='visit';

-- ────────────────────────────────────────────────────────────
-- Topics (A7): WA + optional WN per graph
-- ────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS kg_topic (
  kg            TEXT NOT NULL,               -- 'personal' | 'work'
  topic_wa      TEXT NOT NULL,               -- canonical WA (e.g. 'ucs://wave.tp/dave@personal')
  topic_wn      TEXT,                        -- Wave Number (phone-style id), optional
  topic_id      TEXT NOT NULL,               -- 'topic:' || lower(topic_wa)
  label         TEXT,                        -- human label: 'Dave Ross', 'UCS Hub'
  realm         TEXT,                        -- 'personal' | 'work' | future 'org:...' etc.
  created_ts    INTEGER NOT NULL,            -- when KG first saw this topic
  updated_ts    INTEGER NOT NULL,            -- last update to label/realm

  PRIMARY KEY (kg, topic_id)
);

-- Unique per WA within a graph
CREATE UNIQUE INDEX IF NOT EXISTS idx_topic_kg_wa
  ON kg_topic(kg, topic_wa);

-- Unique per WN within a graph (when present)
CREATE UNIQUE INDEX IF NOT EXISTS idx_topic_kg_wn
  ON kg_topic(kg, topic_wn)
  WHERE topic_wn IS NOT NULL;