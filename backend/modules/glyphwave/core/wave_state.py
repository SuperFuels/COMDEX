from __future__ import annotations

import datetime
import hashlib
import math
import os
import random
import time
from typing import Any, Dict, List, Optional, Tuple
from backend.utils.log_gate import tprint

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
    # keep legacy format used historically in this module
    return datetime.datetime.utcnow().isoformat() + "Z"


# 🧠 Runtime wave store: container_id -> EntangledWave (single source of truth)
from backend.modules.glyphwave.core.wave_store import (  # noqa: E402
    ENTANGLED_WAVE_STORE,
    get_entangled_wave,
    register_entangled_wave,
)

# ✅ Fast vectorized interference kernels with GPU fallback
try:
    from backend.modules.glyphwave.kernels.jax_interference_kernel import join_waves_batch  # type: ignore

    GPU_ENABLED = True
except ImportError:
    from backend.modules.glyphwave.kernels.interference_kernel_core import join_waves_batch  # type: ignore

    GPU_ENABLED = False


def compute_wave_sqi_score(wave: "WaveState") -> float:
    # placeholder, deterministic
    base = 0.5
    ent = getattr(wave, "entangled", None)
    if isinstance(ent, list):
        base += 0.1 * len(ent)
    return min(base, 1.0)


def determine_wave_collapse_state(wave: "WaveState") -> str:
    if getattr(wave, "collapsed", False):
        return "collapsed"
    ent = getattr(wave, "entangled", None)
    if ent:
        return "entangled"
    return "superposed"


def codex_predict_symbol(symbol: str) -> str:
    if symbol in ("⊕", "↔", "⧖"):
        return "logic-combine"
    if symbol == "🧠":
        return "cognitive-insight"
    return "default"


class EntangledWave:
    def __init__(self, mode: str = "bidirectional"):
        self.mode = mode
        self.timestamp = 0.0 if _DETERMINISTIC_TIME else time.time()
        self.waves: List["WaveState"] = []
        self.entanglement_links: List[Tuple[int, int]] = []
        self.metadata: Dict[str, Any] = {}
        self.entangled_map: Dict[int, List[int]] = {}

    def add_wave(self, wave: "WaveState", index: int | None = None) -> None:
        if index is None:
            index = len(self.waves)
        self.waves.append(wave)
        self.entangled_map.setdefault(index, [])

    def generate_links(self) -> None:
        count = len(self.waves)
        for i in range(count):
            for j in range(i + 1, count):
                self.link(i, j)

    def link(self, i: int, j: int) -> None:
        self.entanglement_links.append((i, j))
        self.entangled_map.setdefault(i, []).append(j)
        self.entangled_map.setdefault(j, []).append(i)

    def get_entangled_indices(self, index: int) -> List[int]:
        return self.entangled_map.get(index, [])

    def get_entangled_wave_ids(self, index: int) -> List[str]:
        entangled_ids: List[str] = []
        for partner_index in self.get_entangled_indices(index):
            entangled_ids.extend(self.waves[partner_index].origin_trace)
        return entangled_ids

    def debug_links(self) -> Dict[int, List[int]]:
        return self.entangled_map

    def collapse_all(self) -> Dict[str, Any]:
        return join_waves_batch(self.waves)

    def finalize_collapse(self) -> Dict[str, Any]:
        """
        Full collapse -> merge pipeline for all entangled waves.
        """
        collapsed_payload = self.collapse_all()

        for wave in self.waves:
            wave.sqi_score = compute_wave_sqi_score(wave)
            wave.collapse_state = determine_wave_collapse_state(wave)

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
            log_beam_collapse(wave_id=wave.id, collapse_state=wave.collapse_state)

        return {
            "collapsed_glyphs": collapsed_payload,
            "entangled_wave_ids": [w.id for w in self.waves],
            "collapse_state": "entangled",
            "sqi_scores": [w.sqi_score for w in self.waves],
        }

    def to_qfc_payload(self) -> Dict[str, Any]:
        # Auto-collapse if missing metadata
        if any(w.sqi_score is None or w.collapse_state is None for w in self.waves):
            self.finalize_collapse()

        nodes: List[Dict[str, Any]] = []
        links: List[Dict[str, Any]] = []

        for i, wave in enumerate(self.waves):
            nodes.append(
                {
                    "id": wave.id,
                    "label": wave.glyph_data.get("label", wave.glyph_id),
                    "containerId": wave.container_id or "unknown",
                    "sqi_score": wave.sqi_score,
                    "collapse_state": wave.collapse_state,
                    "prediction": wave.prediction,
                    "metadata": wave.metadata,
                }
            )

            for j in self.get_entangled_indices(i):
                target_wave = self.waves[j]
                links.append(
                    {
                        "source": wave.id,
                        "target": target_wave.id,
                        "type": "entangled",
                        "collapse_state": wave.collapse_state,
                        "sqi_score": wave.sqi_score,
                        "metadata": wave.metadata,
                    }
                )

        return {"nodes": nodes, "links": links}


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
        entangled_wave: Optional[EntangledWave] = None,
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
        self.wave_id = wave_id
        self.glyph_data = glyph_data or {}
        self.glyph_id = glyph_id
        self.container_id = container_id
        self.source = source or self.glyph_data.get("source", "unknown")
        self.target = target or self.glyph_data.get("target", "unknown")

        # deterministic per-wave RNG (prevents global random bleed)
        if _DETERMINISTIC_TIME:
            self._rng = random.Random(
                _stable_u64(self.wave_id, self.glyph_id, self.container_id, self.source, self.target)
            )
        else:
            self._rng = random  # type: ignore[assignment]

        if timestamp is not None:
            self.timestamp = timestamp
        else:
            self.timestamp = _deterministic_iso_utc() if _DETERMINISTIC_TIME else _utc_iso_now()

        self.carrier_type = carrier_type
        self.modulation_strategy = modulation_strategy
        self.delay_ms = delay_ms

        self.phase = self.glyph_data.get("phase", float(self._rng.uniform(0, 2 * math.pi)))
        self.amplitude = float(self.glyph_data.get("amplitude", 1.0))
        self.coherence = float(coherence if coherence is not None else self.glyph_data.get("coherence", 1.0))
        self.entropy = float(self.glyph_data.get("entropy", 0.0))

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
        self.tick = int(tick or 0)
        self.collapse_state = collapse_state
        self.sqi_score = sqi_score
        self.prediction = prediction
        self.metadata = metadata or {}

        self.frequency = float(frequency if frequency is not None else 1.0)
        self.drift = float(drift if drift is not None else 0.0)
        self.qscore = float(qscore if qscore is not None else 1.0)

        self.glow_intensity = float(glow_intensity if glow_intensity is not None else 0.0)
        self.pulse_frequency = float(pulse_frequency if pulse_frequency is not None else 0.0)
        self.mutation_type = mutation_type or "none"
        self.mutation_cause = mutation_cause or "unknown"

        # ✅ Fallback: derive ID from entangled context
        if entangled_wave:
            try:
                primary = entangled_wave.primary_glyph  # type: ignore[attr-defined]
            except AttributeError:
                primary = (
                    entangled_wave.glyphs[0]  # type: ignore[attr-defined]
                    if hasattr(entangled_wave, "glyphs") and getattr(entangled_wave, "glyphs")
                    else {}
                )
            self.id = wave_id or primary.get("id", "entangled_anon")
            if not self.glyph_data:
                self.glyph_data = primary
        else:
            self.id = wave_id or "anon"

    def __repr__(self) -> str:
        return (
            f"<WaveState id={self.id} "
            f"carrier={self.carrier_type}/{self.modulation_strategy} "
            f"delay={self.delay_ms}ms glyphs={len(self.glyph_data)}>"
        )

    def evolve(self) -> None:
        """
        SRK-11 / SRK-16 compatibility:
        Perform a minimal state evolution step.
        Updates phase, coherence, entropy, and SQI metrics.

        Determinism:
          - Under TESSARIS_DETERMINISTIC_TIME=1, do NOT use wall-clock time.
          - Under deterministic mode, use the per-wave RNG (self._rng), not ambient randomness.
        """
        try:
            dphi = float(self._rng.uniform(0.01, 0.1))
            dcoh = float(self._rng.uniform(-0.02, 0.02))
            dent = float(self._rng.uniform(-0.01, 0.01))

            self.phase = (self.phase + dphi) % (2 * math.pi)
            self.coherence = max(0.0, min(1.0, self.coherence + dcoh))
            self.entropy = max(0.0, min(1.0, self.entropy + dent))
            self.last_sqi_score = round(self.coherence * (1.0 - self.entropy), 3)

            self.timestamp = _deterministic_iso_utc() if _DETERMINISTIC_TIME else _utc_iso_now()

        except Exception as e:
            tprint(f"[WaveState:evolve] evolution failed: {e}")

    @classmethod
    def from_container_id(cls, container_id: str) -> "WaveState":
        """
        SRK-16 utility: reconstruct a WaveState instance from an active container ID.

        Note: ENTANGLED_WAVE_STORE stores EntangledWave, not WaveState.
        If a container has an EntangledWave with waves, returns the first WaveState.
        Otherwise returns a minimal WaveState.
        """
        try:
            ew = get_entangled_wave(container_id)
            if ew and getattr(ew, "waves", None):
                w0 = ew.waves[0]
                if isinstance(w0, cls):
                    return w0

            instance = cls(container_id=container_id)
            instance.id = f"{container_id}_wave"
            instance.amplitude = 1.0
            instance.phase = 0.0
            instance.coherence = 1.0
            instance.entropy = 0.0
            instance.last_sqi_score = 0.0
            return instance

        except Exception as e:
            tprint(f"[WaveState] Fallback reconstruction failed for {container_id}: {e}")
            return cls(container_id=container_id)

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
            collapse_state="entangled",
        )

    def to_qfc_payload(self) -> Dict[str, List[Dict[str, Any]]]:
        node: Dict[str, Any] = {
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

        link: Optional[Dict[str, Any]] = None
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
                },
            }

        return {"nodes": [node], "links": [link] if link else []}


def get_active_wave_state_by_container_id(container_id: str) -> Optional[Dict[str, Any]]:
    """
    Retrieve QWave beam data for the given container ID.
    Returns entangled beam dictionaries with live prediction + SQI scoring.
    """
    from backend.modules.codex.codex_core import CodexCore

    ew = ENTANGLED_WAVE_STORE.get(container_id)
    if not ew:
        return None

    codex = CodexCore()
    entangled_beams: List[Dict[str, Any]] = []

    for i, wave in enumerate(ew.waves):
        partners = ew.get_entangled_indices(i)
        for j in partners:
            target_wave = ew.waves[j]

            raw_code = wave.glyph_data.get("raw_codexlang", "")
            exec_result = codex.execute(raw_code, context={"source": "wave_state"})

            prediction = exec_result.get("result", {})
            sqi_score = round(exec_result.get("cost", {}).get("total", 0.0), 3)
            collapse_state = "predicted" if exec_result.get("status") == "executed" else "error"

            glow_intensity = min(max(float(sqi_score), 0.0), 1.0)
            pulse_frequency = round(1.0 / (float(sqi_score) + 0.01), 2)

            wave.metadata["beam_glow"] = glow_intensity
            wave.metadata["pulse_frequency"] = pulse_frequency

            if collapse_state == "error" or "contradicted" in wave.metadata.get("tags", []):
                wave.metadata["beam_style"] = "broken"
                wave.metadata["beam_color"] = "red"
            else:
                wave.metadata["beam_style"] = "smooth"
                wave.metadata["beam_color"] = "blue"

            try:
                from backend.modules.symbolic.metrics_hooks import log_collapse_metric as log_symbolic_collapse_metric
                from backend.modules.symbolic.metrics_hooks import log_sqi_drift

                log_symbolic_collapse_metric(
                    container_id=container_id,
                    beam_id=wave.id,
                    score=sqi_score,
                    state=collapse_state,
                )
                log_sqi_drift(
                    container_id=container_id,
                    beam_id=wave.id,
                    glow=glow_intensity,
                    frequency=pulse_frequency,
                )
            except Exception as e:
                tprint(f"[Metrics] ⚠️ Failed to log symbolic metrics: {e}")

            wave.prediction = prediction
            wave.sqi_score = sqi_score
            wave.collapse_state = collapse_state

            wave.metadata["prediction"] = prediction
            wave.metadata["sqi_score"] = sqi_score
            wave.metadata["collapse_state"] = collapse_state

            if not prediction and hasattr(wave, "symbol"):
                wave.prediction = codex_predict_symbol(getattr(wave, "symbol"))
                wave.sqi_score = compute_wave_sqi_score(wave)
                wave.collapse_state = determine_wave_collapse_state(wave)
                wave.metadata["prediction"] = wave.prediction
                wave.metadata["sqi_score"] = wave.sqi_score
                wave.metadata["collapse_state"] = wave.collapse_state

            log_beam_prediction(
                container_id=wave.origin_trace[0] if wave.origin_trace else "unknown",
                beam_id=wave.id,
                prediction=prediction,
                sqi_score=sqi_score,
                collapse_state=collapse_state,
                metadata=wave.metadata,
            )

            log_collapse_metric(
                container_id=wave.origin_trace[0] if wave.origin_trace else "unknown",
                beam_id=wave.id,
                score=sqi_score,
                state=collapse_state,
            )

            entangled_beams.append(
                {
                    "id": f"beam_{wave.id}__{target_wave.id}",
                    "source_id": wave.id,
                    "target_id": target_wave.id,
                    "carrier_type": wave.carrier_type,
                    "modulation_strategy": wave.modulation_strategy,
                    "coherence_score": 1.0,
                    "SQI_score": sqi_score,
                    "collapse_state": collapse_state,
                    "prediction": prediction,
                    "entangled_path": wave.origin_trace + target_wave.origin_trace,
                    "mutation_trace": [],
                    "metadata": wave.metadata,
                }
            )

    return {"container_id": container_id, "entangled_beams": entangled_beams}
