# File: backend/modules/glyphnet/glyphnet_satellite_mode.py

import time
import logging
from typing import Dict, List, Optional

from backend.modules.glyphnet.glyphnet_packet import send_gip_packet

logger = logging.getLogger(__name__)

# In-memory store for delayed packets
_satellite_buffer: List[Dict] = []

# Manual registry of online targets (can be integrated with real presence system)
available_targets: Dict[str, bool] = {
    "AION": True,
    "ASTARION": True,
    "MARS_DRONE": False,  # Simulate delayed target
}

# Configurable time-to-live for packets (in seconds)
PACKET_TTL_SECONDS = 60 * 60  # 1 hour


def store_packet_for_forwarding(packet: Dict, target: str):
    """
    Store a symbolic .gip packet for later delivery when target comes online.
    """
    _satellite_buffer.append({
        "packet": packet,
        "target": target,
        "timestamp": time.time(),
        "delivered": False,
    })
    logger.info(f"[SatelliteMode] Stored packet for {target}")


def flush_available_packets() -> Dict[str, int]:
    """
    Sends all stored packets to targets that are currently online.
    Also clears expired packets based on TTL.
    Returns delivery stats.
    """
    now = time.time()
    delivered = 0
    expired = 0

    for item in _satellite_buffer:
        target = item["target"]
        age = now - item["timestamp"]

        # Drop if expired
        if age > PACKET_TTL_SECONDS:
            item["expired"] = True
            logger.warning(f"[SatelliteMode] Dropped expired packet for {target} (age {int(age)}s)")
            expired += 1
            continue

        if not item["delivered"] and available_targets.get(target):
            try:
                send_gip_packet(item["packet"], target)
                item["delivered"] = True
                delivered += 1
                logger.info(f"[SatelliteMode] Forwarded packet to {target}")
            except Exception as e:
                logger.warning(f"[SatelliteMode] Failed to forward to {target}: {e}")

    return {"status": "ok", "forwarded": delivered, "expired": expired}


def set_target_status(target: str, is_online: bool):
    """
    Update the online/offline status of a target.
    If newly online, auto-flush pending packets.
    """
    previous = available_targets.get(target, False)
    available_targets[target] = is_online

    if is_online and not previous:
        logger.info(f"[SatelliteMode] Target {target} came online — flushing packets...")
        flush_available_packets()
    elif not is_online and previous:
        logger.info(f"[SatelliteMode] Target {target} went offline.")


def simulate_orbit_tick(delay: float = 2.0):
    """
    Simulates a repeated orbital sync loop that flushes packets.
    Intended for background async use.
    """
    while True:
        flush_available_packets()
        time.sleep(delay)


def get_buffer_status(include_expired: bool = False) -> List[Dict]:
    """
    Returns status of all buffered packets for display/logging/monitoring.

    Args:
        include_expired: If True, also includes expired packets.

    Returns:
        List of packet metadata.
    """
    result = []
    for p in _satellite_buffer:
        if not include_expired and p.get("expired"):
            continue

        result.append({
            "target": p["target"],
            "timestamp": p["timestamp"],
            "delivered": p["delivered"],
            "expired": p.get("expired", False),
        })
    return result


# Optional: persistence hooks for saving/loading buffer across reboots
# def save_buffer_to_disk():
#     pass

# def load_buffer_from_disk():
#     pass