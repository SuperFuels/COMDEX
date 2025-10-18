# ──────────────────────────────────────────────
#  Tessaris • Morphic Holograms Overlay
#  Stage 13.1 — Φ–ψ Resonance Coupling Stream Bridge
#  Connects Morphic Ledger ↔ GHXVisualizer (via CFA telemetry)
# ──────────────────────────────────────────────

import time
import logging
from backend.modules.holograms.morphic_ledger import morphic_ledger
from backend.modules.cognitive_fabric.cognitive_fabric_adapter import CFA

logger = logging.getLogger(__name__)

OVERLAY_ID = "overlay_phi_psi_resonance"


def get_overlay_metadata():
    """Return overlay manifest for GHXVisualizer registration."""
    return {
        "id": OVERLAY_ID,
        "name": "Φ–ψ Resonance Coupling",
        "category": "Symatics Telemetry",
        "version": "1.0",
        "refresh_interval": 3.0,
        "data_source": "symatics/resonance_coupling",
    }


def fetch_live_resonance_data():
    """
    Retrieve Φ–ψ coupling metrics from Morphic Ledger.
    Push data to CFA bus for GHXVisualizer overlay updates.
    """
    try:
        result = morphic_ledger.compute_resonance_coupling()
        if not result or result.get("count", 0) == 0:
            logger.warning("[ΦψOverlay] No Φ–ψ resonance data yet.")
            return {}

        packet = {
            "overlay_id": OVERLAY_ID,
            "timestamp": time.time(),
            "Φ_mean": result.get("Φ_mean"),
            "ψ_mean": result.get("ψ_mean"),
            "correlation": result.get("correlation"),
            "phase_diff": result.get("phase_diff"),
            "resonance_index": result.get("resonance_index"),
            "stability_index": result.get("resonance_index"),
        }

        # 🔁 Publish to Cognitive Fabric → GHXVisualizer domain
        CFA.commit(
            source="MORPHIC_OVERLAY",
            intent="overlay_update",
            payload=packet,
            domain="symatics/resonance_coupling",
            tags=["Φψ", "overlay", "resonance", "telemetry"],
        )

        logger.info(
            f"[ΦψOverlay] → R={packet['resonance_index']:.4f}, Δφ={packet['phase_diff']:.4f}, "
            f"r={packet['correlation']:.4f}"
        )
        return packet

    except Exception as e:
        logger.warning(f"[ΦψOverlay] Failed to update overlay: {e}")
        return {}


def start_overlay_stream(interval: float = 5.0):
    """Continuously stream Φ–ψ resonance data to the overlay bus."""
    logger.info(f"[ΦψOverlay] Starting resonance telemetry stream (interval={interval}s)")
    while True:
        fetch_live_resonance_data()
        time.sleep(interval)