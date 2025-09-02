# File: backend/modules/glyphwave/core/wave_state_store.py

from typing import Dict, Optional, List
from .wave_state import WaveState


class WaveStateStore:
    """
    In-memory store of WaveState objects for GlyphWave.
    Tracks currently active symbolic waves prior to transmission or interference.
    """

    def __init__(self):
        self._store: Dict[str, WaveState] = {}

    def add_wave(self, wave: WaveState) -> None:
        """Adds or updates a wave by its origin ID."""
        if not wave.id:
            raise ValueError("WaveState must have a unique `id` to be stored.")
        self._store[wave.id] = wave

    def get_wave(self, wave_id: str) -> Optional[WaveState]:
        """Retrieve a wave by its ID."""
        return self._store.get(wave_id)

    def remove_wave(self, wave_id: str) -> None:
        """Delete a wave from the store."""
        self._store.pop(wave_id, None)

    def all_waves(self) -> List[WaveState]:
        """Returns all wave states currently stored."""
        return list(self._store.values())

    def clear(self) -> None:
        """Clears all stored wave states."""
        self._store.clear()

    def snapshot(self) -> Dict[str, dict]:
        """
        Export all wave states as dicts (for transmission or diagnostics).
        """
        return {wid: wave.to_dict() for wid, wave in self._store.items()}