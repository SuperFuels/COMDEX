-- 006_kg_topic.sql
-- Topic entities: one row per (kg, topic_wa), optional WN

CREATE TABLE IF NOT EXISTS kg_topic (
  -- logical partition
  kg            TEXT NOT NULL,               -- 'personal' | 'work'

  -- identity
  topic_wa      TEXT NOT NULL,               -- canonical Wave Address (e.g. 'ucs://wave.tp/dave@personal')
  topic_wn      TEXT,                        -- Wave Number (E.164-ish, your “phone” number), optional

  topic_id      TEXT NOT NULL,               -- synthetic id, e.g. 'topic:' || lower(topic_wa)

  -- presentation / grouping
  label         TEXT,                        -- human label: 'Dave Ross', 'UCS Hub'
  realm         TEXT,                        -- 'personal' | 'work' | 'org:...' later

  created_ts    INTEGER NOT NULL,            -- first time KG saw this topic
  updated_ts    INTEGER NOT NULL,            -- last updated (label/realm/wn/wa changes)

  PRIMARY KEY (kg, topic_id)
);

-- Fast lookup by WA
CREATE UNIQUE INDEX IF NOT EXISTS idx_topic_kg_wa
  ON kg_topic(kg, topic_wa);

-- Optional: fast lookup by WN (if you expect reverse-phone lookups)
-- Ensure WN is unique per kg when present
CREATE UNIQUE INDEX IF NOT EXISTS idx_topic_kg_wn
  ON kg_topic(kg, topic_wn)
  WHERE topic_wn IS NOT NULL;