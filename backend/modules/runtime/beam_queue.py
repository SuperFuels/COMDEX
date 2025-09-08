# File: backend/modules/runtime/beam_queue.py

"""
beam_queue.py
===============
Manages the active QWave beam queue.
Used by beam_tick_loop.py to ingest, update, and recycle symbolic beams.

Features:
- Beam ingestion (add_beam)
- Active queue state (get_active_beams)
- Lifecycle update (update_beam_state)
- Support for reinjection, forked paths, or termination
"""

import threading
from typing import List
from backend.modules.glyphwave.core.wave_state import WaveState
from backend.modules.runtime.beam_scheduler import global_scheduler

# Thread-safe list of currently active beams
_active_beams: List[WaveState] = []
_lock = threading.Lock()

def add_beam(beam: WaveState):
    """
    Add a new beam to the active queue or scheduler.
    """
    with _lock:
        _active_beams.append(beam)

def get_active_beams() -> List[WaveState]:
    """
    Retrieve current beams ready for processing.
    Includes scheduled beams from the scheduler.
    """
    with _lock:
        # Pull from scheduler
        scheduled = global_scheduler.get_ready_beams()
        _active_beams.extend(scheduled)
        beams = list(_active_beams)
        _active_beams.clear()
        return beams

def update_beam_state(beam: WaveState):
    """
    Handle updated beam after processing.
    Supports reinjection, mutation forking, or removal.
    """
    if getattr(beam, "status", None) in ("reinjected", "forked", "mutated"):
        add_beam(beam)
    elif getattr(beam, "status", None) == "terminated":
        pass  # Discard beam
    else:
        add_beam(beam)  # Default: keep active