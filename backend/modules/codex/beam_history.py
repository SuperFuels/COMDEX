# File: modules/codex/beam_history.py

import datetime
import logging
import json
import os
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

# In-memory beam mutation registry (can be replaced with DB or Redis)
BEAM_MUTATION_LOG: Dict[str, List[Dict[str, Any]]] = {}

# Optional file log location
MUTATION_LOG_DIR = "./logs/beam_history"
os.makedirs(MUTATION_LOG_DIR, exist_ok=True)

# --- Register a beam mutation ---
def register_beam_mutation(
    beam_id: str,
    mutation: Dict[str, Any],
    container_id: Optional[str] = None,
    symbolic_context: Optional[Dict[str, Any]] = None,
    broadcast: bool = False
) -> None:
    """
    Registers a mutation event for a beam, including full metadata.
    """
    timestamp = datetime.datetime.utcnow().isoformat()
    mutation_record = {
        "timestamp": timestamp,
        "beam_id": beam_id,
        "container_id": container_id,
        "event": "mutation",
        "mutation": mutation,
        "symbolic_context": symbolic_context,
    }

    if beam_id not in BEAM_MUTATION_LOG:
        BEAM_MUTATION_LOG[beam_id] = []
    BEAM_MUTATION_LOG[beam_id].append(mutation_record)

    logger.info(f"[BeamHistory] Beam '{beam_id}' mutated at {timestamp} | Type: {mutation.get('type', 'unknown')}")
    print(f"🧬 Beam '{beam_id}' mutated at {timestamp} | Type: {mutation.get('type', 'unknown')}")

    save_beam_history_to_file(beam_id)

    if broadcast:
        try:
            from backend.modules.hologram.ghx_replay_broadcast import broadcast_mutation_event
            broadcast_mutation_event(mutation_record)
        except Exception as e:
            logger.warning(f"[BeamHistory] Mutation broadcast failed: {e}")

# --- Register a beam collapse ---
def register_beam_collapse(
    beam_id: str,
    collapse_data: Dict[str, Any],
    container_id: Optional[str] = None,
    symbolic_context: Optional[Dict[str, Any]] = None,
    broadcast: bool = False
) -> None:
    """
    Registers a collapse event for a beam (e.g., SQI termination, observer interaction).
    """
    timestamp = datetime.datetime.utcnow().isoformat()
    collapse_record = {
        "timestamp": timestamp,
        "beam_id": beam_id,
        "container_id": container_id,
        "event": "collapse",
        "details": collapse_data,
        "symbolic_context": symbolic_context,
    }

    if beam_id not in BEAM_MUTATION_LOG:
        BEAM_MUTATION_LOG[beam_id] = []
    BEAM_MUTATION_LOG[beam_id].append(collapse_record)

    logger.info(f"[BeamHistory] Beam '{beam_id}' collapsed at {timestamp}")
    print(f"💥 Beam '{beam_id}' collapsed at {timestamp}: {collapse_data}")

    save_beam_history_to_file(beam_id)

    if broadcast:
        try:
            from backend.modules.hologram.ghx_replay_broadcast import broadcast_mutation_event
            broadcast_mutation_event(collapse_record)
        except Exception as e:
            logger.warning(f"[BeamHistory] Collapse broadcast failed: {e}")

# --- Retrieve history ---
def get_beam_history(beam_id: str) -> List[Dict[str, Any]]:
    """
    Retrieves the full mutation/collapse history for a given beam.
    """
    return BEAM_MUTATION_LOG.get(beam_id, [])

# --- Summarize for CLI or logs ---
def summarize_beam_history(beam_id: str) -> str:
    """
    Returns a human-readable summary of beam events.
    """
    history = get_beam_history(beam_id)
    if not history:
        return f"🕳️ No history found for beam '{beam_id}'."

    summary = f"📜 History for beam '{beam_id}':\n"
    for entry in history:
        ts = entry["timestamp"]
        event = entry.get("event", "unknown")
        if event == "mutation":
            mut = entry.get("mutation", {})
            summary += f" - {ts} | Mutation: {mut.get('type', '?')} -> {mut.get('details', {})}\n"
        elif event == "collapse":
            details = entry.get("details", {})
            summary += f" - {ts} | 🛑 Collapse: {details}\n"
        else:
            summary += f" - {ts} | Event: {event}\n"
    return summary

def save_beam_history_to_file(beam_id: str) -> None:
    """
    Saves the beam's history to a .json file for long-term traceability.
    """
    history = get_beam_history(beam_id)
    if not history:
        return
    filepath = os.path.join(MUTATION_LOG_DIR, f"{beam_id}_history.json")

    def default_encoder(obj):
        if hasattr(obj, "to_dict"):
            return obj.to_dict()
        return str(obj)

    try:
        with open(filepath, "w") as f:
            json.dump(history, f, indent=2, default=default_encoder)
        logger.debug(f"[BeamHistory] Saved beam history to {filepath}")
    except Exception as e:
        logger.error(f"[BeamHistory] Failed to save history file: {e}")
        
# --- Load from disk ---
def load_beam_history_from_file(beam_id: str) -> List[Dict[str, Any]]:
    """
    Loads beam history from .json file on disk and caches it in memory.
    """
    filepath = os.path.join(MUTATION_LOG_DIR, f"{beam_id}_history.json")
    try:
        with open(filepath, "r") as f:
            history = json.load(f)
        BEAM_MUTATION_LOG[beam_id] = history
        logger.info(f"[BeamHistory] Loaded history from {filepath}")
        return history
    except FileNotFoundError:
        return []
    except Exception as e:
        logger.error(f"[BeamHistory] Error loading history file: {e}")
        return []