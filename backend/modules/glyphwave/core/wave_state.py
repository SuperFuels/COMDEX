from typing import List, Dict, Tuple
import time

# ✅ NEW: Fast vectorized interference kernels with GPU fallback
try:
    from backend.modules.glyphwave.kernels.jax_interference_kernel import join_waves_batch
    GPU_ENABLED = True
except ImportError:
    from backend.modules.glyphwave.kernels.interference_kernel_core import join_waves_batch
    GPU_ENABLED = False

class EntangledWave:
    def __init__(self, mode: str = "bidirectional"):
        self.mode = mode
        self.timestamp = time.time()
        self.waves: List["WaveState"] = []  # Forward-declared for type safety
        self.entanglement_links: List[Tuple[int, int]] = []
        self.metadata: Dict = {}

        # NEW: Bidirectional entanglement map
        self.entangled_map: Dict[int, List[int]] = {}

    def add_wave(self, wave, index: int = None):
        """Add a wave to the entanglement system, optionally at a specific index."""
        if index is None:
            index = len(self.waves)
        self.waves.append(wave)
        self.entangled_map[index] = []

    def generate_links(self):
        """Automatically link all wave pairs in a bidirectional structure."""
        count = len(self.waves)
        for i in range(count):
            for j in range(i + 1, count):
                self.link(i, j)

    def link(self, i: int, j: int):
        """Link two wave indices bidirectionally."""
        self.entanglement_links.append((i, j))
        self.entangled_map.setdefault(i, []).append(j)
        self.entangled_map.setdefault(j, []).append(i)

    def get_entangled_indices(self, index: int) -> List[int]:
        """Retrieve all wave indices entangled with the given index."""
        return self.entangled_map.get(index, [])

    def get_entangled_wave_ids(self, index: int) -> List[str]:
        """Get origin_trace IDs of waves entangled with the given index."""
        entangled_ids = []
        for partner_index in self.get_entangled_indices(index):
            entangled_ids.extend(self.waves[partner_index].origin_trace)
        return entangled_ids

    def debug_links(self) -> Dict[int, List[int]]:
        """Return a readable entanglement map for debug."""
        return self.entangled_map

    def collapse_all(self) -> Dict:
        """
        Collapse all entangled waves using the fast vectorized interference kernel.
        Returns: collapsed payload dictionary (combined symbolic state).
        """
        return join_waves_batch(self.waves)

class WaveState:
    def __init__(self, origin_trace=None, payload=None, metadata=None):
        self.origin_trace = origin_trace or []
        self.payload = payload or {}
        self.metadata = metadata or {}

    def __repr__(self):
        return f"<WaveState trace={self.origin_trace} payload={self.payload}>"