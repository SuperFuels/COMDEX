-- 020_kg_ledger.sql
-- Hash-chained mutation ledger for KG (A58)

CREATE TABLE IF NOT EXISTS kg_ledger (
  kg        TEXT    NOT NULL,          -- 'personal' | 'work'
  seq       INTEGER NOT NULL,          -- monotonic per kg
  ts        INTEGER NOT NULL,          -- ms since epoch
  op_kind   TEXT    NOT NULL,          -- e.g. 'forget', 'upsert_entity'
  op_desc   TEXT    NOT NULL,          -- short description or route
  prev_hash TEXT,                      -- hash of previous entry (same kg)
  hash      TEXT    NOT NULL,          -- hash of {kg, seq, ts, op_kind, op_desc, prev_hash, payload}
  payload   TEXT,                      -- JSON blob with parameters (optional)
  PRIMARY KEY (kg, seq)
);

-- Helpful indexes
CREATE INDEX IF NOT EXISTS idx_kg_ledger_kg_seq_desc
  ON kg_ledger (kg, seq DESC);

CREATE INDEX IF NOT EXISTS idx_kg_ledger_kg_hash
  ON kg_ledger (kg, hash);