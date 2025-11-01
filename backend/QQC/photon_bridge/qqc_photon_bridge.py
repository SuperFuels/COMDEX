"""
Quantum Quad Core (QQC) - Photon Bridge
────────────────────────────────────────────
Listens to Photon glyph packets from GHX Awareness Feed (SSE or file tail),
decodes them via PhotonIngestProtocol, and forwards normalized fields
to the QQC Resonance Bus.

Usage:
    PYTHONPATH=. python backend/QQC/photon_bridge/qqc_photon_bridge.py
"""

import json
import logging
import requests
import time
from typing import Dict

from backend.RQC.src.photon_runtime.interfaces.photon_ingest_protocol import PhotonIngestProtocol

# ────────────────────────────────────────────────
#  Optional Photon decode import (fallback-safe)
# ────────────────────────────────────────────────
try:
    from backend.RQC.src.photon_runtime.glyph_math.encoder import photon_decode
except Exception:
    photon_decode = None

# ────────────────────────────────────────────────
#  Configuration
# ────────────────────────────────────────────────
SSE_URL = "http://127.0.0.1:5005/stream/ghx"
BASE_RETRY_DELAY = 3      # initial seconds between reconnect attempts
MAX_RETRY_DELAY = 30      # cap for exponential backoff
BACKOFF_FACTOR = 1.5      # growth multiplier for retry delay

# Logger setup
logger = logging.getLogger("QQCPhotonBridge")
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
formatter = logging.Formatter(
    "[%(asctime)s] [%(name)s] %(levelname)s: %(message)s", "%H:%M:%S"
)
handler.setFormatter(formatter)
logger.addHandler(handler)

# ────────────────────────────────────────────────
#  QQC Photon Bridge Implementation
# ────────────────────────────────────────────────
class QQCPhotonBridge(PhotonIngestProtocol):
    """
    QQC subsystem bridge for consuming Photon glyph streams
    and publishing normalized resonance packets to the internal bus.
    """

    def __init__(self, name: str = "QQCPhotonBridge"):
        super().__init__(name)
        logger.info(f"[{name}] Initialized and waiting for stream ...")

    def on_ingest(self, data: Dict):
        """Handle incoming Photon data - forward to QQC Resonant Core."""
        phi = data.get("Φ") or data.get("Phi")
        res = data.get("R") or data.get("resonance_index")
        state = data.get("S") or data.get("closure_state")
        gain = data.get("γ") or data.get("gain")

        # Only log meaningful packets
        if any(v is not None for v in (phi, res, state, gain)):
            logger.info(f"[QQC↦Bus] Φ={phi}  R={res}  S={state}  γ={gain}")

        # TODO: integrate this handoff to QQC resonance subsystem core
        # e.g., self.emit_to_bus({"phi": phi, "res": res, "state": state, "gain": gain})

# ────────────────────────────────────────────────
#  Stream Listener with Auto-Reconnect
# ────────────────────────────────────────────────
def run_qqc_photon_listener():
    """
    Continuously listen to GHX Photon SSE stream and pass packets
    through PhotonIngestProtocol for normalization and dispatch.
    Includes auto-reconnect and exponential backoff for robustness.
    """
    bridge = QQCPhotonBridge()
    retry_delay = BASE_RETRY_DELAY

    while True:
        try:
            logger.info("🔗 QQC Photon Bridge attempting connection to GHX SSE stream ...")
            with requests.get(SSE_URL, stream=True, timeout=None) as resp:
                if resp.status_code != 200:
                    logger.warning(
                        f"[QQCPhotonBridge] Bad status {resp.status_code}, retrying in {retry_delay}s ..."
                    )
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
            logger.info("⏹️ QQC Photon Bridge stopped manually.")
            break

        except requests.exceptions.ChunkedEncodingError as e:
            logger.warning(f"[QQCPhotonBridge] Connection lost: {e}. Retrying in {retry_delay}s ...")
            time.sleep(retry_delay)
            retry_delay = min(retry_delay * BACKOFF_FACTOR, MAX_RETRY_DELAY)
            continue

        except requests.ConnectionError as e:
            logger.warning(f"[QQCPhotonBridge] Connection refused: {e}. Retrying in {retry_delay}s ...")
            time.sleep(retry_delay)
            retry_delay = min(retry_delay * BACKOFF_FACTOR, MAX_RETRY_DELAY)
            continue

        except Exception as e:
            logger.exception(f"[QQCPhotonBridge] Unexpected error: {e}")
            time.sleep(retry_delay)
            retry_delay = min(retry_delay * BACKOFF_FACTOR, MAX_RETRY_DELAY)
            continue

# ────────────────────────────────────────────────
#  Standalone Runner
# ────────────────────────────────────────────────
if __name__ == "__main__":
    run_qqc_photon_listener()