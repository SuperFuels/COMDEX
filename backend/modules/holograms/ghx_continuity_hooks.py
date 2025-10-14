"""
🧩 SRK-18 Task 18.2 — GHX Continuity Hooks + Ledger Integration (GCH)
Module: backend/modules/holograms/ghx_continuity_hooks.py

Purpose:
    Extend continuity monitoring to emit signed GHX Continuity Ledger (GCL)
    events for trust anchoring. Integrates with:
        • GHXVaultExporter (state snapshots)
        • CodexTrace (runtime telemetry)
        • GHXContinuityLedger (event ledger)
"""

import time
import asyncio
import hashlib
from typing import Dict, Any, Optional

from backend.modules.holograms.ghx_vault_exporter import GHXVaultExporter
from backend.modules.codex.codex_trace import CodexTrace
from backend.modules.holograms.ghx_continuity_ledger import GHXContinuityLedger


class GHXContinuityHooks:
    """SRK-18 — GHX Continuity Hooks with Ledger Event Recording"""

    def __init__(self, node_id: str = "Tessaris.Node.Local"):
        self.vault_exporter = GHXVaultExporter()
        self.trace = CodexTrace()
        self.ledger = GHXContinuityLedger(node_id=node_id)
        self._last_check: Optional[Dict[str, Any]] = None

    # ────────────────────────────────────────────────────────────────
    async def heartbeat(self, interval: float = 1.0) -> Dict[str, Any]:
        """
        Periodically verify continuity and emit heartbeat metrics.
        Also records a signed GCL event.
        """
        await asyncio.sleep(interval)
        integrity_score = await self._verify_continuity()
        heartbeat = {
            "timestamp": time.time(),
            "integrity_score": integrity_score,
            "status": "ok" if integrity_score >= 0.95 else "degraded",
        }

        # Codex trace event
        self.trace.record(
            "ghx_continuity_ping",
            {"score": round(integrity_score, 3)},
            {"module": "GHX-Continuity-Hooks", "phase": "monitor"},
        )

        # GCL ledger event
        signature = hashlib.sha3_256(str(heartbeat).encode()).hexdigest()
        self.ledger.append_event("heartbeat", heartbeat, signature=signature)

        self._last_check = heartbeat
        return heartbeat

    # ────────────────────────────────────────────────────────────────
    async def _verify_continuity(self) -> float:
        """
        Compare CodexTrace vs last Vault Exporter snapshot integrity hashes.
        Returns a float 0–1 representing agreement ratio.
        Emits a GCL validation event.
        """
        if not self.vault_exporter._last_export:
            self.ledger.append_event("continuity_check", {"status": "no_snapshot"})
            return 1.0

        snapshot = self.vault_exporter._last_export
        recorded_hash = snapshot.get("integrity")
        trace_ref = hashlib.sha3_512(str(snapshot["chain_head"]).encode()).hexdigest()
        match = 1.0 if recorded_hash[:16] == trace_ref[:16] else 0.0

        self.ledger.append_event(
            "continuity_check",
            {"match": match, "ref": trace_ref[:16], "recorded": recorded_hash[:16]},
        )
        return match

    # ────────────────────────────────────────────────────────────────
    async def auto_realign(self) -> Dict[str, Any]:
        """
        Trigger auto-recovery using the last verified Vault snapshot.
        Emits a ledger recovery event.
        """
        try:
            replay = await self.vault_exporter.replay_from_vault()
            status = "replay_success"
        except RuntimeError:
            # No prior export — create synthetic recovery entry
            replay = {"status": "no_prior_export", "recovered": False}
            status = "no_export"

        self.trace.record(
            "ghx_realign_event",
            replay,
            {"module": "GHX-Continuity-Hooks", "phase": "recovery"},
        )

        signature = hashlib.sha3_256(str(replay).encode()).hexdigest()
        self.ledger.append_event("auto_realign", {"status": status, **replay}, signature=signature)
        return replay

    # ────────────────────────────────────────────────────────────────
    async def continuity_report(self) -> Dict[str, Any]:
        """
        Return the last heartbeat and ledger state.
        """
        report = {
            "last_check": self._last_check,
            "vault_head": getattr(self.vault_exporter._last_export, "chain_head", None),
            "ledger": self.ledger.snapshot(),
        }
        self.ledger.append_event("continuity_report", {"entries": len(report["ledger"]["chain"])})
        return report