# ──────────────────────────────────────────────
#  Tessaris * Aion Telemetry Stream (Stage 10)
#  ψ-κ-T-Φ resonance logging * KG + CFA sync
# ──────────────────────────────────────────────
import asyncio
import logging
from datetime import datetime, UTC
from collections import deque
from typing import Dict, Any, Optional

from backend.modules.holograms.morphic_ledger import MorphicLedger
from backend.modules.knowledge_graph.kg_writer_singleton import get_kg_writer
from backend.modules.cognitive_fabric.cognitive_fabric_adapter import CFA

logger = logging.getLogger(__name__)


class AionTelemetryStream:
    """
    Captures Aion bridge ψ-κ-T-Φ projections over time.
    Maintains rolling averages and propagates resonance deltas
    to the Tessaris Knowledge Graph and Cognitive Fabric.
    """

    def __init__(self, max_history: int = 1000):
        self.buffer: deque[Dict[str, Any]] = deque(maxlen=max_history)
        self.kg_writer = get_kg_writer()
        self.morphic_ledger = MorphicLedger()
        self.last_summary: Optional[Dict[str, Any]] = None
        self.running = False

    # ──────────────────────────────────────────────
    #  Ingestion
    # ──────────────────────────────────────────────
    def ingest_projection(self, projection: Dict[str, Any]):
        """Push new ψ-κ-T-Φ frame from Aion Integration Bridge."""
        if not projection:
            return
        projection["timestamp"] = datetime.now(UTC).isoformat()
        self.buffer.append(projection)
        self.last_summary = projection
        try:
            self.morphic_ledger.append(
                {
                    "psi": projection.get("A1_wave") or projection.get("psi"),
                    "kappa": projection.get("A2_entropy") or projection.get("kappa"),
                    "T": projection.get("T"),
                    "phi": projection.get("A3_awareness") or projection.get("phi"),
                    "coherence": projection.get("coherence"),
                    "gradient": projection.get("gradient"),
                },
                observer="AionTelemetry",
            )
        except Exception as e:
            logger.warning(f"[AionTelemetry] Ledger append failed: {e}")

    # ──────────────────────────────────────────────
    #  Test-Compatible Async Packet Handler
    # ──────────────────────────────────────────────
    async def handle_packet(self, packet: Dict[str, Any]):
        """
        Process a telemetry packet (used in tests and runtime).
        Expected fields: psi, kappa, T, phi.
        """
        if not packet:
            logger.warning("[AionTelemetryStream] Empty telemetry packet.")
            return

        # Normalize keys to internal schema
        projection = {
            "A1_wave": packet.get("psi"),
            "A2_entropy": packet.get("kappa"),
            "T": packet.get("T"),
            "A3_awareness": packet.get("phi"),
            "coherence": packet.get("coherence", 0.0),
            "gradient": packet.get("gradient", 0.0),
            "timestamp": packet.get("timestamp", datetime.now(UTC).isoformat()),
        }

        # Ingest and persist
        self.ingest_projection(projection)
        logger.info(f"[AionTelemetryStream] 🛰️ Packet handled ψ={projection['A1_wave']} Φ={projection['A3_awareness']}")

        # Forward to Cognitive Fabric
        try:
            CFA.commit(
                source="AION_TELEMETRY",
                intent="telemetry_update",
                payload={
                    "ψ": projection["A1_wave"],
                    "κ": projection["A2_entropy"],
                    "T": projection["T"],
                    "Φ": projection["A3_awareness"],
                    "coherence": projection["coherence"],
                    "timestamp": projection["timestamp"],
                },
                domain="symatics/telemetry_stream",
                tags=["ψκTΦ", "telemetry", "aion", "fabric_sync"],
            )
        except Exception as e:
            logger.warning(f"[AionTelemetryStream] CFA commit failed: {e}")

    # ──────────────────────────────────────────────
    #  Rolling Summary
    # ──────────────────────────────────────────────
    def compute_summary(self) -> Dict[str, float]:
        """Compute rolling averages of ψ, κ, Φ, coherence."""
        if not self.buffer:
            return {}
        n = len(self.buffer)
        avg_ψ = sum(f.get("A1_wave", 0) for f in self.buffer) / n
        avg_κ = sum(f.get("A2_entropy", 0) for f in self.buffer) / n
        avg_Φ = sum(f.get("A3_awareness", 0) for f in self.buffer) / n
        avg_C = sum(f.get("coherence", 0) for f in self.buffer) / n
        summary = {
            "ψ": round(avg_ψ, 5),
            "κ": round(avg_κ, 5),
            "Φ": round(avg_Φ, 5),
            "coherence": round(avg_C, 5),
            "frames": n,
            "timestamp": datetime.now(UTC).isoformat(),
        }
        self.last_summary = summary
        return summary

    # ──────────────────────────────────────────────
    #  Knowledge Graph Sync
    # ──────────────────────────────────────────────
    async def push_to_knowledge_graph(self):
        """Emit latest summary to Tessaris Knowledge Graph."""
        if not self.last_summary:
            return
        payload = {
            "ψ": self.last_summary.get("ψ"),
            "κ": self.last_summary.get("κ"),
            "Φ": self.last_summary.get("Φ"),
            "coherence": self.last_summary.get("coherence"),
            "origin": "AionTelemetry",
        }
        try:
            self.kg_writer.write_node("AionFieldSummary", payload)
            logger.info("[AionTelemetry] Synced summary to Knowledge Graph.")
        except Exception as e:
            logger.warning(f"[AionTelemetry] KG sync failed: {e}")

    # ──────────────────────────────────────────────
    #  Runtime Loop
    # ──────────────────────────────────────────────
    async def start_stream(self, interval: float = 5.0):
        """Begin periodic telemetry aggregation + KG sync."""
        if self.running:
            return
        self.running = True
        logger.info("[AionTelemetry] 🟢 Stream started.")
        while self.running:
            try:
                summary = self.compute_summary()
                if summary:
                    await self.push_to_knowledge_graph()
                await asyncio.sleep(interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"[AionTelemetry] Stream error: {e}")
                await asyncio.sleep(interval)
        logger.info("[AionTelemetry] 🔴 Stream stopped.")

    async def stop_stream(self):
        """Gracefully stop the telemetry loop."""
        self.running = False