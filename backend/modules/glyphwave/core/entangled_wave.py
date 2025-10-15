from typing import Dict, List, Any, Optional
import time

from backend.modules.glyphwave.kernels.interference_kernel_core import join_waves_batch

try:
    import jax
    DEVICE_TYPE = jax.devices()[0].device_kind if jax.devices() else "Unknown"
except Exception:
    DEVICE_TYPE = "Unavailable"


class EntangledWave:
    def __init__(self, mode: str = "bidirectional"):
        self.mode = mode
        self.waves: List["WaveState"] = []
        self.entanglement_map: Dict[int, List[int]] = {}

        # ✅ B6a additions
        self.forward_links: Dict[str, List[str]] = {}  # wave_id → entangled wave_ids
        self.reverse_links: Dict[str, List[str]] = {}  # entangled wave_id → source wave_ids
        self.entangled_ids: Dict[int, str] = {}        # index → entangled_id

    def add_wave(self, wave: "WaveState", index: Optional[int] = None):
        """
        Adds a WaveState to the entangled set.
        Backward-compatible: if index is not provided, assigns the next available index.
        """
        # 🧩 Assign automatic index if omitted
        if index is None:
            index = len(self.waves)

        self.waves.append(wave)
        self.entanglement_map[index] = []

        # ✅ Generate unique entangled ID
        entangled_id = f"entangled_{index}"
        self.entangled_ids[index] = entangled_id

        # ✅ Ensure wave metadata consistency
        wave_id = wave.metadata.get("wave_id", f"wave_{index}")
        wave.metadata["wave_id"] = wave_id
        wave.metadata["entangled_id"] = entangled_id

        # ✅ Initialize linkage structures
        self.forward_links.setdefault(wave_id, [])
        self.reverse_links.setdefault(entangled_id, [])
        self.reverse_links[entangled_id].append(wave_id)

        # ✅ Optional: register wave in ENTANGLED_WAVE_STORE for fast access
        try:
            from backend.modules.glyphwave.core.wave_state import ENTANGLED_WAVE_STORE
            if hasattr(wave, "container_id"):
                ENTANGLED_WAVE_STORE[wave.container_id] = self
        except Exception:
            pass  # safe to ignore if store not yet initialized

    def generate_links(self):
        for i in range(len(self.waves)):
            for j in range(i + 1, len(self.waves)):
                if self.mode == "bidirectional":
                    self.entanglement_map[i].append(j)
                    self.entanglement_map[j].append(i)
                elif self.mode == "fused":
                    self.entanglement_map[i].extend([k for k in range(len(self.waves)) if k != i])

                # ✅ B6a: Track bidirectional links
                wave_i = self.waves[i]
                wave_j = self.waves[j]

                id_i = wave_i.metadata["wave_id"]
                id_j = wave_j.metadata["wave_id"]

                self.forward_links[id_i].append(id_j)
                self.forward_links[id_j].append(id_i)

    # ✅ B6a: Accessors
    def get_entangled_partners(self, wave_id: str) -> List[str]:
        """Return all wave_ids entangled with the given wave_id."""
        return self.forward_links.get(wave_id, [])

    def get_linked_wave_ids(self, entangled_id: str) -> List[str]:
        """Return all wave_ids associated with a given entangled_id."""
        return self.reverse_links.get(entangled_id, [])

    def debug_summary(self) -> Dict:
        return {
            "total_waves": len(self.waves),
            "mode": self.mode,
            "forward_links": self.forward_links,
            "reverse_links": self.reverse_links
        }

    # ✅ B6b: Debug printer
    def print_graph_debug(self):
        print(f"\n[EntangledWave Graph - mode: {self.mode}]")
        for idx, targets in self.entanglement_map.items():
            print(f"  Wave {idx} ↔ {targets}")

    # ✅ B6b: Convert to graph (for GHX/debug)
    def to_graph(self) -> Dict:
        """
        Convert entanglement map to graph structure: nodes + links.
        Useful for debug display or GHX/QFC overlay rendering.
        """
        nodes = []
        links = []

        for idx, wave in enumerate(self.waves):
            wave_id = wave.metadata.get("wave_id", f"wave_{idx}")
            nodes.append({
                "id": wave_id,
                "label": f"Wave {idx}",
                "phase": wave.phase,
                "amplitude": wave.amplitude,
                "coherence": wave.coherence,
                "timestamp": wave.timestamp
            })

        for source, targets in self.forward_links.items():
            for target in targets:
                links.append({
                    "source": source,
                    "target": target,
                    "type": self.mode
                })

        return {
            "nodes": nodes,
            "links": links,
            "mode": self.mode
        }

    # ✅ F03: Collapse with GPU metrics
    def collapse_all(self) -> Dict:
        """
        Collapse all entangled waves using the fast vectorized GPU/MLX-compatible kernel.
        Returns a payload with symbolic results + performance metrics.
        Ensures the returned object is always a dict, even if the kernel
        outputs a list, ndarray, or WaveState object.
        """
        start_time = time.time()
        result = join_waves_batch(self.waves)
        duration_ms = round((time.time() - start_time) * 1000, 3)

        metrics = {
            "collapse_time_ms": duration_ms,
            "device": DEVICE_TYPE if "DEVICE_TYPE" in globals() else "CPU",
            "num_waves": len(self.waves),
            "timestamp": time.time()
        }

        # 🧩 Normalize result: ensure it's always a dict
        if isinstance(result, dict):
            result["collapse_metrics"] = metrics
        else:
            result = {
                "collapsed_waves": result,
                "collapse_metrics": metrics
            }

        # 🔁 Inject metrics into each wave's metadata
        for wave in self.waves:
            if hasattr(wave, "metadata") and isinstance(wave.metadata, dict):
                wave.metadata["collapse_metrics"] = metrics

        return result
        
    # ✅ NEW: From glyphs → builds an EntangledWave object from glyph list
    @classmethod
    def from_glyphs(cls, glyphs: List[Dict]) -> "EntangledWave":
        """
        Create an EntangledWave instance from a list of glyph dicts.
        Each glyph is transformed into a WaveState, entangled bidirectionally.
        """
        from backend.modules.glyphwave.core.wave_state import WaveState  # ⏳ delay to break import loop

        entangled = cls(mode="bidirectional")
        for idx, glyph in enumerate(glyphs):
            wave = WaveState.from_glyph_dict(glyph)
            entangled.add_wave(wave, index=idx)

        entangled.generate_links()
        return entangled