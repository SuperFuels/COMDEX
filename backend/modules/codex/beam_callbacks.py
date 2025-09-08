# File: backend/modules/codex/beam_callbacks.py

"""
beam_callbacks.py

Manages symbolic lifecycle callbacks for beam mutation, scoring, collapse,
and emission phases. Enables modular plug-in logic for GHX, SQI, SoulLaw, etc.
"""

import logging
from typing import Callable, Dict, List

from backend.modules.codex.beam_event_bus import beam_event_bus

logger = logging.getLogger(__name__)

# Internal registry of symbolic lifecycle callbacks
_registered_callbacks: Dict[str, List[Callable]] = {
    "on_mutation": [],
    "on_score": [],
    "on_collapse": [],
    "on_emit": [],
}


def register_callback(event_type: str, callback: Callable) -> None:
    """
    Register a callback for a symbolic beam lifecycle event.

    Args:
        event_type (str): One of "on_mutation", "on_score", "on_collapse", "on_emit".
        callback (Callable): Function to call with the beam instance.
    """
    if event_type not in _registered_callbacks:
        raise ValueError(f"Invalid callback type: {event_type}")
    _registered_callbacks[event_type].append(callback)
    logger.debug(f"🔗 Callback registered for {event_type}: {callback.__name__}")


def emit_callbacks(event_type: str, beam) -> None:
    """
    Emit all registered callbacks for a given beam event.

    Args:
        event_type (str): The symbolic lifecycle event type.
        beam (Beam): The beam object being processed.
    """
    for callback in _registered_callbacks.get(event_type, []):
        try:
            callback(beam)
        except Exception as e:
            logger.warning(f"⚠️ Callback {callback.__name__} failed during {event_type}: {e}")


def register_beam_callbacks() -> None:
    """
    Hook into the beam event bus so that symbolic lifecycle events
    trigger associated callbacks across the system.
    """
    beam_event_bus.subscribe("mutation", lambda beam: emit_callbacks("on_mutation", beam))
    beam_event_bus.subscribe("score", lambda beam: emit_callbacks("on_score", beam))
    beam_event_bus.subscribe("collapse", lambda beam: emit_callbacks("on_collapse", beam))
    beam_event_bus.subscribe("emit", lambda beam: emit_callbacks("on_emit", beam))

    logger.info("✅ Symbolic beam callbacks registered to event bus.")