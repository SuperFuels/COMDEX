"""
AION Cognition Trace Bus
Unified event bus → Replay engine → HUD Pulse → SCI bridge.

This bus is intentionally minimal and non-blocking.
Multiple subscribers (replay reducer, live HUD, logs) can attach here.
"""

from typing import Callable, List

# Internal subscriber list
_subscribers: List[Callable] = []

def subscribe(callback: Callable):
    """
    Register a callback that receives cognition events.

    callback(event: dict)
    """
    _subscribers.append(callback)


def emit(event: dict):
    """
    Emit a cognition trace event to all subscribers.
    No guarantees about async/ordering – subscribers handle buffering.
    """
    for cb in _subscribers:
        try:
            cb(event)
        except Exception:
            pass  # never crash the bus


def trace_emit(event: dict):
    """
    Public entrypoint used across AION/Photon/AtomSave.
    Example event payload:
    {
        "type": "glyph_edit",
        "doc": "default",
        "content": "...",
        "sqi": 0.91,
        "t": 1730478200.12
    }
    """
    emit(event)