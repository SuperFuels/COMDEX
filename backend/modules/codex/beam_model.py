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

class Beam:
    def __init__(self, id, logic_tree, glyphs, phase, amplitude, coherence, origin_trace):
        self.id = id
        self.logic_tree = logic_tree
        self.glyphs = glyphs
        self.phase = phase
        self.amplitude = amplitude
        self.coherence = coherence
        self.origin_trace = origin_trace

        # Additional defaults
        self.status = "initial"
        self.sqi_score = None
        self.entropy = None
        self.drift_cost = None
        self.drift_signature = None
        self.soullaw_status = "unknown"
        self.soullaw_violations = []

    def to_dict(self):
        return {
            "id": self.id,
            "logic_tree": self.logic_tree,
            "glyphs": self.glyphs,
            "phase": self.phase,
            "amplitude": self.amplitude,
            "coherence": self.coherence,
            "origin_trace": self.origin_trace,
            "status": self.status,
            "sqi_score": self.sqi_score,
            "entropy": self.entropy,
            "drift_cost": self.drift_cost,
            "drift_signature": self.drift_signature,
            "soullaw_status": self.soullaw_status,
            "soullaw_violations": self.soullaw_violations,
        }

# Export it
__all__ = ["Beam"]

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

    # Ensure serializable format
    mutation = _safe_dict(mutation)

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

    # Ensure serializable format
    collapse_data = _safe_dict(collapse_data)

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
            summary += f" - {ts} | Mutation: {mut.get('type', '?')} → {mut.get('details', {})}\n"
        elif event == "collapse":
            details = entry.get("details", {})
            summary += f" - {ts} | 🛑 Collapse: {details}\n"
        else:
            summary += f" - {ts} | Event: {event}\n"
    return summary


# --- Save to disk ---
def save_beam_history_to_file(beam_id: str) -> None:
    """
    Saves the beam's history to a .json file for long-term traceability.
    """
    history = get_beam_history(beam_id)
    if not history:
        return
    filepath = os.path.join(MUTATION_LOG_DIR, f"{beam_id}_history.json")
    try:
        with open(filepath, "w") as f:
            json.dump(history, f, indent=2)
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


# --- Helper: ensure serializability ---
def _safe_dict(obj: Any) -> Dict[str, Any]:
    """
    Converts objects (like Beam) to dict if possible.
    """
    if isinstance(obj, dict):
        return obj
    elif hasattr(obj, "to_dict") and callable(obj.to_dict):
        return obj.to_dict()
    else:
        return {"value": str(obj)}