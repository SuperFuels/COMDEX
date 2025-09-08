# File: backend/modules/codex/beam_history_viewer.py

import logging
from typing import List, Dict, Any, Optional
from backend.modules.codex.beam_history import BEAM_MUTATION_LOG

logger = logging.getLogger(__name__)

def list_all_beams() -> List[str]:
    """
    Return all known beam IDs.
    """
    return list(BEAM_MUTATION_LOG.keys())

def get_mutation_count(beam_id: str) -> int:
    """
    Returns number of mutations for a given beam.
    """
    return len(BEAM_MUTATION_LOG.get(beam_id, []))

def summarize_beam(beam_id: str) -> str:
    """
    Returns readable summary of all mutations.
    """
    history = BEAM_MUTATION_LOG.get(beam_id, [])
    if not history:
        return f"No mutations found for beam '{beam_id}'."

    summary = f"📜 Mutation history for beam '{beam_id}':\n"
    for i, entry in enumerate(history):
        ts = entry["timestamp"]
        mut = entry.get("mutation", {})
        summary += f" {i+1}. [{ts}] Type: {mut.get('type', 'unknown')} → {mut.get('details', {})}\n"
    return summary

def replay_beam_chain(beam_id: str) -> List[Dict[str, Any]]:
    """
    Returns list of all mutations in order.
    """
    return BEAM_MUTATION_LOG.get(beam_id, [])

def get_latest_state(beam_id: str) -> Optional[Dict[str, Any]]:
    """
    Returns the most recent mutation for a beam (simulates current beam state).
    """
    history = BEAM_MUTATION_LOG.get(beam_id, [])
    return history[-1] if history else None

def export_beam_history(beam_id: str) -> Dict[str, Any]:
    """
    Export full mutation log for a beam as a dict.
    Useful for JSON storage or containerization.
    """
    return {
        "beam_id": beam_id,
        "mutation_count": get_mutation_count(beam_id),
        "history": replay_beam_chain(beam_id)
    }

def find_beams_by_mutation_type(mutation_type: str) -> List[str]:
    """
    Search for all beam IDs that had at least one mutation of a given type.
    """
    matching = []
    for beam_id, history in BEAM_MUTATION_LOG.items():
        for entry in history:
            if entry.get("mutation", {}).get("type") == mutation_type:
                matching.append(beam_id)
                break
    return matching