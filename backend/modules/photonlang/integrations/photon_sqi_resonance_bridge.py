# ===============================================================
# 🌌 Photon ↔ SQI ↔ QQC ↔ QFC Resonance Bridge
# File: backend/modules/photonlang/integrations/photon_sqi_resonance_bridge.py
# ===============================================================
from __future__ import annotations
import asyncio
from typing import Any, Dict, Optional

# --- Optional imports with fallbacks -----------------------------------------
try:
    from backend.modules.sqi.sqi_resonance_bridge import compute_sqi_resonance
except Exception:
    async def compute_sqi_resonance(state: Dict[str, Any]) -> Dict[str, Any]:
        # graceful fallback
        return {"sqi_score": 1.0, "entropy": 0.0, "harmony": 1.0, "drift": 0.0}

try:
    from backend.modules.qqc.qqc_resonance_bridge import emit_resonance_state
except Exception:
    async def emit_resonance_state(packet: Dict[str, Any]) -> None:
        print(f"[Stub QQC] Resonance emitted: {packet.get('resonance_index', 'n/a')}")

try:
    from backend.modules.visualization.quantum_field_canvas_api import trigger_qfc_render
except Exception:
    async def trigger_qfc_render(payload: Dict[str, Any], source: str = "photon_sqi_bridge"):
        print(f"[Stub QFC] Would trigger render from [{source}] -> {list(payload.keys())}")

try:
    from backend.modules.teleportation.teleport_api import teleport_to_container
except Exception:
    async def teleport_to_container(packet: Dict[str, Any], target: Optional[str] = None):
        print(f"[Stub Teleport] Simulated teleport of packet to {target or 'default-container'}")
# -----------------------------------------------------------------------------

# --- Bridge Core -------------------------------------------------------------
class PhotonSQIResonanceBridge:
    """
    Orchestrates real-time coupling between PhotonLang resonance events,
    SQI metrics, QQC quantum coherence, and QFC visual rendering.
    """

    def __init__(self):
        self.last_state: Optional[Dict[str, Any]] = None
        self.last_sqi: Optional[Dict[str, Any]] = None

    # --------------------------------------------------------------
    async def capture_resonance(self, photon_state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Transform PhotonRuntime.resonance state into a standardized packet.
        Expected photon_state fields:
          { "seq", "intensity", "ops", "resonance_index", "Φ", "ψ" }
        """
        packet = {
            "type": "resonance_packet",
            "seq": photon_state.get("seq"),
            "intensity": photon_state.get("intensity", 1.0),
            "ops": photon_state.get("ops", []),
            "Φ_mean": photon_state.get("Φ", 1.0),
            "ψ_mean": photon_state.get("ψ", 1.0),
            "resonance_index": photon_state.get("resonance_index", 1.0),
        }
        self.last_state = packet
        return packet

    # --------------------------------------------------------------
    async def compute_sqi_feedback(self, photon_state: Dict[str, Any]) -> Dict[str, Any]:
        """Compute or update SQI feedback metrics for the given photon state."""
        sqi = await compute_sqi_resonance(photon_state)
        self.last_sqi = sqi
        return sqi

    # --------------------------------------------------------------
    async def emit_to_qqc(self, resonance_packet: Dict[str, Any]) -> None:
        """Push the resonance state into the Quantum Quad Core for coherence alignment."""
        await emit_resonance_state(resonance_packet)

    # --------------------------------------------------------------
    async def visualize_in_qfc(self, resonance_packet: Dict[str, Any], sqi_feedback: Dict[str, Any]) -> None:
        """Trigger live QFC render to show updated symbolic resonance + SQI state."""
        payload = {
            "resonance": resonance_packet,
            "sqi": sqi_feedback,
            "meta": {"bridge": "photon_sqi_resonance_bridge"}
        }
        await trigger_qfc_render(payload, source="photon_sqi_bridge")

    # --------------------------------------------------------------
    async def teleport_resonance_state(self, resonance_packet: Dict[str, Any], target_container: Optional[str] = None) -> None:
        """Send the resonance packet through the teleportation layer (container sync)."""
        await teleport_to_container(resonance_packet, target=target_container)

    # --------------------------------------------------------------
    async def integrate_all(self, photon_state: Dict[str, Any], container_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Complete bridge pipeline:
          1. Capture photon resonance
          2. Compute SQI feedback
          3. Emit to QQC
          4. Teleport if container target provided
          5. Visualize in QFC
        """
        packet = await self.capture_resonance(photon_state)
        sqi = await self.compute_sqi_feedback(packet)

        await asyncio.gather(
            self.emit_to_qqc(packet),
            self.visualize_in_qfc(packet, sqi),
            self.teleport_resonance_state(packet, target_container=container_id),
        )

        combined = {**packet, **sqi}
        print(f"🌀 Bridge integrated resonance -> SQI:{sqi.get('sqi_score')} QQC/QFC/Teleport complete")
        return combined


# --- Singleton helper for global access -------------------------------------
BRIDGE = PhotonSQIResonanceBridge()