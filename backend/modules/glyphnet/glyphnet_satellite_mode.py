# backend/modules/glyphnet/glyphnet_satellite_mode.py

import time
import logging
from typing import Dict, List, Optional

from backend.modules.glyphnet.glyphnet_packet import send_gip_packet

logger = logging.getLogger(__name__)

# In-memory store for delayed packets
_satellite_buffer: List[Dict] = []

# Manual registry of online targets (simplified mockup)
available_targets: Dict[str, bool] = {
    "AION": True,
    "ASTARION": True,
    "MARS_DRONE": False,  # Simulate delayed target
}


def store_packet_for_forwarding(packet: Dict, target: str):
    _satellite_buffer.append({
        "packet": packet,
        "target": target,
        "timestamp": time.time(),
        "delivered": False,
    })
    logger.info(f"[SatelliteMode] Stored packet for {target}")


def flush_available_packets():
    """
    Sends all stored packets to online targets.
    """
    delivered = 0
    for item in _satellite_buffer:
        target = item["target"]
        if not item["delivered"] and available_targets.get(target):
            try:
                send_gip_packet(item["packet"], target)
                item["delivered"] = True
                delivered += 1
                logger.info(f"[SatelliteMode] Forwarded packet to {target}")
            except Exception as e:
                logger.warning(f"[SatelliteMode] Failed to forward to {target}: {e}")

    return {"status": "ok", "forwarded": delivered}


def simulate_orbit_tick(delay: float = 2.0):
    """
    Simulates a repeated orbital sync that flushes stored packets.
    """
    while True:
        flush_available_packets()
        time.sleep(delay)


def get_buffer_status() -> List[Dict]:
    """
    Returns all packets, useful for UI/log/monitor.
    """
    return [
        {
            "target": p["target"],
            "timestamp": p["timestamp"],
            "delivered": p["delivered"],
        }
        for p in _satellite_buffer
    ]