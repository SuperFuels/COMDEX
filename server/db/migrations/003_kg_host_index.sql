-- 003_kg_host_index.sql
-- Index visits by host for fast queries
CREATE INDEX IF NOT EXISTS idx_kg_host
ON kg_events (
  kg,
  json_extract(payload,'$.host'),
  ts,
  id
);