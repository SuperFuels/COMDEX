# ──────────────────────────────────────────────
#  Tessaris * Morphic Ledger (HQCE Stage 8)
#  Append-only runtime ledger for ψ-κ-T tensors
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


def _truthy_env(name: str, default: str = "") -> bool:
    return os.getenv(name, default).strip().lower() in ("1", "true", "yes", "on")


class MorphicLedger:
    """
    Append-only ledger for storing HQCE field tensor data.
    Compatible with GHXFieldCompiler and QuantumMorphicRuntime.
    Provides runtime query and trend analysis utilities.
    """

    def __init__(self, base_path: str = "data/ledger", use_sqlite: bool = False):
        self.base_path = base_path
        self.use_sqlite = use_sqlite

        # session id still useful for exports / tracing, but we no longer shard JSONL by default
        self.session_id = os.getenv("MORPHIC_LEDGER_SESSION_ID") or f"ledger_{uuid.uuid4().hex[:8]}"
        os.makedirs(self.base_path, exist_ok=True)

        # ✅ Stop creating thousands of shards:
        # - default: write to a single stable file (MORPHIC_LEDGER_FILE)
        # - optional: enable sharding with MORPHIC_LEDGER_SHARD=1
        shard = _truthy_env("MORPHIC_LEDGER_SHARD", "0")
        if shard:
            filename = f"{self.session_id}.jsonl"
        else:
            filename = os.getenv("MORPHIC_LEDGER_FILE", "morphic_ledger.jsonl")

        self.ledger_path = os.path.join(self.base_path, filename)
        self.enable_logging = True  # default for debug + test environments

        # Ensure target file exists
        try:
            os.makedirs(os.path.dirname(self.ledger_path), exist_ok=True)
            if not os.path.exists(self.ledger_path):
                open(self.ledger_path, "a", encoding="utf-8").close()
        except Exception as e:
            logger.warning(f"[MorphicLedger] Could not precreate ledger file: {e}")

        # ── SQLite mode (optional Stage 9+ integration)
        self._db_conn = None
        if self.use_sqlite:
            try:
                import sqlite3
                db_path = os.path.join(self.base_path, "morphic_ledger.db")
                self._db_conn = sqlite3.connect(db_path)
                self._init_sqlite()

                # Add 'link' column if not present
                try:
                    cur = self._db_conn.cursor()
                    cur.execute("ALTER TABLE morphic_records ADD COLUMN link TEXT")
                    self._db_conn.commit()
                    logger.info("[MorphicLedger] Added 'link' column to morphic_records.")
                except sqlite3.OperationalError:
                    # Column may already exist
                    logger.info("[MorphicLedger] SQLite morphic_records already has 'link' column.")

                logger.info("[MorphicLedger] Initialized SQLite ledger backend.")
            except Exception as e:
                logger.warning(f"[MorphicLedger] SQLite unavailable: {e}. Falling back to JSONL.")
                self._db_conn = None

    # ──────────────────────────────────────────────
    #  JSONL Append Path
    # ──────────────────────────────────────────────
    def append(self, tensor_data: Dict[str, Any], observer: Optional[str] = None) -> None:
        """Append a tensor record to the active Morphic Ledger (JSONL + optional SQLite mirror)."""
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
        record["phi"] = tensor_data.get("phi", tensor_data.get("Φ", tensor_data.get("\u03a6", 0.0)))
        record["coherence"] = record["tensor"]["coherence"]

        try:
            # Write to JSONL ledger
            with open(self.ledger_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(record) + "\n")

            # SQLite mirror (if enabled)
            try:
                self._sqlite_insert_record(record)
            except Exception as e:
                logger.warning(f"[MorphicLedger] SQLite insert failed: {e}")

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
                        "Φ": record["phi"],
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

            # 🪶 Mirror Φ-awareness if Φ present
            if record["phi"] not in (None, 0.0):
                self.log_phi_awareness(
                    {
                        "timestamp": record["timestamp"],
                        "Φ": record["phi"],
                        "ψ": record["tensor"]["psi"],
                        "κ": record["tensor"]["kappa"],
                        "T": record["tensor"]["T"],
                        "coherence": record["tensor"]["coherence"],
                    }
                )

        except Exception as e:
            logger.error(f"[MorphicLedger] Failed to append record: {e}")

    # ──────────────────────────────────────────────
    #  Φ-Awareness History Extension (Stage 10)
    # ──────────────────────────────────────────────
    def _init_phi_history_table(self):
        """Ensure the Φ_awareness_history table exists in SQLite."""
        if not self._db_conn:
            return
        cur = self._db_conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS phi_awareness_history (
                id TEXT PRIMARY KEY,
                timestamp REAL,
                phi REAL,
                psi REAL,
                kappa REAL,
                T REAL,
                coherence REAL
            )
        """)
        self._db_conn.commit()
        logger.info("[MorphicLedger] Φ_awareness_history table ready.")

    def log_phi_awareness(self, entry: Dict[str, Any]) -> None:
        """
        Persist Φ-awareness samples to JSONL and (if enabled) SQLite.
        Expected keys: timestamp, Φ, ψ, κ, T, coherence.
        """
        try:
            # JSONL mirror
            aw_path = os.path.join(self.base_path, "phi_awareness_history.jsonl")
            os.makedirs(self.base_path, exist_ok=True)
            with open(aw_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry) + "\n")

            # SQLite persistence (if available)
            if self._db_conn:
                self._init_phi_history_table()
                cur = self._db_conn.cursor()
                cur.execute("""
                    INSERT INTO phi_awareness_history
                    (id, timestamp, phi, psi, kappa, T, coherence)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    f"phi_{uuid.uuid4().hex[:10]}",
                    entry.get("timestamp", time.time()),
                    entry.get("Φ", 0.0),
                    entry.get("ψ", 0.0),
                    entry.get("κ", 0.0),
                    entry.get("T", 0.0),
                    entry.get("coherence", 0.0),
                ))
                self._db_conn.commit()

            logger.info(
                f"[ΦHistory] Logged Φ={entry.get('Φ'):.3f}, ψ={entry.get('ψ'):.3f}, "
                f"κ={entry.get('κ'):.3f}, T={entry.get('T'):.3f}"
            )

            # Mirror to CFA awareness channel
            try:
                CFA.commit(
                    source="MORPHIC_LEDGER",
                    intent="record_phi_awareness",
                    payload=entry,
                    domain="symatics/phi_awareness_history",
                    tags=["Φ", "awareness", "history", "morphic"],
                )
            except Exception as e:
                logger.warning(f"[ΦHistory] CFA mirror failed: {e}")

        except Exception as e:
            logger.warning(f"[ΦHistory] Failed to log Φ-awareness: {e}")

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
                meta TEXT,
                link TEXT
            )
        """)
        self._db_conn.commit()


    def _sqlite_insert_record(self, record: Dict[str, Any]) -> None:
        """Insert a ledger record into SQLite if enabled."""
        if not self._db_conn:
            return
        try:
            cur = self._db_conn.cursor()
            cur.execute(
                """
                INSERT INTO morphic_records
                (id, timestamp, observer, psi, kappa, T, coherence, gradient, stability, meta, link)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record.get("id"),
                    float(record.get("timestamp", time.time())),
                    record.get("observer"),
                    float(record.get("tensor", {}).get("psi", 0.0)),
                    float(record.get("tensor", {}).get("kappa", 0.0)),
                    float(record.get("tensor", {}).get("T", 0.0)),
                    float(record.get("tensor", {}).get("coherence", 0.0)),
                    float(record.get("tensor", {}).get("gradient", 0.0)),
                    float(record.get("tensor", {}).get("stability", 0.0)),
                    json.dumps(record.get("meta", {}) or {}),
                    json.dumps(record.get("link")) if record.get("link") is not None else None,
                ),
            )
            self._db_conn.commit()
        except Exception as e:
            logger.warning(f"[MorphicLedger] SQLite insert failed: {e}")

    # ──────────────────────────────────────────────
    #  Retrieval / Query
    # ──────────────────────────────────────────────
    def query_phi_history(self, limit: int = 100):
        """Retrieve last N Φ-awareness records (JSONL or SQLite)."""
        if self._db_conn:
            cur = self._db_conn.cursor()
            cur.execute(
                "SELECT timestamp, phi, psi, kappa, T, coherence "
                "FROM phi_awareness_history ORDER BY timestamp DESC LIMIT ?",
                (limit,),
            )
            rows = cur.fetchall()
            return [
                {
                    "timestamp": r[0],
                    "Φ": r[1],
                    "ψ": r[2],
                    "κ": r[3],
                    "T": r[4],
                    "coherence": r[5],
                }
                for r in rows
            ]

        # JSONL fallback
        path = os.path.join(self.base_path, "phi_awareness_history.jsonl")
        if not os.path.exists(path):
            return []

        records = []
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                try:
                    rec = json.loads(line)
                    # Normalize escaped Greek keys -> plain symbols
                    norm = {
                        "timestamp": rec.get("timestamp"),
                        "Φ": rec.get("Φ", rec.get("\u03a6")),
                        "ψ": rec.get("ψ", rec.get("\u03c8")),
                        "κ": rec.get("κ", rec.get("\u03ba")),
                        "T": rec.get("T"),
                        "coherence": rec.get("coherence"),
                    }
                    records.append(norm)
                except Exception as e:
                    logger.warning(f"[ΦHistory] Bad JSONL entry: {e}")
        return records[-limit:]

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
        Compute mean & variance of ψ-κ-T-C values over the last N entries.
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

        logger.debug(f"[MorphicLedger] Trend summary -> {summary}")
        return summary

    # ──────────────────────────────────────────────
    #  Φ-Awareness Trend Retrieval & Visualization
    # ──────────────────────────────────────────────
    def get_phi_history(self, limit: int = 1000) -> List[Dict[str, Any]]:
        return self.query_phi_history(limit=limit)

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
            logger.info(f"[MorphicLedger] Exported {len(entries)} records -> {output_path}")
            return output_path
        except Exception as e:
            logger.error(f"[MorphicLedger] Export failed: {e}")
            return ""

    # ──────────────────────────────────────────────
    #  Knowledge-Graph Integration (Stage 12 -> 13)
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
            logger.debug(f"[MorphicLedger] Linked {latest['id']} -> {node_id}")
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
                print(f"[MorphicLedger] 🔄 Global instance path synchronized -> {self.ledger_path}")

        if getattr(self, "enable_logging", True):
            print(f"[MorphicLedger] ⚠️ Path override -> {self.ledger_path}")

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
            print(f"[MorphicLedger] 🧪 Test record appended -> {target}")
        return target

    # ──────────────────────────────────────────────
    #  Φ-Awareness Trend Retrieval & Visualization
    # ──────────────────────────────────────────────
    def get_phi_trend(self, limit: int = 100) -> Dict[str, float]:
        """Compute Φ trend statistics for CodexTrace Narrator."""
        path = os.path.join(self.base_path, "phi_awareness_history.jsonl")
        if not os.path.exists(path):
            logger.warning("[ΦTrend] No history file found.")
            return {"count": 0}

        records = []
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                try:
                    rec = json.loads(line)
                    records.append({
                        "timestamp": rec.get("timestamp"),
                        "Φ": rec.get("Φ", rec.get("\u03a6")),
                        "ψ": rec.get("ψ", rec.get("\u03c8")),
                        "κ": rec.get("κ", rec.get("\u03ba")),
                        "T": rec.get("T"),
                        "coherence": rec.get("coherence"),
                    })
                except Exception as e:
                    logger.warning(f"[ΦTrend] Bad entry: {e}")

        if not records:
            return {"count": 0}

        φ_vals = [r["Φ"] for r in records if r["Φ"] is not None]
        ψ_vals = [r["ψ"] for r in records if r["ψ"] is not None]
        κ_vals = [r["κ"] for r in records if r["κ"] is not None]
        coh_vals = [r["coherence"] for r in records if r["coherence"] is not None]

        φ_mean = sum(φ_vals) / len(φ_vals)
        φ_std = (sum((x - φ_mean) ** 2 for x in φ_vals) / len(φ_vals)) ** 0.5
        stability = 1.0 - φ_std

        stats = {
            "count": len(φ_vals),
            "Φ_mean": φ_mean,
            "Φ_std": φ_std,
            "ψ_mean": sum(ψ_vals) / len(ψ_vals),
            "κ_mean": sum(κ_vals) / len(κ_vals),
            "coherence_mean": sum(coh_vals) / len(coh_vals),
            "stability_index": stability,
            "last_timestamp": records[-1]["timestamp"],
        }

        logger.info(f"[ΦTrend] Φ_mean={φ_mean:.4f}, stability_index={stability:.4f}")
        return stats

    def plot_phi_over_time(self, output_path="data/ledger/phi_trend.png"):
        """Plot Φ awareness evolution over time."""
        import matplotlib.pyplot as plt

        records = []
        path = os.path.join(self.base_path, "phi_awareness_history.jsonl")
        if not os.path.exists(path):
            logger.warning("[ΦPlot] No data file found.")
            return

        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    rec = json.loads(line)
                    records.append({
                        "timestamp": rec.get("timestamp"),
                        "Φ": rec.get("Φ", rec.get("\u03a6")),
                    })

        if not records:
            logger.warning("[ΦPlot] No records found.")
            return

        times = [r["timestamp"] for r in records]
        phi_vals = [r["Φ"] for r in records]

        plt.figure(figsize=(8, 4))
        plt.plot(times, phi_vals, marker="o", linestyle="-")
        plt.title("Φ-Awareness Evolution")
        plt.xlabel("Timestamp")
        plt.ylabel("Φ")
        plt.grid(True)
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        plt.savefig(output_path)
        logger.info(f"[ΦPlot] Saved Φ-awareness trend -> {output_path}")

    # ──────────────────────────────────────────────
    #  Stage 12 * QFC Bridge Synchronization Layer
    # ──────────────────────────────────────────────
    async def broadcast_qfc_update(
        self,
        payload: Dict[str, Any],
        observer_id: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        """Asynchronously broadcast Φ-ψ resonance data to Quantum Field Controller."""
        try:
            import asyncio, json
            await asyncio.sleep(0.01)
            msg = json.dumps({
                "topic": "qfc://resonance/update",
                "payload": payload,
                "observer_id": observer_id or "anonymous",
                "timestamp": time.time(),
            })
            print(f"[QFC↗] Broadcast resonance packet -> {msg[:100]}...")
        except Exception as e:
            logger.warning(f"[QFCBridge] Broadcast failed: {e}")

    def _safe_async(self, coro_func, *args, **kwargs):
        """Run an async coroutine safely, even if no event loop is running."""
        import asyncio
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(coro_func(*args, **kwargs))
        except RuntimeError:
            asyncio.run(coro_func(*args, **kwargs))

    def compute_resonance_coupling(self, window: int = 100) -> Dict[str, Any]:
        """Analyze Φ-ψ coupling and emit live QFC resonance packet."""
        import math, statistics
        entries = self.get_phi_history(window)
        if not entries or len(entries) < 3:
            logger.warning("[ΦΨResonance] Not enough Φ-ψ data points.")
            return {"count": 0}

        Φ_vals = [e.get("Φ", 0.0) for e in entries]
        ψ_vals = [e.get("ψ", 0.0) for e in entries]
        Φ_mean, ψ_mean = statistics.mean(Φ_vals), statistics.mean(ψ_vals)

        num = sum((a - Φ_mean) * (b - ψ_mean) for a, b in zip(Φ_vals, ψ_vals))
        den = math.sqrt(sum((a - Φ_mean)**2 for a in Φ_vals) *
                        sum((b - ψ_mean)**2 for b in ψ_vals))
        correlation = num / den if den else 0.0

        phase_diff = statistics.mean(abs(a - b) for a, b in zip(Φ_vals, ψ_vals))
        resonance_index = max(0.0, min(1.0, (1.0 - phase_diff) * abs(correlation)))

        result = {
            "count": len(Φ_vals),
            "Φ_mean": Φ_mean,
            "ψ_mean": ψ_mean,
            "correlation": correlation,
            "phase_diff": phase_diff,
            "resonance_index": resonance_index,
            "timestamp": entries[-1].get("timestamp"),
        }

        logger.info(f"[ΦΨResonance] r={correlation:.4f}, Δφ={phase_diff:.4f}, R={resonance_index:.4f}")

        # Cognitive Fabric mirror
        try:
            CFA.commit(
                source="MORPHIC_LEDGER",
                intent="phi_psi_resonance",
                payload=result,
                domain="symatics/resonance_coupling",
                tags=["Φψ", "resonance", "coupling", "analysis"],
            )
        except Exception as e:
            logger.warning(f"[ΦΨResonance] CFA commit failed: {e}")

        # 🔊 QFC live bridge
        try:
            self._safe_async(self.broadcast_qfc_update, result)
        except Exception as e:
            logger.warning(f"[ΦΨResonance] Async bridge failed: {e}")

        return result

    def plot_phi_psi_coupling(self, save_path: str = "data/ledger/phi_psi_coupling.png") -> Optional[str]:
        """
        Plot Φ and ψ over time to visualize resonance coupling.
        """
        try:
            import matplotlib.pyplot as plt
            entries = self.get_phi_history(200)
            if not entries:
                logger.warning("[ΦΨPlot] No Φ-ψ history to plot.")
                return None

            t = [e["timestamp"] for e in entries]
            Φ_vals = [e.get("Φ", 0.0) for e in entries]
            ψ_vals = [e.get("ψ", 0.0) for e in entries]

            plt.figure(figsize=(8, 4))
            plt.plot(t, Φ_vals, label="Φ (awareness)", linestyle="-", marker="o")
            plt.plot(t, ψ_vals, label="ψ (wave field)", linestyle="--", marker="x")
            plt.title("Φ-ψ Resonance Coupling Over Time")
            plt.xlabel("Timestamp")
            plt.ylabel("Field Values")
            plt.legend()
            plt.grid(True)
            os.makedirs(os.path.dirname(save_path), exist_ok=True)
            plt.savefig(save_path, dpi=150, bbox_inches="tight")

            logger.info(f"[ΦΨPlot] Saved Φ-ψ resonance plot -> {save_path}")
            return save_path
        except Exception as e:
            logger.error(f"[ΦΨPlot] Failed to generate Φ-ψ plot: {e}")
            return None


# ──────────────────────────────────────────────
#  Singleton instance (used by HQCE runtime)
# ──────────────────────────────────────────────
morphic_ledger = MorphicLedger()