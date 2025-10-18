"""
AION — Photon Ingest Bridge
────────────────────────────────────────────
Receives Photon glyph packets (via GHX Awareness Feed or QQC forwarder),
decodes and normalizes them using PhotonIngestProtocol,
and injects them into the AION Cognitive Fabric (ψ κ T Φ pipeline).

Usage:
    PYTHONPATH=. python backend/AION/photon_bridge/aion_photon_ingest.py
"""

import json
import logging
import requests
import time
from typing import Dict
from flask import Flask, request, jsonify

from backend.RQC.src.photon_runtime.interfaces.photon_ingest_protocol import PhotonIngestProtocol
from backend.AION.fabric.aion_fabric_resonance import resonance_ingest

# ────────────────────────────────────────────────
# Optional Photon decoder (fallback-safe)
# ────────────────────────────────────────────────
try:
    from backend.RQC.src.photon_runtime.glyph_math.encoder import photon_decode
except Exception:
    photon_decode = None

# ────────────────────────────────────────────────
# Configuration
# ────────────────────────────────────────────────
SSE_URL = "http://127.0.0.1:5005/stream/ghx"
BASE_RETRY_DELAY = 3
MAX_RETRY_DELAY = 30
BACKOFF_FACTOR = 1.5

# ────────────────────────────────────────────────
# Logging Setup
# ────────────────────────────────────────────────
logger = logging.getLogger("AIONPhotonIngest")
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
formatter = logging.Formatter("[%(asctime)s] [%(name)s] %(levelname)s: %(message)s", "%H:%M:%S")
handler.setFormatter(formatter)
logger.addHandler(handler)

# ────────────────────────────────────────────────
# AION Photon Bridge Implementation
# ────────────────────────────────────────────────
class AIONPhotonIngestor(PhotonIngestProtocol):
    """
    AION-side Photon Language ingestion bridge.
    Translates resonance glyph packets (Φ, R, S, γ)
    into internal ψ κ T Φ cognitive fabric fields
    for live awareness coupling.
    """

    def __init__(self, name: str = "AIONPhotonIngestor"):
        super().__init__(name)
        self.current_gamma_prime = 1.0  # adaptive feedback gain
        logger.info(f"[{name}] Initialized and waiting for stream …")

    # ───────────────────────────────
    # Feedback Gain Handling
    # ───────────────────────────────
    def update_feedback_gain(self, gamma_prime: float):
        """Receives γ′ (adaptive gain) from AION Fabric Feedback Controller."""
        if not isinstance(gamma_prime, (int, float)):
            logger.warning(f"[AIONPhotonIngestor] Invalid γ′ value: {gamma_prime}")
            return
        self.current_gamma_prime = max(0.1, min(2.0, gamma_prime))
        logger.info(f"[AIONPhotonIngestor] Updated feedback gain γ′={self.current_gamma_prime:.3f}")

    # ───────────────────────────────
    # Packet Ingestion Logic
    # ───────────────────────────────
    def on_ingest(self, data: Dict):
        """Handle Photon packet decoded from GHX stream."""
        if not isinstance(data, dict) or not data:
            self.log_event("AION⇌Fabric[Invalid]", {"error": "Malformed or empty packet"})
            return

        phi = data.get("Φ") or data.get("Phi")
        res = data.get("R") or data.get("resonance_index")
        state = data.get("S") or data.get("closure_state")
        gain = data.get("γ") or data.get("gain")

        # Apply feedback gain correction (σ→γ′ coupling)
        if gain is not None:
            gain = (gain or 1.0) * getattr(self, "current_gamma_prime", 1.0)

        fabric_packet = {
            "ψ": phi,
            "κ": res,
            "T": gain,
            "Φ": phi,
            "stability": state,
        }

        logger.info(f"[AION⇌Fabric] ψ={phi} κ={res} T={gain} Φ={phi} S={state}")
        self._forward_to_cognitive_fabric(fabric_packet)

    # ───────────────────────────────
    # Internal forward stub
    # ───────────────────────────────
    def _forward_to_cognitive_fabric(self, payload: Dict):
        """Forward normalized ψ–κ–T–Φ packet to AION Morphic Fabric."""
        resonance_ingest(payload)

# ────────────────────────────────────────────────
# Flask API for feedback gain update
# ────────────────────────────────────────────────
app = Flask("AIONGainReceiver")
bridge = AIONPhotonIngestor()

@app.route("/aion/update_gain", methods=["POST"])
def update_gain():
    data = request.json
    gamma_prime = data.get("gamma_prime")
    bridge.update_feedback_gain(gamma_prime)
    return jsonify({"status": "ok", "gamma_prime": gamma_prime})

# ────────────────────────────────────────────────
# Stream Listener with Auto-Reconnect
# ────────────────────────────────────────────────
def run_aion_photon_listener():
    """Continuously listen to GHX Photon SSE stream and pass packets to AION."""
    retry_delay = BASE_RETRY_DELAY

    while True:
        try:
            logger.info("🔗 AION Photon Ingestor attempting connection to GHX SSE stream …")
            with requests.get(SSE_URL, stream=True, timeout=None) as resp:
                if resp.status_code != 200:
                    logger.warning(f"[AIONPhotonIngestor] Bad status {resp.status_code}, retrying in {retry_delay}s …")
                    time.sleep(retry_delay)
                    retry_delay = min(retry_delay * BACKOFF_FACTOR, MAX_RETRY_DELAY)
                    continue

                logger.info("✅ Connected to GHX Photon SSE feed.")
                retry_delay = BASE_RETRY_DELAY  # reset after success

                for line in resp.iter_lines(decode_unicode=True):
                    if not line or not line.startswith("data: "):
                        continue
                    packet = line.replace("data: ", "").strip()
                    if not packet:
                        continue
                    bridge.ingest_packet(packet)

        except KeyboardInterrupt:
            logger.info("⏹️ AION Photon Ingestor stopped manually.")
            break

        except requests.exceptions.ChunkedEncodingError as e:
            logger.warning(f"[AIONPhotonIngestor] Connection lost: {e}. Retrying in {retry_delay}s …")
            time.sleep(retry_delay)
            retry_delay = min(retry_delay * BACKOFF_FACTOR, MAX_RETRY_DELAY)
            continue

        except requests.ConnectionError as e:
            logger.warning(f"[AIONPhotonIngestor] Connection refused: {e}. Retrying in {retry_delay}s …")
            time.sleep(retry_delay)
            retry_delay = min(retry_delay * BACKOFF_FACTOR, MAX_RETRY_DELAY)
            continue

        except Exception as e:
            logger.exception(f"[AIONPhotonIngestor] Unexpected error: {e}")
            time.sleep(retry_delay)
            retry_delay = min(retry_delay * BACKOFF_FACTOR, MAX_RETRY_DELAY)
            continue

# ────────────────────────────────────────────────
# Standalone Runner
# ────────────────────────────────────────────────
if __name__ == "__main__":
    from threading import Thread

    # Run Flask gain listener on a side thread
    Thread(target=lambda: app.run(port=5070, debug=False, use_reloader=False)).start()

    # Start photon listener
    run_aion_photon_listener()