import time
from typing import List, Dict, Tuple, Optional
from backend.modules.codex.codex_core import CodexCore

# 🧠 Runtime wave store: container_id → EntangledWave
ENTANGLED_WAVE_STORE: Dict[str, "EntangledWave"] = {}

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
    def __init__(
        self,
        wave_id: str,
        glyph_data: dict,
        carrier_type: str = "simulated",
        modulation_strategy: str = "default",
        delay_ms: int = 0,
        origin_trace: list = None,
        metadata: dict = None,
        prediction: dict = None,
        sqi_score: Optional[float] = None,
        collapse_state: str = "entangled",
    ):
        self.id = wave_id
        self.glyph_data = glyph_data or {}
        self.carrier_type = carrier_type
        self.modulation_strategy = modulation_strategy
        self.delay_ms = delay_ms
        self.origin_trace = origin_trace or []
        self.metadata = metadata or {}

        self.prediction = prediction or {}
        self.sqi_score = sqi_score
        self.collapse_state = collapse_state

    def __repr__(self):
        return (
            f"<WaveState id={self.id} "
            f"carrier={self.carrier_type}/{self.modulation_strategy} "
            f"delay={self.delay_ms}ms glyphs={len(self.glyph_data)}>"
        )

def compute_sqi_score(w1: WaveState, w2: WaveState) -> float:
    """
    Placeholder logic for SQI score.
    This should be replaced with a true symbolic interference coherence measure.
    """
    if w1.carrier_type == w2.carrier_type:
        return 0.95
    return 0.75

def determine_collapse_state(w1: WaveState, w2: WaveState) -> str:
    """
    Determine the symbolic collapse state based on metadata and symbolic clues.
    """
    if "contradicted" in w1.metadata or "contradicted" in w2.metadata:
        return "contradicted"
    if "collapsed" in w1.metadata or "collapsed" in w2.metadata:
        return "collapsed"
    if "prediction" in w1.metadata or "prediction" in w2.metadata:
        return "predicted"
    return "entangled"

def register_entangled_wave(container_id: str, entangled_wave: EntangledWave):
    """
    Register or update the entangled wave state for a specific container.
    """
    ENTANGLED_WAVE_STORE[container_id] = entangled_wave

def get_active_wave_state_by_container_id(container_id: str) -> Optional[Dict]:
    """
    Retrieve QWave beam data for the given container ID.
    Returns a list of entangled beam dictionaries with live prediction + SQI scoring.
    """
    ew = ENTANGLED_WAVE_STORE.get(container_id)
    if not ew:
        return None

    codex = CodexCore()
    entangled_beams = []

    for i, wave in enumerate(ew.waves):
        partners = ew.get_entangled_indices(i)
        for j in partners:
            target_wave = ew.waves[j]

            # 🧠 Run CodexLang prediction on source wave
            raw_code = wave.glyph_data.get("raw_codexlang", "")
            exec_result = codex.execute(raw_code, context={"source": "wave_state"})

            sqi_score = round(exec_result.get("cost", {}).get("total", 0.0), 3)
            collapse_state = "predicted" if exec_result["status"] == "executed" else "error"
            prediction = exec_result.get("result", {})

            # ✅ Store into wave state for downstream access
            wave.prediction = prediction
            wave.sqi_score = sqi_score
            wave.collapse_state = collapse_state

            # ✅ Log prediction for collapse trace export
            from backend.modules.codex.collapse_trace_exporter import log_beam_prediction

            log_beam_prediction(
                container_id=wave.origin_trace[0] if wave.origin_trace else "unknown",
                beam_id=wave.id,
                prediction=wave.prediction,
                sqi_score=wave.sqi_score,
                collapse_state=wave.collapse_state,
                metadata=wave.metadata,
            )

            # 🛰️ Build beam with injected metadata
            beam = {
                "id": f"beam_{wave.id}__{target_wave.id}",
                "source_id": wave.id,
                "target_id": target_wave.id,
                "carrier_type": wave.carrier_type,
                "modulation_strategy": wave.modulation_strategy,
                "coherence_score": 1.0,  # Still placeholder
                "SQI_score": sqi_score,
                "collapse_state": collapse_state,
                "prediction": prediction,
                "entangled_path": wave.origin_trace + target_wave.origin_trace,
                "mutation_trace": [],
                "metadata": wave.metadata,
            }

            entangled_beams.append(beam)

    return {
        "container_id": container_id,
        "entangled_beams": entangled_beams,
    }