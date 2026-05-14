-- 010_kg_edge.sql
-- Generic edge table for SENT_BY / ON_TOPIC / IN_THREAD / etc.

CREATE TABLE IF NOT EXISTS kg_edge (
  kg         TEXT NOT NULL,          -- 'personal' | 'work'

  kind       TEXT NOT NULL,          -- 'SENT_BY' | 'ON_TOPIC' | 'IN_THREAD' | ...
  src_type   TEXT NOT NULL,          -- 'message' | 'call' | 'visit' | 'cookie' | ...
  src_id     TEXT NOT NULL,          -- usually kg_events.id or a node id

  dst_type   TEXT NOT NULL,          -- 'agent' | 'topic' | 'thread' | 'file' | ...
  dst_id     TEXT NOT NULL,          -- e.g. agent WA, topic_id, thread_id, file_id

  created_ts INTEGER NOT NULL,       -- when this edge was created

  PRIMARY KEY (kg, kind, src_type, src_id, dst_type, dst_id)
);

-- Fast lookup by target side for graph queries:
CREATE INDEX IF NOT EXISTS idx_edge_dst
  ON kg_edge (kg, kind, dst_type, dst_id, src_type, src_id);