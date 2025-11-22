-- 007_kg_thread.sql
-- Thread entities: one row per (kg, thread_id)

CREATE TABLE IF NOT EXISTS kg_thread (
  -- logical partition
  kg            TEXT NOT NULL,               -- 'personal' | 'work'

  -- identity
  thread_id     TEXT NOT NULL,               -- 'kg:{kg}:{topic_wa}' (A84)
  topic_wa      TEXT NOT NULL,               -- canonical WA for this thread
  topic_wn      TEXT,                        -- optional Wave Number for this topic

  -- lifecycle / aggregates
  created_ts    INTEGER NOT NULL,            -- first time KG saw this thread
  updated_ts    INTEGER NOT NULL,            -- last update to this row
  last_event_ts INTEGER,                     -- ts of last event seen in this thread

  -- future: message_count, last_kind, etc.

  PRIMARY KEY (kg, thread_id)
);

-- Fast lookups by topic WA
CREATE INDEX IF NOT EXISTS idx_thread_kg_topic
  ON kg_thread(kg, topic_wa);

-- Optional: look up thread by WN (if set)
CREATE INDEX IF NOT EXISTS idx_thread_kg_wn
  ON kg_thread(kg, topic_wn)
  WHERE topic_wn IS NOT NULL;