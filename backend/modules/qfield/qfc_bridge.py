# ============================================================
# 📁 backend/modules/qfield/qfc_bridge.py
# ============================================================

"""
QFCBridge - unifies Quantum Field Computation (QFC) operations for QQC runtime.
Provides programmatic and CLI interfaces for generating, broadcasting, and saving
QFC (Quantum Field Computation) payloads from container data.
"""

import argparse
import json
import logging
from collections import deque, defaultdict
from typing import Any, Dict, Optional

from backend.modules.qfield.qfc_utils import build_qfc_view

try:
    from backend.modules.qfield.qfc_ws_broadcast import send_qfc_payload
except ImportError:
    send_qfc_payload = None

logger = logging.getLogger(__name__)

# ============================================================
# 🔄 Live Pulse Smoothing Buffers
# ============================================================

_QFC_SMOOTH = defaultdict(lambda: {
    "sqi": deque(maxlen=5),
    "coherence": deque(maxlen=5),
})

def _smooth(value, buf, default=1.0):
    if value is None:
        value = default
    try:
        value = float(value)
    except Exception:
        value = default
    buf.append(value)
    return sum(buf) / len(buf)

# ============================================================
#  Core Bridge Class
# ============================================================
class QFCBridge:
    """Runtime-accessible bridge for QFC view generation and broadcast."""

    def __init__(self):
        self.last_payload: Optional[Dict[str, Any]] = None
        self.last_mode: str = "test"
        logger.info("[QFCBridge] Initialized quantum field bridge.")

    def generate_view(self, container: Dict[str, Any], mode: str = "test") -> Dict[str, Any]:
        """Generate a QFC payload view for a container + smooth SQI/Coherence."""
        try:
            payload = build_qfc_view(container, mode=mode)
            self.last_payload = payload
            self.last_mode = mode

            cid = container.get("id") or "global"
            bufs = _QFC_SMOOTH[cid]

            sqi = payload.get("sqi")
            coh = payload.get("coherence") or payload.get("coh")

            payload["sqi_smoothed"] = _smooth(sqi, bufs["sqi"])
            payload["coherence_smoothed"] = _smooth(coh, bufs["coherence"])

            logger.debug(f"[QFCBridge] Generated QFC payload in mode={mode}.")
            return payload

        except Exception as e:
            logger.error(f"[QFCBridge] Failed to generate QFC view: {e}")
            raise

    def broadcast(self, container: Dict[str, Any], mode: Optional[str] = None) -> bool:
        """Broadcast the QFC payload via WebSocket."""
        if send_qfc_payload is None:
            logger.warning("[QFCBridge] send_qfc_payload not available - broadcast skipped.")
            return False

        payload = self.generate_view(container, mode or self.last_mode)
        try:
            send_qfc_payload(payload, mode=mode or self.last_mode)
            logger.info(f"[QFCBridge] 📡 Broadcasted QFC payload (mode={mode or self.last_mode}).")
            return True
        except Exception as e:
            logger.error(f"[QFCBridge] Broadcast failed: {e}")
            return False

    def save(self, container: Dict[str, Any], path: str, mode: Optional[str] = None) -> str:
        """Save the generated QFC view to a JSON file."""
        payload = self.generate_view(container, mode or self.last_mode)
        try:
            with open(path, "w", encoding="utf-8") as out:
                json.dump(payload, out, indent=2)
            logger.info(f"[QFCBridge] ✅ Saved QFC view to {path}")
            return path
        except Exception as e:
            logger.error(f"[QFCBridge] Failed to save QFC view: {e}")
            raise

# ============================================================
#  CLI Entrypoint (Preserved)
# ============================================================
def main():
    parser = argparse.ArgumentParser(description="🧪 Preview or broadcast QFC structure for a .dc.json container.")
    parser.add_argument("cid", help="Container ID or path to .dc.json file")
    parser.add_argument("--save", help="Path to save QFC view as JSON")
    parser.add_argument("--mode", default="test", help="Mode tag: live | replay | test | mutation")
    parser.add_argument("--broadcast", action="store_true", help="Send QFC view via WebSocket")

    args = parser.parse_args()

    # 📦 Load container
    try:
        if args.cid.endswith(".json"):
            with open(args.cid, "r", encoding="utf-8") as f:
                container = json.load(f)
        else:
            from backend.modules.dimensions.universal_container_system.container_loader import load_container_by_id
            container = load_container_by_id(args.cid)
    except Exception as e:
        print(f"❌ Failed to load container: {e}")
        return

    # 🌌 Generate QFC view and optionally broadcast
    bridge = QFCBridge()
    try:
        qfc_payload = bridge.generate_view(container, mode=args.mode)
        print(json.dumps(qfc_payload, indent=2))

        if args.save:
            bridge.save(container, args.save, mode=args.mode)

        if args.broadcast:
            bridge.broadcast(container, mode=args.mode)

    except Exception as e:
        print(f"❌ Failed to generate or broadcast QFC view: {e}")


if __name__ == "__main__":
    main()