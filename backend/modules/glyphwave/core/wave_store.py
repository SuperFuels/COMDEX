from __future__ import annotations

from typing import Dict, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    # Only for typing; avoids runtime import cycles.
    from backend.modules.glyphwave.core.wave_state import EntangledWave

# container_id -> EntangledWave
ENTANGLED_WAVE_STORE: Dict[str, "EntangledWave"] = {}


def register_entangled_wave(container_id: str, entangled_wave: "EntangledWave") -> None:
    """Register or update the entangled wave state for a specific container."""
    ENTANGLED_WAVE_STORE[container_id] = entangled_wave


def get_entangled_wave(container_id: str) -> Optional["EntangledWave"]:
    """Fetch an entangled wave by container id (or None)."""
    return ENTANGLED_WAVE_STORE.get(container_id)
