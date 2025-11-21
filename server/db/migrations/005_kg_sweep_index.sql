-- 005_kg_sweep_index.sql
CREATE INDEX IF NOT EXISTS idx_kg_type_kind_ts
  ON kg_events (kg, type, IFNULL(kind,''), ts);