# File: backend/modules/glyphnet/glyphnet_satellite_mode.py

import time
import json
import logging
import asyncio
from typing import Dict, List, Optional

from backend.modules.glyphnet.glyphnet_packet import push_symbolic_packet

logger = logging.getLogger(__name__)

# In-memory store for delayed packets
_satellite_buffer: List[Dict] = []

# Manual registry of online targets (can be integrated with real presence/identity system)
available_targets: Dict[str, bool] = {
    "AION": True,
    "ASTARION": True,
    "MARS_DRONE": False,  # Simulated delayed target
}

# Configurable time-to-live for packets (in seconds)
PACKET_TTL_SECONDS = 60 * 60  # 1 hour

# ──────────────────────────────────────────────
# Core helpers (internal)
# ──────────────────────────────────────────────
def _is_expired(ts: float, now: float) -> bool:
    return (now - ts) > PACKET_TTL_SECONDS


# ──────────────────────────────────────────────
# Public API - synchronous (backward compatible)
# ──────────────────────────────────────────────
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
    Returns delivery stats. (Synchronous)
    """
    now = time.time()
    delivered = 0
    expired = 0

    for item in _satellite_buffer:
        target = item["target"]
        age_expired = _is_expired(item["timestamp"], now)

        # Drop if expired (mark once)
        if age_expired:
            if not item.get("expired"):
                item["expired"] = True
                logger.warning(f"[SatelliteMode] Dropped expired packet for {target} (age {int(now - item['timestamp'])}s)")
                expired += 1
            continue

        # Deliver if available and not yet delivered
        if not item["delivered"] and available_targets.get(target):
            try:
                success = push_symbolic_packet(item["packet"])
                if success:
                    item["delivered"] = True
                    delivered += 1
                    logger.info(f"[SatelliteMode] Forwarded packet to {target}")
                else:
                    logger.warning(f"[SatelliteMode] Push failed for {target}")
            except Exception as e:
                logger.warning(f"[SatelliteMode] Exception forwarding to {target}: {e}")

    return {"status": "ok", "forwarded": delivered, "expired": expired}


def set_target_status(target: str, is_online: bool):
    """
    Update the online/offline status of a target.
    If newly online, auto-flush pending packets. (Synchronous)
    """
    previous = available_targets.get(target, False)
    available_targets[target] = is_online

    if is_online and not previous:
        logger.info(f"[SatelliteMode] Target {target} came online - flushing packets...")
        flush_available_packets()
    elif not is_online and previous:
        logger.info(f"[SatelliteMode] Target {target} went offline.")


def simulate_orbit_tick(delay: float = 2.0):
    """
    Blocking loop that periodically flushes packets. (Synchronous)
    """
    while True:
        flush_available_packets()
        time.sleep(delay)


def get_buffer_status(include_expired: bool = False) -> List[Dict]:
    """
    Returns status of all buffered packets for display/logging/monitoring.
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


def save_buffer_to_disk(path: str = "/tmp/glyphnet_satellite_buffer.json"):
    """
    Persist buffer to disk. (Synchronous)
    """
    try:
        with open(path, "w") as f:
            json.dump(_satellite_buffer, f)
        logger.info(f"[SatelliteMode] Buffer saved to {path}")
    except Exception as e:
        logger.error(f"[SatelliteMode] Failed to save buffer: {e}")


def load_buffer_from_disk(path: str = "/tmp/glyphnet_satellite_buffer.json"):
    """
    Load buffer from disk. (Synchronous)
    """
    global _satellite_buffer
    try:
        with open(path, "r") as f:
            _satellite_buffer = json.load(f)
        logger.info(f"[SatelliteMode] Buffer loaded from {path} ({len(_satellite_buffer)} packets)")
    except FileNotFoundError:
        logger.info(f"[SatelliteMode] No buffer file found at {path}")
    except Exception as e:
        logger.error(f"[SatelliteMode] Failed to load buffer: {e}")


# ──────────────────────────────────────────────
# Public API - asynchronous (non-blocking)
# ──────────────────────────────────────────────
async def flush_available_packets_async() -> Dict[str, int]:
    """
    Async variant of flush_available_packets.
    Runs push in a thread executor to avoid blocking the event loop.
    """
    loop = asyncio.get_running_loop()
    now = time.time()
    delivered = 0
    expired = 0

    # We iterate over the same in-memory buffer; logic mirrors sync path
    for item in _satellite_buffer:
        target = item["target"]
        age_expired = _is_expired(item["timestamp"], now)

        if age_expired:
            if not item.get("expired"):
                item["expired"] = True
                logger.warning(f"[SatelliteMode] Dropped expired packet for {target} (age {int(now - item['timestamp'])}s)")
                expired += 1
            continue

        if not item["delivered"] and available_targets.get(target):
            try:
                # push_symbolic_packet is synchronous -> run in a thread
                success = await loop.run_in_executor(None, push_symbolic_packet, item["packet"])
                if success:
                    item["delivered"] = True
                    delivered += 1
                    logger.info(f"[SatelliteMode] (async) Forwarded packet to {target}")
                else:
                    logger.warning(f"[SatelliteMode] (async) Push failed for {target}")
            except Exception as e:
                logger.warning(f"[SatelliteMode] (async) Exception forwarding to {target}: {e}")

    return {"status": "ok", "forwarded": delivered, "expired": expired}


async def set_target_status_async(target: str, is_online: bool):
    """
    Async variant of set_target_status. Auto-flush on online transition.
    """
    previous = available_targets.get(target, False)
    available_targets[target] = is_online

    if is_online and not previous:
        logger.info(f"[SatelliteMode] Target {target} came online - async flushing packets...")
        await flush_available_packets_async()
    elif not is_online and previous:
        logger.info(f"[SatelliteMode] Target {target} went offline.")


async def simulate_orbit_tick_async(delay: float = 2.0, stop_event: Optional[asyncio.Event] = None):
    """
    Non-blocking periodic flusher for FastAPI/async runtimes.
    If stop_event is provided, loop exits when it is set.
    """
    while True:
        await flush_available_packets_async()
        try:
            if stop_event:
                # Wait with cancellation awareness
                await asyncio.wait_for(stop_event.wait(), timeout=delay)
                if stop_event.is_set():
                    logger.info("[SatelliteMode] Async orbit tick stopping (stop_event set).")
                    return
            else:
                await asyncio.sleep(delay)
        except asyncio.TimeoutError:
            # timeout -> loop again
            pass


async def save_buffer_to_disk_async(path: str = "/tmp/glyphnet_satellite_buffer.json"):
    """
    Async wrapper to persist buffer to disk without blocking the event loop.
    """
    loop = asyncio.get_running_loop()
    await loop.run_in_executor(None, save_buffer_to_disk, path)


async def load_buffer_from_disk_async(path: str = "/tmp/glyphnet_satellite_buffer.json"):
    """
    Async wrapper to load buffer from disk without blocking the event loop.
    """
    loop = asyncio.get_running_loop()
    await loop.run_in_executor(None, load_buffer_from_disk, path)