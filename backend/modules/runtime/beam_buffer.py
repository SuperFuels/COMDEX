# File: backend/modules/runtime/beam_buffer.py

"""
beam_buffer.py
==============

Manages the in-memory symbolic QWave beam buffer.
Supports:
- Shared access across beam processors
- GPU handoff and return
- Lifecycle tagging (new, collapsed, mutated, reinjected)
- Entangled set coordination (optional)
"""

import threading
from typing import List, Dict
from backend.modules.quantum.wave_state import WaveState

class BeamBuffer:
    def __init__(self):
        self._lock = threading.Lock()
        self._buffer: Dict[str, WaveState] = {}       # Indexed by beam ID
        self._tags: Dict[str, str] = {}               # beam_id → tag (e.g., new, gpu, mutated)
    
    def add_beam(self, beam: WaveState, tag: str = "new"):
        with self._lock:
            self._buffer[beam.id] = beam
            self._tags[beam.id] = tag

    def get_all(self) -> List[WaveState]:
        with self._lock:
            return list(self._buffer.values())

    def get_by_tag(self, tag: str) -> List[WaveState]:
        with self._lock:
            return [b for bid, b in self._buffer.items() if self._tags.get(bid) == tag]

    def mark(self, beam_id: str, tag: str):
        with self._lock:
            if beam_id in self._buffer:
                self._tags[beam_id] = tag

    def pop_by_tag(self, tag: str) -> List[WaveState]:
        with self._lock:
            popped = []
            to_remove = [bid for bid, t in self._tags.items() if t == tag]
            for bid in to_remove:
                popped.append(self._buffer.pop(bid))
                self._tags.pop(bid)
            return popped

    def get_beam(self, beam_id: str) -> WaveState:
        with self._lock:
            return self._buffer.get(beam_id)

    def remove_beam(self, beam_id: str):
        with self._lock:
            self._buffer.pop(beam_id, None)
            self._tags.pop(beam_id, None)

    def clear(self):
        with self._lock:
            self._buffer.clear()
            self._tags.clear()

    def stats(self) -> Dict[str, int]:
        with self._lock:
            tag_count = {}
            for tag in self._tags.values():
                tag_count[tag] = tag_count.get(tag, 0) + 1
            return tag_count


# Global beam buffer instance (or override per container/thread)
global_beam_buffer = BeamBuffer()