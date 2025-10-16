# ──────────────────────────────────────────────
#  Tessaris • QQC Repair Manager (F2 — Rollback / SoulLaw)
#  Handles rollback, SoulLaw veto checks, and ψ–κ–T state repair.
#  v0.2 — adds detailed SQI diagnostics + full tensor restoration
# ──────────────────────────────────────────────

import json
import logging
import os
import time
from typing import Dict, Any, Optional, List
from backend.modules.holograms.hst_generator import HSTGenerator
from backend.modules.holograms.morphic_feedback_controller import MorphicFeedbackController

logger = logging.getLogger(__name__)

LEDGER_PATH = "data/ledger/qqc_commit_log.jsonl"
SQI_THRESHOLD = 0.85


class QQCRepairManager:
    """Rollback and repair handler for Quantum Quad Core coherence management."""

    def __init__(self, hst: HSTGenerator):
        self.hst = hst
        self.feedback = MorphicFeedbackController()
        self.last_repair_time: Optional[float] = None
        self.repair_count = 0

    # ──────────────────────────────────────────────
    #  Instability Detection
    # ──────────────────────────────────────────────
    def detect_instability(self, txn: Dict[str, Any]) -> bool:
        """
        Evaluate SQI, ψ–κ divergence, and temporal coherence decay.
        """
        sqi = txn.get("C_total", 0.0)
        holographic = txn.get("holographic_state", {}) or {}

        psi = holographic.get("psi", holographic.get("psi_kappa_T", {}).get("psi", 0.0))
        kappa = holographic.get("kappa", holographic.get("psi_kappa_T", {}).get("kappa", 0.0))
        T = holographic.get("T", holographic.get("psi_kappa_T", {}).get("T", 1.0))

        # Primary SQI check
        if sqi < SQI_THRESHOLD:
            logger.warning(f"[QQCRepair] SQI below threshold ({sqi:.3f} < {SQI_THRESHOLD}) — rollback required.")
            return True

        # ψ–κ divergence check
        if abs(psi - kappa) > 0.5:
            logger.warning(f"[QQCRepair] ψ–κ divergence detected (ψ={psi:.3f}, κ={kappa:.3f})")
            return True

        # Temporal instability check
        if T < 10:
            logger.warning(f"[QQCRepair] Temporal flux instability detected (T={T:.3f})")
            return True

        return False

    # ──────────────────────────────────────────────
    #  SoulLaw Veto (Ethical / Logical Constraints)
    # ──────────────────────────────────────────────
    def apply_soullaw_veto(self, txn: Dict[str, Any]) -> bool:
        """
        Placeholder for SoulLaw (ethical/logical constraint system).
        Prevents field operations that violate cognitive or symbolic integrity.
        """
        meta = txn.get("symbolic_state", {})
        if meta.get("allow_collapse", True) is False:
            reason = meta.get("veto_reason", "disallowed collapse")
            logger.error(f"[SoulLaw] ❌ Veto triggered — {reason}.")
            return True
        return False

    # ──────────────────────────────────────────────
    #  Rollback & Restore
    # ──────────────────────────────────────────────
    def rollback_last_commit(self) -> Optional[Dict[str, Any]]:
        """Revert to last known stable ledger entry."""
        if not os.path.exists(LEDGER_PATH):
            logger.error("[QQCRepair] No ledger found for rollback.")
            return None

        try:
            with open(LEDGER_PATH, "r", encoding="utf-8") as f:
                lines = [json.loads(line) for line in f.readlines() if line.strip()]
        except Exception as e:
            logger.error(f"[QQCRepair] Ledger read failed: {e}")
            return None

        if not lines:
            logger.warning("[QQCRepair] Ledger empty — no state to restore.")
            return None

        # Prefer most recent committed entry with valid ψ–κ–T
        stable_entries = [l for l in lines if "psi_kappa_T" in l.get("psi_kappa_T", {})]
        last_state = stable_entries[-1] if stable_entries else lines[-1]

        ts = last_state.get("timestamp", 0)
        try:
            ts_val = float(ts)
        except Exception:
            ts_val = time.time()
        logger.info(
            f"[QQCRepair] Rolling back to ledger entry "
            f"{last_state.get('runtime_id', 'unknown')} at {time.ctime(ts_val)}"
        )
        return last_state

    def restore_field_state(self, snapshot: Dict[str, Any]):
        """
        Reconstruct holographic field tensor and nodes from ledger snapshot.
        """
        if not snapshot:
            logger.warning("[QQCRepair] No snapshot to restore.")
            return

        self.hst.clear()
        nodes = snapshot.get("morphic_state", {}).get("nodes", [])
        restored = 0

        for n in nodes:
            try:
                self.hst.inject_lightwave_beam(n)
                restored += 1
            except Exception as e:
                logger.warning(f"[QQCRepair] Failed to inject node during rollback: {e}")

        # Recompute ψ–κ–T
        self.hst._update_field_tensor()
        psi_kappa_T = self.hst.field_tensor
        logger.info(
            f"[QQCRepair] Holographic field restored successfully "
            f"({restored} nodes, ψκT={psi_kappa_T})"
        )

    # ──────────────────────────────────────────────
    #  Integrated Repair Cycle
    # ──────────────────────────────────────────────
    def run_repair_cycle(self, txn: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute full rollback + stabilization process.
        Returns a repair status dictionary for QQC telemetry.
        """
        if not txn:
            return {"status": "no_txn", "restored": False}

        # SoulLaw check or instability detection
        if self.apply_soullaw_veto(txn) or self.detect_instability(txn):
            last_stable = self.rollback_last_commit()
            if last_stable:
                self.restore_field_state(last_stable)

                # Reapply ψ–κ–T feedback regulation
                try:
                    self.feedback.regulate(self.hst.field_tensor, list(self.hst.nodes.values()))
                except Exception as e:
                    logger.error(f"[QQCRepair] Feedback stabilization failed: {e}")

                self.repair_count += 1
                self.last_repair_time = time.time()
                logger.info(f"[QQCRepair] ✅ System rolled back and stabilized. (Repairs={self.repair_count})")

                return {
                    "status": "repaired",
                    "restored": True,
                    "repairs": self.repair_count,
                    "timestamp": self.last_repair_time,
                }
            else:
                logger.error("[QQCRepair] ❌ Rollback failed — no stable state found.")
                return {"status": "rollback_failed", "restored": False}
        else:
            logger.debug("[QQCRepair] No repair required — field stable.")
            return {"status": "stable", "restored": False}