import time
import os
import datetime
import math
import random
import hashlib
from typing import List, Dict, Tuple, Optional, Any
from backend.modules.codex.collapse_trace_exporter import log_beam_prediction
from backend.modules.codex.codex_metrics import log_collapse_metric
from backend.modules.collapse.collapse_trace_exporter import log_beam_collapse

_DETERMINISTIC_TIME = os.getenv("TESSARIS_DETERMINISTIC_TIME", "") == "1"


def _stable_u64(*parts: Any) -> int:
    blob = "|".join("" if p is None else str(p) for p in parts).encode("utf-8")
    h = hashlib.sha256(blob).digest()
    return int.from_bytes(h[:8], "big", signed=False)


def _deterministic_iso_utc() -> str:
    return "0000-00-00T00:00:00Z"


def _utc_iso_now() -> str:
    # keep legacy format used in this file
    return datetime.datetime.utcnow().isoformat() + "Z"


# 🧠 Runtime wave store: container_id -> EntangledWave
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
        self.timestamp = 0.0 if _DETERMINISTIC_TIME else time.time()
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

    def to_qfc_payload(self) -> Dict[str, Any]:
        """
        Convert entangled waves into a QFC payload with nodes and links.
        Includes SQI, prediction, collapse_state, and style metadata.
        Auto-triggers collapse if required metadata is missing.
        """
        # 🧠 Auto-collapse if critical metadata is missing
        if any(w.sqi_score is None or w.collapse_state is None for w in self.waves):
            print("⚠️ Auto-collapsing due to missing SQI/collapse metadata...")
            self.finalize_collapse()

        nodes = []
        links = []

        for i, wave in enumerate(self.waves):
            node = {
                "id": wave.id,
                "label": wave.glyph_data.get("label", wave.glyph_id),
                "containerId": wave.container_id or "unknown",
                "sqi_score": wave.sqi_score,
                "collapse_state": wave.collapse_state,
                "prediction": wave.prediction,
                "metadata": wave.metadata,
            }
            nodes.append(node)

            # 🧬 Generate links from entanglement structure
            for j in self.get_entangled_indices(i):
                target_wave = self.waves[j]
                links.append({
                    "source": wave.id,
                    "target": target_wave.id,
                    "type": "entangled",
                    "collapse_state": wave.collapse_state,
                    "sqi_score": wave.sqi_score,
                    "metadata": wave.metadata,
                })

        return {
            "nodes": nodes,
            "links": links,
        }


class WaveState:
    def __init__(
        self,
        wave_id: Optional[str] = None,
        glyph_data: Optional[dict] = None,
        glyph_id: str = "anon_glyph",
        carrier_type: str = "simulated",
        modulation_strategy: str = "default",
        delay_ms: int = 0,
        origin_trace: Optional[list] = None,
        metadata: Optional[dict] = None,
        prediction: Optional[dict] = None,
        sqi_score: Optional[float] = None,
        collapse_state: str = "entangled",
        entangled_wave: Optional["EntangledWave"] = None,
        tick: Optional[int] = None,
        state: Optional[str] = None,
        container_id: Optional[str] = None,
        source: Optional[str] = None,
        target: Optional[str] = None,
        timestamp: Optional[str] = None,
        glow_intensity: Optional[float] = None,
        pulse_frequency: Optional[float] = None,
        mutation_type: Optional[str] = None,
        mutation_cause: Optional[str] = None,
        # 🌊 UltraQC extensions
        frequency: Optional[float] = None,
        drift: Optional[float] = 0.0,
        qscore: Optional[float] = 1.0,
        entanglement_id: Optional[str] = None,
        coherence: Optional[float] = 1.0,
    ):
        # --- Core identification ---
        self.wave_id = wave_id
        self.glyph_data = glyph_data or {}
        self.glyph_id = glyph_id
        self.container_id = container_id
        self.source = source or self.glyph_data.get("source", "unknown")
        self.target = target or self.glyph_data.get("target", "unknown")

        # deterministic per-wave RNG (prevents any accidental global random bleed)
        if _DETERMINISTIC_TIME:
            self._rng = random.Random(
                _stable_u64(self.wave_id, self.glyph_id, self.container_id, self.source, self.target)
            )
        else:
            self._rng = random  # type: ignore[assignment]

        if timestamp is not None:
            self.timestamp = timestamp
        else:
            if _DETERMINISTIC_TIME:
                self.timestamp = _deterministic_iso_utc()
            else:
                self.timestamp = _utc_iso_now()

        # --- Physical parameters ---
        self.carrier_type = carrier_type
        self.modulation_strategy = modulation_strategy
        self.delay_ms = delay_ms
        self.phase = self.glyph_data.get("phase", self._rng.uniform(0, 2 * math.pi))
        self.amplitude = self.glyph_data.get("amplitude", 1.0)
        self.coherence = coherence or self.glyph_data.get("coherence", 1.0)
        self.entropy = self.glyph_data.get("entropy", 0.0)
        self.entropy = self.glyph_data.get("entropy", 0.0)

        # --- Symbolic & entanglement state ---
        self.origin_trace = origin_trace or []
        self.entangled_wave = entangled_wave

        if entanglement_id is not None:
            self.entanglement_id = entanglement_id
        else:
            if wave_id:
                self.entanglement_id = f"ent_{wave_id}"
            else:
                if _DETERMINISTIC_TIME:
                    n = 1000 + (_stable_u64("ent", self.glyph_id, self.container_id, self.source, self.target) % 9000)
                else:
                    n = random.randint(1000, 9999)
                self.entanglement_id = f"ent_{n}"

        self.state = state or "active"
        self.tick = tick or 0
        self.collapse_state = collapse_state
        self.sqi_score = sqi_score
        self.prediction = prediction
        self.metadata = metadata or {}

        # --- UltraQC extensions ---
        self.frequency = frequency or 1.0
        self.drift = drift
        self.qscore = qscore

        # --- Aesthetic / mutation fields ---
        self.glow_intensity = glow_intensity or 0.0
        self.pulse_frequency = pulse_frequency or 0.0
        self.mutation_type = mutation_type or "none"
        self.mutation_cause = mutation_cause or "unknown"

        # ✅ Fallback: derive ID from entangled context
        if entangled_wave:
            try:
                primary = entangled_wave.primary_glyph
            except AttributeError:
                primary = (
                    entangled_wave.glyphs[0]
                    if hasattr(entangled_wave, "glyphs") and entangled_wave.glyphs
                    else {}
                )
            self.id = wave_id or primary.get("id", "entangled_anon")
            if not self.glyph_data:
                self.glyph_data = primary
        else:
            self.id = wave_id or "anon"

    def __repr__(self):
        return (
            f"<WaveState id={self.id} "
            f"carrier={self.carrier_type}/{self.modulation_strategy} "
            f"delay={self.delay_ms}ms glyphs={len(self.glyph_data)}>"
        )

    def evolve(self):
        """
        SRK-11 / SRK-16 compatibility:
        Perform a minimal state evolution step.
        Updates phase, coherence, entropy, and SQI metrics.
        """
        try:
            # Time-based phase oscillation
            self.phase = (self.phase + self._rng.uniform(0.01, 0.1)) % (2 * math.pi)

            # Simulate coherence/entropy drift
            self.coherence = max(0.0, min(1.0, self.coherence + self._rng.uniform(-0.02, 0.02)))
            self.entropy = max(0.0, min(1.0, self.entropy + self._rng.uniform(-0.01, 0.01)))

            # Simulate SQI score (wave stability index)
            self.last_sqi_score = round(self.coherence * (1.0 - self.entropy), 3)

            # Update internal timestamp
            if _DETERMINISTIC_TIME:
                self.timestamp = _deterministic_iso_utc()
            else:
                self.timestamp = time.time()

        except Exception as e:
            print(f"[WaveState:evolve] evolution failed: {e}")

    @classmethod
    def from_container_id(cls, container_id: str) -> "WaveState":
        """
        SRK-16 utility: reconstruct a WaveState instance from an active container ID.
        Falls back to a minimal empty state if none is found in ENTANGLED_WAVE_STORE.
        """
        try:
            from backend.modules.glyphwave.core.wave_state import ENTANGLED_WAVE_STORE
            ws = ENTANGLED_WAVE_STORE.get(container_id)
            if ws and isinstance(ws, cls):
                return ws
            # fallback: create minimal instance
            instance = cls(container_id=container_id)
            instance.id = f"{container_id}_wave"
            instance.amplitude = 1.0
            instance.phase = 0.0
            instance.coherence = 1.0
            instance.entropy = 0.0
            instance.last_sqi_score = 0.0
            return instance
        except Exception as e:
            print(f"[WaveState] Fallback reconstruction failed for {container_id}: {e}")
            instance = cls(container_id=container_id)
            return instance

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "glyph_data": self.glyph_data,
            "carrier_type": self.carrier_type,
            "modulation_strategy": self.modulation_strategy,
            "delay_ms": self.delay_ms,
            "origin_trace": self.origin_trace,
            "metadata": self.metadata,
            "prediction": self.prediction,
            "sqi_score": self.sqi_score,
            "collapse_state": self.collapse_state,
        }

    @classmethod
    def from_glyph_dict(cls, glyph: dict) -> "WaveState":
        """
        Create a WaveState from a glyph dictionary directly.
        Supports both legacy 'id' and modern 'qwave_id' keys.
        Avoids EntangledWave to prevent circular import/recursion.
        """
        qwave_id = glyph.get("qwave_id", glyph.get("id", f"wave_{hash(str(glyph)) & 0xFFFFF}"))
        return cls(
            wave_id=qwave_id,
            glyph_data=glyph,
            carrier_type=glyph.get("carrier_type", "simulated"),
            modulation_strategy=glyph.get("modulation_strategy", "default"),
            delay_ms=glyph.get("delay_ms", 0),
            origin_trace=glyph.get("origin_trace", []),
            metadata=glyph.get("metadata", {}),
            prediction=None,
            sqi_score=None,
            collapse_state="entangled"
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


def codex_predict_symbol(symbol: str) -> str:
    # Placeholder: use real prediction engine or symbolic logic
    if symbol in ("⊕", "↔", "⧖"):
        return "logic-combine"
    elif symbol == "🧠":
        return "cognitive-insight"
    return "default"


def compute_sqi_score(wave) -> float:
    base_score = 0.5
    if hasattr(wave, "entangled") and isinstance(wave.entangled, list):
        base_score += 0.1 * len(wave.entangled)
    return min(base_score, 1.0)


def determine_collapse_state(wave) -> str:
    if getattr(wave, "collapsed", False):
        return "collapsed"
    if hasattr(wave, "entangled") and wave.entangled:
        return "entangled"
    return "superposed"


def finalize_collapse(self) -> Dict:
    """
    Perform full collapse -> merge pipeline for all entangled waves.
    Includes:
        - Vectorized interference (join_waves_batch)
        - SQI score computation
        - Collapse state tagging
        - Logging beam prediction + Codex collapse metrics
    Returns: Final collapsed result with metadata.
    """
    collapsed_payload = self.collapse_all()

    # Post-process and annotate each wave
    for wave in self.waves:
        wave.sqi_score = compute_sqi_score(wave)
        wave.collapse_state = determine_collapse_state(wave)
        log_beam_prediction(
            wave_id=wave.id,
            container_id=wave.metadata.get("container_id", "unknown"),
            prediction=wave.prediction or {},
            collapse_state=wave.collapse_state,
            sqi_score=wave.sqi_score,
        )
        log_collapse_metric(
            wave_id=wave.id,
            collapse_type="entangled",
            metadata=wave.metadata,
            sqi_score=wave.sqi_score,
        )
        log_beam_collapse(
            wave_id=wave.id,
            collapse_state=wave.collapse_state
        )

    return {
        "collapsed_glyphs": collapsed_payload,
        "entangled_wave_ids": [w.id for w in self.waves],
        "collapse_state": "entangled",
        "sqi_scores": [w.sqi_score for w in self.waves],
    }


def get_active_wave_state_by_container_id(container_id: str) -> Optional[Dict]:
    """
    Retrieve QWave beam data for the given container ID.
    Returns a list of entangled beam dictionaries with live prediction + SQI scoring.
    """
    from backend.modules.codex.codex_core import CodexCore
    ew = ENTANGLED_WAVE_STORE.get(container_id)
    codex = CodexCore()
    if not ew:
        return None

    codex = CodexCore()
    entangled_beams = []

    for i, wave in enumerate(ew.waves):
        partners = ew.get_entangled_indices(i)
        for j in partners:
            target_wave = ew.waves[j]

            # 🧠 CodexLang execution
            raw_code = wave.glyph_data.get("raw_codexlang", "")
            exec_result = codex.execute(raw_code, context={"source": "wave_state"})

            prediction = exec_result.get("result", {})
            sqi_score = round(exec_result.get("cost", {}).get("total", 0.0), 3)
            # 🌊 Compute collapse state and drift overlays
            collapse_state = "predicted" if exec_result.get("status") == "executed" else "error"

            # 🔁 Add drift glow and pulse frequency (A3a)
            glow_intensity = min(max(sqi_score, 0.0), 1.0)
            pulse_frequency = round(1.0 / (sqi_score + 0.01), 2)  # Prevent div-by-zero

            wave.metadata["beam_glow"] = glow_intensity
            wave.metadata["pulse_frequency"] = pulse_frequency

            # ❗ Contradiction overlay if collapse state is failure (A3b)
            if collapse_state == "error" or "contradicted" in wave.metadata.get("tags", []):
                wave.metadata["beam_style"] = "broken"
                wave.metadata["beam_color"] = "red"
            else:
                wave.metadata["beam_style"] = "smooth"
                wave.metadata["beam_color"] = "blue"

            # 🧠 Log to Codex + SQI metrics (A3c)
            try:
                from backend.modules.symbolic.metrics_hooks import log_collapse_metric, log_sqi_drift
                log_collapse_metric(
                    container_id=container_id,
                    beam_id=wave.id,
                    score=sqi_score,
                    state=collapse_state
                )
                log_sqi_drift(
                    container_id=container_id,
                    beam_id=wave.id,
                    glow=glow_intensity,
                    frequency=pulse_frequency
                )
            except Exception as e:
                print(f"[Metrics] ⚠️ Failed to log symbolic metrics: {e}")

            # ✅ Inject into wave object
            wave.prediction = prediction
            wave.sqi_score = sqi_score
            wave.collapse_state = collapse_state

            # ✅ Also mirror into metadata for export and HUD sync
            wave.metadata["prediction"] = prediction
            wave.metadata["sqi_score"] = sqi_score
            wave.metadata["collapse_state"] = collapse_state

            # ✅ Symbol-level fallback if CodexLang failed or raw_code was empty
            if not prediction and hasattr(wave, "symbol"):
                wave.prediction = codex_predict_symbol(wave.symbol)
                wave.sqi_score = compute_sqi_score(wave)
                wave.collapse_state = determine_collapse_state(wave)

                wave.metadata["prediction"] = wave.prediction
                wave.metadata["sqi_score"] = wave.sqi_score
                wave.metadata["collapse_state"] = wave.collapse_state

            # ✅ Log symbolic prediction to Codex trace
            log_beam_prediction(
                container_id=wave.origin_trace[0] if wave.origin_trace else "unknown",
                beam_id=wave.id,
                prediction=prediction,
                sqi_score=sqi_score,
                collapse_state=collapse_state,
                metadata=wave.metadata,
            )

            # ✅ Log symbolic collapse metric to CodexMetrics
            log_collapse_metric(
                container_id=wave.origin_trace[0] if wave.origin_trace else "unknown",
                beam_id=wave.id,
                score=sqi_score,
                state=collapse_state,
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

    def to_qfc_payload(self) -> Dict[str, List[Dict]]:
        """
        Convert this WaveState into a symbolic QFC render payload with node + optional link.
        Useful for HUD updates, live canvas rendering, or beam overlay.
        """
        node = {
            "id": self.id,
            "label": self.glyph_data.get("label", self.glyph_id),
            "type": self.glyph_data.get("type", "wave"),
            "containerId": self.container_id or "unknown",
            "metadata": self.metadata,
            "prediction": self.prediction,
            "sqi_score": self.sqi_score,
            "collapse_state": self.collapse_state,
            "origin_trace": self.origin_trace,
        }

        link = None
        if self.source and self.target and self.source != self.target:
            link = {
                "id": f"{self.source}__{self.target}",
                "source": self.source,
                "target": self.target,
                "metadata": {
                    "carrier_type": self.carrier_type,
                    "modulation_strategy": self.modulation_strategy,
                    "collapse_state": self.collapse_state,
                    "sqi_score": self.sqi_score,
                }
            }

        return {
            "nodes": [node],
            "links": [link] if link else []
        }