# ──────────────────────────────────────────────
#  Tessaris • Morphic Ledger (HQCE Stage 8)
#  Append-only runtime ledger for ψ–κ–T tensors
#  Records coherence, entropy, stability per tick
#  Supports both JSONL and SQLite backends
#  Extended for trend analysis + vault signing
# ──────────────────────────────────────────────

import os
import json
import time
import uuid
import logging
import statistics
from typing import Dict, Any, Optional, List

logger = logging.getLogger(__name__)


class MorphicLedger:
    """
    Append-only ledger for storing HQCE field tensor data.
    Compatible with GHXFieldCompiler and QuantumMorphicRuntime.
    Provides runtime query and trend analysis utilities.
    """

    def __init__(self, base_path: str = "data/ledger", use_sqlite: bool = False):
        self.base_path = base_path
        self.use_sqlite = use_sqlite
        self.session_id = f"ledger_{uuid.uuid4().hex[:8]}"
        os.makedirs(self.base_path, exist_ok=True)
        self.ledger_path = os.path.join(self.base_path, f"{self.session_id}.jsonl")

        # SQLite mode placeholder (future Stage 9)
        self._db_conn = None
        if self.use_sqlite:
            try:
                import sqlite3
                self._db_conn = sqlite3.connect(os.path.join(self.base_path, "morphic_ledger.db"))
                self._init_sqlite()
                logger.info("[MorphicLedger] Initialized SQLite ledger backend.")
            except Exception as e:
                logger.warning(f"[MorphicLedger] SQLite unavailable: {e}. Falling back to JSONL.")

        logger.info(f"[MorphicLedger] Session initialized → {self.ledger_path}")

    # ──────────────────────────────────────────────
    #  JSONL Append Path
    # ──────────────────────────────────────────────
    def append(self, tensor_data: Dict[str, Any], observer: Optional[str] = None) -> None:
        """
        Append a tensor record (ψ, κ, T, C, stability) with metadata.
        """
        record = {
            "id": f"entry_{uuid.uuid4().hex[:10]}",
            "timestamp": time.time(),
            "observer": observer or "HQCE_Runtime",
            "tensor": {
                "psi": tensor_data.get("psi", 0.0),
                "kappa": tensor_data.get("kappa", 0.0),
                "T": tensor_data.get("T", 0.0),
                "coherence": tensor_data.get("coherence", 0.0),
                "gradient": tensor_data.get("gradient", 0.0),
                "stability": tensor_data.get("stability", 0.0),
            },
            "meta": tensor_data.get("metadata", {}),
        }

        try:
            with open(self.ledger_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(record) + "\n")
            logger.debug(
                f"[MorphicLedger] + Appended ψ={record['tensor']['psi']:.3f} "
                f"κ={record['tensor']['kappa']:.3f} C={record['tensor']['coherence']:.3f}"
            )
        except Exception as e:
            logger.error(f"[MorphicLedger] Failed to append record: {e}")

    # ──────────────────────────────────────────────
    #  Optional SQLite Backend (Stage 9)
    # ──────────────────────────────────────────────
    def _init_sqlite(self):
        """Initialize SQLite table for tensor storage."""
        if not self._db_conn:
            return
        cur = self._db_conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS morphic_records (
                id TEXT PRIMARY KEY,
                timestamp REAL,
                observer TEXT,
                psi REAL,
                kappa REAL,
                T REAL,
                coherence REAL,
                gradient REAL,
                stability REAL,
                meta TEXT
            )
        """)
        self._db_conn.commit()

    def append_sqlite(self, tensor_data: Dict[str, Any], observer: Optional[str] = None) -> None:
        """Future: SQLite append mode."""
        if not self._db_conn:
            return
        cur = self._db_conn.cursor()
        cur.execute("""
            INSERT INTO morphic_records VALUES (?,?,?,?,?,?,?,?,?,?)
        """, (
            f"entry_{uuid.uuid4().hex[:10]}",
            time.time(),
            observer or "HQCE_Runtime",
            tensor_data.get("psi", 0.0),
            tensor_data.get("kappa", 0.0),
            tensor_data.get("T", 0.0),
            tensor_data.get("coherence", 0.0),
            tensor_data.get("gradient", 0.0),
            tensor_data.get("stability", 0.0),
            json.dumps(tensor_data.get("metadata", {}))
        ))
        self._db_conn.commit()

    # ──────────────────────────────────────────────
    #  Retrieval / Query
    # ──────────────────────────────────────────────
    def load_all(self) -> List[Dict[str, Any]]:
        """Load all JSONL entries."""
        if not os.path.exists(self.ledger_path):
            return []
        try:
            with open(self.ledger_path, "r", encoding="utf-8") as f:
                return [json.loads(line) for line in f if line.strip()]
        except Exception as e:
            logger.error(f"[MorphicLedger] Failed to read ledger: {e}")
            return []

    def query_latest(self) -> Optional[Dict[str, Any]]:
        """Return the latest ledger entry."""
        entries = self.load_all()
        return entries[-1] if entries else None

    # ──────────────────────────────────────────────
    #  Trend & Summary Analysis
    # ──────────────────────────────────────────────
    def trend_summary(self, window: int = 20) -> Dict[str, Any]:
        """
        Compute mean & variance of ψ–κ–T–C values over last N entries.
        Useful for runtime dashboards and telemetry reports.
        """
        entries = self.load_all()[-window:]
        if not entries:
            return {"count": 0}

        ψ_vals = [e["tensor"]["psi"] for e in entries]
        κ_vals = [e["tensor"]["kappa"] for e in entries]
        C_vals = [e["tensor"]["coherence"] for e in entries]

        summary = {
            "count": len(entries),
            "ψ_mean": statistics.mean(ψ_vals),
            "κ_mean": statistics.mean(κ_vals),
            "C_mean": statistics.mean(C_vals),
            "ψ_std": statistics.pstdev(ψ_vals) if len(ψ_vals) > 1 else 0,
            "C_std": statistics.pstdev(C_vals) if len(C_vals) > 1 else 0,
            "stability_index": 1 - (statistics.pstdev(C_vals) if len(C_vals) > 1 else 0),
            "last_timestamp": entries[-1]["timestamp"],
        }
        logger.debug(f"[MorphicLedger] Trend summary → {summary}")
        return summary

    # ──────────────────────────────────────────────
    #  Export for Analysis or Dashboard
    # ──────────────────────────────────────────────
    def export_json(self, output_path: Optional[str] = None) -> str:
        """
        Export full ledger to an external JSON file for GHX dashboard or archival.
        """
        output_path = output_path or os.path.join(self.base_path, f"{self.session_id}_export.json")
        try:
            entries = self.load_all()
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(entries, f, indent=2)
            logger.info(f"[MorphicLedger] Exported {len(entries)} records → {output_path}")
            return output_path
        except Exception as e:
            logger.error(f"[MorphicLedger] Export failed: {e}")
            return ""

# ──────────────────────────────────────────────
#  Singleton instance (used by HQCE runtime)
# ──────────────────────────────────────────────
morphic_ledger = MorphicLedger()