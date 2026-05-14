# ──────────────────────────────────────────────
#  Tessaris * HQCE Telemetry Database (Stage 10)
#  Persistent store for ψ-κ-T-C metrics
#  Supports trend queries and dashboard integration
# ──────────────────────────────────────────────

import os
import json
import time
import sqlite3
import logging
from typing import Dict, Any, List, Optional, Tuple

logger = logging.getLogger(__name__)


class HQCETelemetryDB:
    """Persistent telemetry store for HQCE field tensor data."""

    def __init__(self, db_path: str = "data/ledger/hqce_telemetry.db"):
        self.db_path = db_path
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self.conn = sqlite3.connect(self.db_path)
        self._init_schema()

    # ──────────────────────────────────────────────
    #  Schema
    # ──────────────────────────────────────────────
    def _init_schema(self):
        cur = self.conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS telemetry (
                id TEXT PRIMARY KEY,
                timestamp REAL,
                session_id TEXT,
                observer TEXT,
                psi REAL,
                kappa REAL,
                T REAL,
                coherence REAL,
                stability REAL,
                meta TEXT
            );
        """)
        cur.execute("CREATE INDEX IF NOT EXISTS idx_time ON telemetry(timestamp);")
        self.conn.commit()
        logger.info("[HQCETelemetryDB] Schema initialized.")

    # ──────────────────────────────────────────────
    #  Ingestion
    # ──────────────────────────────────────────────
    def ingest_record(self, record: Dict[str, Any], session_id: str) -> None:
        """Insert a telemetry record (from MorphicLedger)."""
        try:
            t = record.get("tensor", {})
            cur = self.conn.cursor()
            cur.execute("""
                INSERT INTO telemetry VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                record.get("id"),
                record.get("timestamp", time.time()),
                session_id,
                record.get("observer", "HQCE_Runtime"),
                t.get("psi", 0.0),
                t.get("kappa", 0.0),
                t.get("T", 0.0),
                t.get("coherence", 0.0),
                t.get("stability", 0.0),
                json.dumps(record.get("meta", {}))
            ))
            self.conn.commit()
        except sqlite3.IntegrityError:
            logger.debug(f"[HQCETelemetryDB] Duplicate record skipped: {record.get('id')}")
        except Exception as e:
            logger.error(f"[HQCETelemetryDB] Ingestion failed: {e}")

    def bulk_ingest_jsonl(self, path: str, session_id: Optional[str] = None) -> int:
        """Load MorphicLedger JSONL file into the DB."""
        if not os.path.exists(path):
            logger.warning(f"[HQCETelemetryDB] Ledger not found: {path}")
            return 0

        session_id = session_id or f"session_{int(time.time())}"
        count = 0
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    rec = json.loads(line)
                    rec.setdefault("id", f"entry_{time.time_ns()}")
                    self.ingest_record(rec, session_id)
                    count += 1
                except json.JSONDecodeError:
                    continue
        logger.info(f"[HQCETelemetryDB] Imported {count} records from {path}")
        return count

    # ──────────────────────────────────────────────
    #  Query API
    # ──────────────────────────────────────────────
    def query_range(self, start: float, end: float) -> List[Dict[str, Any]]:
        """Return all telemetry between timestamps."""
        cur = self.conn.cursor()
        cur.execute("SELECT * FROM telemetry WHERE timestamp BETWEEN ? AND ? ORDER BY timestamp ASC", (start, end))
        rows = cur.fetchall()
        return [self._row_to_dict(r) for r in rows]

    def latest_values(self, limit: int = 20) -> List[Dict[str, Any]]:
        cur = self.conn.cursor()
        cur.execute("SELECT * FROM telemetry ORDER BY timestamp DESC LIMIT ?", (limit,))
        rows = cur.fetchall()
        return [self._row_to_dict(r) for r in rows]

    def summary(self) -> Dict[str, Any]:
        """Return aggregate metrics (mean ψ, κ, coherence, stability)."""
        cur = self.conn.cursor()
        cur.execute("""
            SELECT AVG(psi), AVG(kappa), AVG(coherence), AVG(stability)
            FROM telemetry
        """)
        ψ, κ, C, S = cur.fetchone()
        return {"ψ_mean": ψ or 0, "κ_mean": κ or 0, "C_mean": C or 0, "stability_mean": S or 0}

    def coherence_trend(self, limit: int = 100) -> List[Tuple[float, float]]:
        """Return timestamp -> coherence pairs for visualization."""
        cur = self.conn.cursor()
        cur.execute("SELECT timestamp, coherence FROM telemetry ORDER BY timestamp DESC LIMIT ?", (limit,))
        return cur.fetchall()

    # ──────────────────────────────────────────────
    #  Export
    # ──────────────────────────────────────────────
    def export_json(self, path: str = "data/ledger/hqce_telemetry_export.json") -> str:
        cur = self.conn.cursor()
        cur.execute("SELECT * FROM telemetry ORDER BY timestamp ASC")
        data = [self._row_to_dict(r) for r in cur.fetchall()]
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        logger.info(f"[HQCETelemetryDB] Exported {len(data)} entries -> {path}")
        return path

    # ──────────────────────────────────────────────
    #  Helpers
    # ──────────────────────────────────────────────
    @staticmethod
    def _row_to_dict(row: Tuple) -> Dict[str, Any]:
        return {
            "id": row[0],
            "timestamp": row[1],
            "session_id": row[2],
            "observer": row[3],
            "psi": row[4],
            "kappa": row[5],
            "T": row[6],
            "coherence": row[7],
            "stability": row[8],
            "meta": json.loads(row[9]) if row[9] else {},
        }


# ──────────────────────────────────────────────
#  Singleton instance (used by HQCE Dashboard)
# ──────────────────────────────────────────────
hqce_telemetry_db = HQCETelemetryDB()