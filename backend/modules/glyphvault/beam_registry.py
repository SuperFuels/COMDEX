# File: backend/modules/glyphvault/beam_registry.py

"""
beam_registry.py

Stores collapsed beams after SQI collapse or interference resolution.
Supports in-memory, file-based, and optional GHX/SymbolNet integration.
"""

import os
import json
import logging
import datetime
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

# In-memory collapsed beam store
COLLAPSED_BEAM_STORE: Dict[str, Dict[str, Any]] = {}

# Persistent log location
REGISTRY_DIR = "./logs/collapsed_beams"
os.makedirs(REGISTRY_DIR, exist_ok=True)

# Broadcast integration (GHX / WebSocket fallback)
try:
    from backend.modules.hologram.ghx_replay_broadcast import broadcast_collapsed_beam_event  # type: ignore
except ImportError:
    def broadcast_collapsed_beam_event(data: dict):
        print(f"[SIM] Broadcast (fallback): {data.get('beam_id', 'unknown')}")


def store_collapsed_beam(
    beam_id: str,
    beam_data: Dict[str, Any],
    persist: bool = True,
    broadcast: bool = True
) -> None:
    """
    Store a collapsed beam in the registry (in-memory + disk + GHX broadcast).
    
    Args:
        beam_id: Unique identifier of the collapsed beam.
        beam_data: Dictionary representation of the beam state.
        persist: Whether to save the beam to disk.
        broadcast: Whether to emit GHX/WebSocket event.
    """
    COLLAPSED_BEAM_STORE[beam_id] = beam_data
    logger.info(f"[BeamRegistry] Stored collapsed beam: {beam_id}")
    print(f"📦 Stored collapsed beam: {beam_id} | Status: {beam_data.get('status', 'unknown')}")

    if persist:
        _save_beam_to_file(beam_id, beam_data)

    if broadcast:
        try:
            enriched = _prepare_broadcast_payload(beam_id, beam_data)
            broadcast_collapsed_beam_event(enriched)
        except Exception as e:
            logger.warning(f"[BeamRegistry] Broadcast failed for beam {beam_id}: {e}")


def retrieve_collapsed_beam(beam_id: str) -> Optional[Dict[str, Any]]:
    """
    Retrieve a collapsed beam from memory or disk.
    """
    if beam_id in COLLAPSED_BEAM_STORE:
        return COLLAPSED_BEAM_STORE[beam_id]

    filepath = os.path.join(REGISTRY_DIR, f"{beam_id}.json")
    if os.path.exists(filepath):
        try:
            with open(filepath, "r") as f:
                data = json.load(f)
            COLLAPSED_BEAM_STORE[beam_id] = data
            logger.debug(f"[BeamRegistry] Loaded collapsed beam from disk: {beam_id}")
            return data
        except Exception as e:
            logger.error(f"[BeamRegistry] Failed to load beam from disk: {e}")
    return None


def _save_beam_to_file(beam_id: str, data: Dict[str, Any]) -> None:
    """
    Persist the collapsed beam to disk for replay or forensic debugging.
    """
    filepath = os.path.join(REGISTRY_DIR, f"{beam_id}.json")
    try:
        with open(filepath, "w") as f:
            json.dump(data, f, indent=2)
        logger.debug(f"[BeamRegistry] Persisted beam to {filepath}")
    except Exception as e:
        logger.error(f"[BeamRegistry] Failed to persist beam to disk: {e}")


def _prepare_broadcast_payload(beam_id: str, beam_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Attach metadata for GHX/SymbolicNet broadcast of a collapsed beam.
    """
    return {
        "event": "beam_collapsed",
        "beam_id": beam_id,
        "timestamp": datetime.datetime.utcnow().isoformat(),
        "status": beam_data.get("status", "unknown"),
        "sqi_score": beam_data.get("sqi_score"),
        "entropy": beam_data.get("entropy"),
        "soullaw_status": beam_data.get("soullaw_status"),
        "tags": beam_data.get("tags", []),
        "container_id": beam_data.get("container_id"),
        "origin_trace": beam_data.get("origin_trace", []),
        "ghx_signature": beam_data.get("ghx_signature", None)
    }