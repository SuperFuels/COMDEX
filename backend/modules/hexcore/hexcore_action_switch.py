# ==========================================================
#  Tessaris * HexCore Action Switch ↔ Photon Bridge
#  Encodes symbolic AION actions into Photon packets (.photo)
#  and emits them to the QQC Photon Bridge resonance bus.
#  Stage 14.2 - Action Resonance Propagation
# ==========================================================

import json
import os
import time
import logging
from typing import Dict, Any, Optional

# ──────────────────────────────────────────────
# Photon Encoder (Glyph-based)
# ──────────────────────────────────────────────
try:
    from backend.RQC.src.photon_runtime.glyph_math.encoder import (
        encode_record as photon_encode,
        photon_decode,
    )
    try:
        # Optional advanced Photon encoder (v2)
        from backend.RQC.src.photon_runtime.glyph_math.photon_encode_v2 import photon_encode as photon_encode_v2
    except Exception:
        photon_encode_v2 = None
except ModuleNotFoundError:
    # Fallback encoder if Photon runtime not yet available
    def photon_encode(record):
        print("[MockPhotonEncoder] Encoding:", record)
        return json.dumps(record)

    photon_encode_v2 = None
    photon_decode = None

# ──────────────────────────────────────────────
# Optional direct QQC bridge
# ──────────────────────────────────────────────
try:
    from backend.QQC.photon_bridge.qqc_photon_bridge import QQCPhotonBridge
except ImportError:
    QQCPhotonBridge = None

logger = logging.getLogger("HexCoreActionSwitch")


class HexCoreActionSwitch:
    """
    Encodes high-level AION or HexCore actions into Photon
    resonance packets for QQC ingestion.
    """

    def __init__(self, qqc_ref: Optional[object] = None):
        self.bridge = QQCPhotonBridge() if QQCPhotonBridge else None
        self.qqc = qqc_ref
        os.makedirs("exports/photon", exist_ok=True)
        logger.info("[HexCoreActionSwitch] Initialized with Photon encoder/bridge.")

    # ------------------------------------------------------
    #  Primary Entry
    # ------------------------------------------------------
    def propagate_action(self, action: Dict[str, Any]):
        """
        Convert an action dict into a Photon packet and emit
        to QQC Photon Bridge or save as .photo file.
        Example action:
            {"intent": "reflect", "energy": 0.92, "context": "resonant_field"}
        """
        try:
            payload = {
                "intent": action.get("intent"),
                "energy": action.get("energy", 1.0),
                "timestamp": time.time(),
                "origin": "AION_ActionSwitch",
                "ψ": action.get("psi", 0.0),
                "κ": action.get("kappa", 0.0),
                "Φ": action.get("phi", 0.0),
            }

            # Encode to Photon glyph or JSON string
            encoded = photon_encode_v2(payload) if photon_encode_v2 else photon_encode(payload)
            packet_path = f"exports/photon/{int(time.time()*1000)}.photo"

            # Write encoded stream to file
            with open(packet_path, "w", encoding="utf-8") as f:
                f.write(encoded if isinstance(encoded, str) else json.dumps(encoded))

            # Optional live broadcast -> QQC
            if self.bridge:
                self.bridge.on_ingest(payload)
                logger.info(f"[HexCoreActionSwitch] 🚀 Photon packet emitted to QQC bus (intent={payload['intent']})")

            # If QQC kernel ref provided, append to telemetry
            if self.qqc and hasattr(self.qqc, "last_summary"):
                self.qqc.last_summary.setdefault("actions", []).append(payload)

            logger.info(f"[HexCoreActionSwitch] Photon packet saved -> {packet_path}")

            return {"status": "emitted", "path": packet_path, "payload": payload}

        except Exception as e:
            logger.error(f"[HexCoreActionSwitch] Action propagation failed: {e}")
            return {"status": "error", "error": str(e)}

    # ------------------------------------------------------
    #  Diagnostic utilities
    # ------------------------------------------------------
    def emit_test_signal(self, label: str = "ping", energy: float = 1.0):
        """Emit a diagnostic Photon packet for system health testing."""
        test_action = {"intent": label, "energy": energy, "psi": 0.5, "kappa": 0.5, "phi": 0.5}
        return self.propagate_action(test_action)