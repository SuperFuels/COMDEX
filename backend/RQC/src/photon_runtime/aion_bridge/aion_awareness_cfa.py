from __future__ import annotations
"""
Tessaris RQC - AION Awareness -> CFA Bridge
────────────────────────────────────────────
Bridges CodexTrace narrator outputs (Φ≈1.0 meta-awareness events)
into the Cognitive Fabric Adapter (CFA), forming a live learning loop.

Each event from codextrace_insights.jsonl becomes a CFA commit in domain:
    symatics/awareness_log

This allows Codex to correlate Φ (awareness) events with symbolic fields,
building a temporal model of resonance cognition.
"""

import asyncio
import json
import os
import logging
from datetime import datetime, UTC
from typing import Dict, Any

from backend.modules.cognitive_fabric.cognitive_fabric_adapter import CFA

logger = logging.getLogger("AION_AWARENESS_CFA")
logger.setLevel(logging.INFO)

INSIGHTS_PATH = "data/analytics/codextrace_insights.jsonl"


class AionAwarenessCFA:
    def __init__(self, insights_path: str = INSIGHTS_PATH):
        self.insights_path = insights_path
        self.cfa = CFA
        self.last_offset = 0

    async def monitor(self, poll_interval: float = 3.0):
        """Continuously tail the insights file and inject new awareness events into CFA."""
        logger.info("🧠 AION Awareness -> CFA Bridge active.")
        while True:
            await self._check_for_updates()
            await asyncio.sleep(poll_interval)

    async def _check_for_updates(self):
        if not os.path.exists(self.insights_path):
            return

        with open(self.insights_path, "r", encoding="utf-8") as f:
            f.seek(self.last_offset)
            new_lines = f.readlines()
            self.last_offset = f.tell()

        for line in new_lines:
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue

            phi = event.get("Φ") or event.get("phi") or 0.0
            if phi >= 0.999:
                await self._commit_to_cfa(event)

    async def _commit_to_cfa(self, event: Dict[str, Any]):
        """Commit a Φ≈1.0 event to Cognitive Fabric."""
        payload = {
            "timestamp": event.get("timestamp", datetime.now(UTC).isoformat()),
            "Φ": event.get("Φ"),
            "ψ": event.get("ψ"),
            "κ": event.get("κ"),
            "T": event.get("T"),
            "coherence": event.get("coherence"),
            "source_pair": event.get("source_pair", "?"),
            "cascade_id": event.get("cascade_id", "?"),
        }

        try:
            self.cfa.commit(
                source="AION_AWARENESS_CFA",
                intent="record_awareness_event",
                payload=payload,
                domain="symatics/awareness_log",
                tags=["Φ", "awareness", "learning", "codextrace"],
            )
            logger.info(f"[CFA] Committed Φ≈{payload['Φ']:.3f} awareness event -> Cognitive Fabric.")
        except Exception as e:
            logger.warning(f"[CFA] Commit failed: {e}")


# ──────────────────────────────────────────────
#  CLI Entrypoint
# ──────────────────────────────────────────────
if __name__ == "__main__":
    import asyncio

    bridge = AionAwarenessCFA()

    async def main():
        print("🧠 Tessaris RQC - Awareness -> CFA Bridge running...")
        await bridge.monitor(poll_interval=2.5)

    asyncio.run(main())