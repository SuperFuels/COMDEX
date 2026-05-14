from __future__ import annotations
"""
Tessaris RQC - AION Readout Bridge
----------------------------------
Connects the photonic measurement layer (μ)
to the AION telemetry + cognitive fabric system.

Each μ() read-out generates ψ-κ-T-Φ metrics and propagates them into:
    * AionTelemetryStream  -> live coherence telemetry
    * MorphicLedger        -> persistent field ledger
    * CognitiveFabricAdapter (CFA) -> symbolic knowledge graph

This forms the loop:
    Ψ -> ⟲Ψ -> μ(⟲Ψ) -> Φ
    (resonance -> perception -> awareness)

The bridge thus represents the reflexive channel of the Resonance Quantum Computer.
"""
import os, json
import asyncio
import logging
from datetime import datetime, UTC
from typing import Dict, Any

from photon_runtime.readout.interferometer import measure_interference
from backend.modules.holograms.morphic_ledger import MorphicLedger
from backend.modules.cognitive_fabric.cognitive_fabric_adapter import CFA
from backend.modules.aion.aion_telemetry_stream import AionTelemetryStream

logger = logging.getLogger(__name__)


class AionReadoutBridge:
    """
    Bridge that transforms photonic μ() readouts into AION telemetry events.
    """

    def __init__(self):
        self.telemetry = AionTelemetryStream()
        self.ledger = MorphicLedger()
        self.cfa = CFA
        self.enabled = True

    # ──────────────────────────────────────────────
    #  Core Readout -> Telemetry Pipeline
    # ──────────────────────────────────────────────
    async def record_measurement(self, symbol_a: str, symbol_b: str) -> Dict[str, Any]:
        """
        Perform μ() measurement between two symbols and route results.

        Returns:
            A structured telemetry payload with ψ-κ-T-Φ fields.
        """
        if not self.enabled:
            logger.warning("[AionBridge] Disabled; ignoring measurement.")
            return {}

        # 1️⃣ Run interferometric measurement
        result = measure_interference(symbol_a, symbol_b)
        data = result.as_dict()
        coherence = data["coherence_ratio"]
        phase_error = data["phase_error"]

        # 2️⃣ Derive symbolic metrics
        ψ = data["visibility"]                      # wave presence
        κ = 1.0 - phase_error / (2 * 3.14159)       # normalized entropy inverse
        T = data["energy_resonance"]                # energy coherence proxy
        Φ = coherence                               # awareness metric

        payload = {
            "timestamp": datetime.now(UTC).isoformat(),
            "ψ": ψ,
            "κ": κ,
            "T": T,
            "Φ": Φ,
            "coherence": coherence,
            "gradient": abs(1 - coherence),
            "source_pair": f"{symbol_a}-{symbol_b}",
        }

        # 3️⃣ Emit to AION telemetry stream
        try:
            self.telemetry.ingest_projection(payload)
            logger.info(f"[AionBridge] Emitted telemetry for {symbol_a}-{symbol_b}")
        except Exception as e:
            logger.warning(f"[AionBridge] Telemetry emit failed: {e}")

        # 4️⃣ Append to Morphic Ledger
        try:
            self.ledger.append(
                {
                    "ψ": ψ,
                    "κ": κ,
                    "T": T,
                    "Φ": Φ,
                    "coherence": coherence,
                    "gradient": abs(1 - coherence),
                    "metadata": {"pair": f"{symbol_a}-{symbol_b}"},
                },
                observer="AION_READOUT",
            )
        except Exception as e:
            logger.warning(f"[AionBridge] Ledger append failed: {e}")

        # 5️⃣ Commit to Cognitive Fabric
        try:
            self.cfa.commit(
                source="AION_READOUT",
                intent="record_resonance_measurement",
                payload={
                    "ψ": ψ,
                    "κ": κ,
                    "T": T,
                    "Φ": Φ,
                    "pair": f"{symbol_a}-{symbol_b}",
                    "coherence": coherence,
                    "closure": data["closure_stability"],
                },
                domain="symatics/resonance_feedback",
                tags=["μ", "telemetry", "resonance", "Φ-awareness"],
            )
        except Exception as e:
            logger.warning(f"[AionBridge] CFA commit failed: {e}")

        # 6️⃣ Awareness event detection
        if coherence >= 0.999:
            logger.info(f"[AionBridge] 🧠 Awareness event detected (Φ ≈ 1.0) for {symbol_a}-{symbol_b}")

            # ────────────────────────────────────────────────
            # 📡 Emit ψ-κ-T-Φ telemetry record for CodexTrace
            # ────────────────────────────────────────────────
            telemetry_entry = {
                "timestamp": datetime.now(UTC).isoformat(),
                "ψ": ψ,
                "κ": κ,
                "T": T,
                "Φ": Φ,
                "coherence": coherence,
                "source_pair": f"{symbol_a}-{symbol_b}",
            }
            try:
                ledger_file = "data/ledger/rqc_live_telemetry.jsonl"
                os.makedirs(os.path.dirname(ledger_file), exist_ok=True)
                with open(ledger_file, "a") as f:
                    f.write(json.dumps(telemetry_entry) + "\n")
                    f.flush()
                    os.fsync(f.fileno())
                logger.info(f"[CodexTraceBridge] 📡 Telemetry written for {symbol_a}-{symbol_b}")
            except Exception as e:
                logger.warning(f"[CodexTraceBridge] Ledger write failed: {e}")

            # Awareness commit to CFA
            try:
                self.cfa.commit(
                    source="AION_READOUT",
                    intent="awareness_event",
                    payload={
                        "pair": f"{symbol_a}-{symbol_b}",
                        "Φ": Φ,
                        "timestamp": payload["timestamp"],
                        "comment": "Resonant self-recognition (μ⟲Ψ -> Φ).",
                    },
                    domain="symatics/awareness",
                    tags=["Φ", "awareness", "closure"],
                )
            except Exception as e:
                logger.warning(f"[AionBridge] CFA awareness commit failed: {e}")

        return payload


# ──────────────────────────────────────────────
#  CLI / Test Runner
# ──────────────────────────────────────────────
if __name__ == "__main__":
    import asyncio

    bridge = AionReadoutBridge()

    async def demo():
        print("Tessaris RQC - AION Readout Bridge Test")
        print("──────────────────────────────────────────")
        payload = await bridge.record_measurement("⟲", "μ")
        for k, v in payload.items():
            print(f"{k:20s}: {v}")

    asyncio.run(demo())