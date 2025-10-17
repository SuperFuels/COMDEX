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
from backend.modules.cognitive_fabric.cognitive_fabric_adapter import CFA

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

        # Define the ledger path once
        self.ledger_path = os.path.join(self.base_path, f"{self.session_id}.jsonl")
        self.enable_logging = True  # default for debug + test environments

        # ── SQLite mode (optional Stage 9+ integration)
        self._db_conn = None
        if self.use_sqlite:
            try:
                import sqlite3
                db_path = os.path.join(self.base_path, "morphic_ledger.db")
                self._db_conn = sqlite3.connect(db_path)
                self._init_sqlite()

                # Add 'link' column if not present
                cur = self._db_conn.cursor()
                cur.execute("""ALTER TABLE morphic_records ADD COLUMN link TEXT""")
                self._db_conn.commit()
                logger.info("[MorphicLedger] Initialized SQLite ledger backend with link column.")
            except sqlite3.OperationalError:
                # Column may already exist
                logger.info("[MorphicLedger] SQLite ledger already has 'link' column.")
            except Exception as e:
                logger.warning(f"[MorphicLedger] SQLite unavailable: {e}. Falling back to JSONL.")

        logger.info(f"[MorphicLedger] Session initialized → {self.ledger_path}")

    # ──────────────────────────────────────────────
    #  JSONL Append Path
    # ──────────────────────────────────────────────
    def append(self, tensor_data: Dict[str, Any], observer: Optional[str] = None) -> None:
        """Append a tensor record to the active Morphic Ledger."""
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
            "link": tensor_data.get("link"),
        }

        # 🔁 Flattened aliases (for external tests & analytics)
        record["psi"] = record["tensor"]["psi"]
        record["phi"] = tensor_data.get("phi", tensor_data.get("Φ", 0.0))
        record["coherence"] = record["tensor"]["coherence"]

        try:
            with open(self.ledger_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(record) + "\n")

            logger.debug(
                f"[MorphicLedger] + Appended ψ={record['tensor']['psi']:.3f} "
                f"κ={record['tensor']['kappa']:.3f} C={record['tensor']['coherence']:.3f}"
            )

            # 🔶 Commit to Cognitive Fabric
            try:
                CFA.commit(
                    source="MORPHIC_LEDGER",
                    intent="record_field_state",
                    payload={
                        "ψ": record["tensor"]["psi"],
                        "κ": record["tensor"]["kappa"],
                        "T": record["tensor"]["T"],
                        "Φ": record["phi"],  # include Φ in payload too
                        "C": record["tensor"]["coherence"],
                        "gradient": record["tensor"]["gradient"],
                        "stability": record["tensor"]["stability"],
                        "meta": record.get("meta", {}),
                        "link": record.get("link"),
                    },
                    domain="symatics/morphic_field",
                    tags=["ledger", "ψκTΦ", "morphic", "state", "record"],
                )
            except Exception as e:
                logger.warning(f"[MorphicLedger] CFA commit failed: {e}")

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
        """Append to SQLite backend (future extension)."""
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

    def latest_metrics(self):
        """Return minimal telemetry dict for UI streaming."""
        e = self.query_latest()
        if not e:
            return {}
        t = e["tensor"]
        return {
            "ψ": t["psi"],
            "κ": t["kappa"],
            "T": t["T"],
            "C": t["coherence"],
            "timestamp": e["timestamp"],
            "observer": e["observer"],
        }

    # ──────────────────────────────────────────────
    #  Trend & Summary Analysis
    # ──────────────────────────────────────────────
    def trend_summary(self, window: int = 20) -> Dict[str, Any]:
        """
        Compute mean & variance of ψ–κ–T–C values over the last N entries.
        Useful for runtime dashboards, stability telemetry, and coherence tracking.
        """
        entries = self.load_all()[-window:]
        if not entries:
            return {"count": 0}

        ψ_vals = [e["tensor"]["psi"] for e in entries]
        κ_vals = [e["tensor"]["kappa"] for e in entries]
        C_vals = [e["tensor"]["coherence"] for e in entries]

        ψ_std = statistics.pstdev(ψ_vals) if len(ψ_vals) > 1 else 0
        κ_std = statistics.pstdev(κ_vals) if len(κ_vals) > 1 else 0
        C_std = statistics.pstdev(C_vals) if len(C_vals) > 1 else 0

        summary = {
            "count": len(entries),
            "ψ_mean": statistics.mean(ψ_vals),
            "κ_mean": statistics.mean(κ_vals),
            "C_mean": statistics.mean(C_vals),
            "ψ_std": ψ_std,
            "κ_std": κ_std,
            "C_std": C_std,
            "stability_index": max(0.0, 1 - C_std),
            "last_timestamp": entries[-1]["timestamp"],
        }

        logger.debug(f"[MorphicLedger] Trend summary → {summary}")
        return summary

    # ──────────────────────────────────────────────
    #  Export for Analysis or Dashboard
    # ──────────────────────────────────────────────
    def export_json(self, output_path: Optional[str] = None) -> str:
        """
        Export the full ledger to an external JSON file for GHX dashboard or archival.
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
    #  Knowledge-Graph Integration (Stage 12 → 13)
    # ──────────────────────────────────────────────
    def link_to_graph(self, node_id: str, relation: str = "origin") -> None:
        """
        Attach the most recent record to a knowledge-graph node, establishing symbolic linkage.
        """
        latest = self.query_latest()
        if not latest:
            return

        latest["link"] = {"node_id": node_id, "relation": relation}
        try:
            with open(self.ledger_path, "a", encoding="utf-8") as f:
                f.write(json.dumps({"update_link": latest["id"], "node_id": node_id}) + "\n")
            logger.debug(f"[MorphicLedger] Linked {latest['id']} → {node_id}")
        except Exception as e:
            logger.warning(f"[MorphicLedger] Link write failed: {e}")

    # ──────────────────────────────────────────────
    #  TEST / DEBUG UTILITIES
    # ──────────────────────────────────────────────
    def _override_path(self, new_path: str) -> None:
        """
        Redirects the ledger output path (used only in tests or debug mode).
        """
        if not new_path.endswith(".jsonl"):
            new_path += ".jsonl"

        self.ledger_path = new_path
        self._test_override = True

        # Ensure directory & file exist
        os.makedirs(os.path.dirname(new_path), exist_ok=True)
        if not os.path.exists(new_path):
            open(new_path, "w").close()

        # 🔄 Propagate override to global singleton
        import sys
        mod = sys.modules.get("backend.modules.holograms.morphic_ledger")
        if mod and hasattr(mod, "morphic_ledger"):
            mod.morphic_ledger.ledger_path = self.ledger_path
            mod.morphic_ledger._test_override = True
            if getattr(self, "enable_logging", True):
                print(f"[MorphicLedger] 🔄 Global instance path synchronized → {self.ledger_path}")

        if getattr(self, "enable_logging", True):
            print(f"[MorphicLedger] ⚠️ Path override → {self.ledger_path}")

    def record(self, data: Optional[Dict[str, Any]] = None, path: Optional[str] = None) -> str:
        """
        Simple fallback record stub for testing.
        Writes a lightweight JSON line to the current ledger path.
        """
        target = path or getattr(self, "ledger_path", "/tmp/test_morphic_ledger.jsonl")
        os.makedirs(os.path.dirname(target), exist_ok=True)

        with open(target, "a", encoding="utf-8") as f:
            json.dump(data or {"status": "ok", "message": "ledger entry stub"}, f)
            f.write("\n")

        if getattr(self, "enable_logging", True):
            print(f"[MorphicLedger] 🧪 Test record appended → {target}")
        return target


# ──────────────────────────────────────────────
#  Singleton instance (used by HQCE runtime)
# ──────────────────────────────────────────────
morphic_ledger = MorphicLedger()