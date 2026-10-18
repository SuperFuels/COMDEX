from __future__ import annotations

"""
Symatics Engine (minimal write-path runtime)

Purpose
- Compile intentional Symatics / Photon-Algebra expressions into emitted waveforms.
- Hold those waveforms stable with a lightweight SQI-style feedback loop.
- Replace most of the old Hyperdrive stage/particle shell for Hello World experiments.

Design
    SymaticsExpression -> SymaticsCompiler -> EmissionProfile -> Emitter
                                                   ^              |
                                                   |              v
                                            SQIStabilizer <- feedback

Notes
- This is intentionally minimal. It does not simulate particles, chambers, fuel, or stages.
- It is built for first-contact / Hello World experiments:
    * constructive lock
    * destructive lock
    * beyond-Boolean intermediate phase states
- It can be adapted to an existing field_bridge by implementing an emitter adapter.
- Safe-mode determinism has been tightened so repeated runs are comparable.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Protocol
import math
import time

from backend.modules.dimensions.ucs.zones.experiments.qwave_engine.field_bridge import FieldBridge

TWO_PI = 2.0 * math.pi


def _wrap_phase(phi: float) -> float:
    return float(phi) % TWO_PI


def _clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


@dataclass(slots=True)
class SymaticsExpression:
    """Human-meaningful symbolic intent to be spoken outward."""

    name: str
    mode: str = "interference"
    phi: float = 0.0
    amplitude: float = 1.0
    frequency: float = 1.0
    harmonics: List[int] = field(default_factory=lambda: [1])
    duty_cycle: float = 0.5
    envelope: str = "steady"
    duration_s: float = 2.0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class EmissionProfile:
    """Physical waveform parameters produced by the compiler."""

    label: str
    phi: float
    amplitude: float
    frequency: float
    harmonics: List[int]
    duty_cycle: float
    envelope: str
    duration_s: float
    interference_factor: float
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class FeedbackSample:
    """Minimal feedback view from the outside world or bridge."""

    timestamp: float
    measured_voltage: float = 0.0
    measured_phase: float = 0.0
    measured_amplitude: float = 0.0
    measured_frequency: float = 0.0
    stability_score: float = 0.0
    notes: Dict[str, Any] = field(default_factory=dict)


class Emitter(Protocol):
    def emit(self, profile: EmissionProfile) -> None: ...
    def sample_feedback(self) -> FeedbackSample: ...


class SymaticsCompiler:
    """
    Converts symbolic expressions into emission profiles.

    Strategy
    - phi is the core symbolic word boundary.
    - interference_factor is preserved as symbolic metadata.
    - amplitude remains user intent, not multiplied destructively at compile time.
      That lets the field bridge decide how to physically realise cancellation
      or intermediate states.
    - compilation is deterministic and auditable.
    """

    def __init__(self) -> None:
        self._compile_counter = 0

    def compile(self, expr: SymaticsExpression) -> EmissionProfile:
        self._compile_counter += 1
        phi = _wrap_phase(expr.phi)

        # Symbolic meaning only; not used to destroy amplitude at compile-time.
        interference_factor = 1.0 + math.cos(phi)

        amplitude = max(0.0, float(expr.amplitude))
        frequency = max(0.001, float(expr.frequency))
        duty_cycle = _clamp(float(expr.duty_cycle), 0.01, 0.99)
        harmonics = [max(1, int(h)) for h in (expr.harmonics[:] if expr.harmonics else [1])]

        metadata = {
            "expression_name": expr.name,
            "mode": expr.mode,
            # deterministic compile ordinal instead of wall-clock
            "compile_index": self._compile_counter,
            "semantic_phi_state": self.describe_phi_state(phi),
            **expr.metadata,
        }

        return EmissionProfile(
            label=expr.name,
            phi=phi,
            amplitude=amplitude,
            frequency=frequency,
            harmonics=harmonics,
            duty_cycle=duty_cycle,
            envelope=expr.envelope,
            duration_s=max(0.01, float(expr.duration_s)),
            interference_factor=interference_factor,
            metadata=metadata,
        )

    @staticmethod
    def describe_phi_state(phi: float) -> str:
        phi = _wrap_phase(phi)
        if abs(phi - 0.0) < 1e-6 or abs(phi - TWO_PI) < 1e-6:
            return "constructive"
        if abs(phi - math.pi) < 1e-6:
            return "destructive"
        if abs(phi - (math.pi / 2.0)) < 1e-6:
            return "beyond_boolean_positive"
        if abs(phi - (3.0 * math.pi / 2.0)) < 1e-6:
            return "beyond_boolean_negative"
        return "intermediate"

    def hello_world_constructive(self) -> SymaticsExpression:
        return SymaticsExpression(
            name="hello_world_constructive",
            phi=0.0,
            amplitude=1.0,
            frequency=1.0,
            harmonics=[1, 2],
            envelope="steady",
            duration_s=3.0,
            metadata={"semantic_state": "constructive"},
        )

    def hello_world_destructive(self) -> SymaticsExpression:
        return SymaticsExpression(
            name="hello_world_destructive",
            phi=math.pi,
            amplitude=0.2,
            frequency=1.0,
            harmonics=[1],
            envelope="steady",
            duration_s=3.0,
            metadata={"semantic_state": "destructive"},
        )

    def hello_world_beyond_boolean(self) -> SymaticsExpression:
        return SymaticsExpression(
            name="hello_world_beyond_boolean",
            phi=math.pi / 2.0,
            amplitude=0.8,
            frequency=1.0,
            harmonics=[1, 2, 3],
            envelope="steady",
            duration_s=3.0,
            metadata={"semantic_state": "beyond_boolean_probe"},
        )

    def phase_probe(
        self,
        phi: float,
        frequency: float = 1.0,
        amplitude: float = 1.0,
        harmonics: Optional[List[int]] = None,
    ) -> SymaticsExpression:
        return SymaticsExpression(
            name=f"phase_probe_{phi:.6f}",
            phi=float(phi),
            amplitude=float(amplitude),
            frequency=float(frequency),
            harmonics=harmonics or [1, 2],
            envelope="steady",
            duration_s=2.0,
            metadata={"semantic_state": "phase_probe"},
        )


class SQIStabilizer:
    """
    Minimal closed-loop stabilizer.

    It does not invent the word. It only helps hold the emitted word stable.
    """

    def __init__(
        self,
        target_voltage: float = 1.0,
        target_stability: float = 0.90,
        amplitude_blend: float = 0.05,
        frequency_blend: float = 0.03,
        phase_nudge: float = 0.03,
    ):
        self.target_voltage = float(target_voltage)
        self.target_stability = float(target_stability)
        self.amplitude_blend = float(amplitude_blend)
        self.frequency_blend = float(frequency_blend)
        self.phase_nudge = float(phase_nudge)
        self.feedback_history: List[FeedbackSample] = []

    def observe(self, sample: FeedbackSample) -> None:
        self.feedback_history.append(sample)
        if len(self.feedback_history) > 200:
            self.feedback_history = self.feedback_history[-200:]

    def drift(self, window: int = 20) -> float:
        recent = self.feedback_history[-window:]
        if len(recent) < 2:
            return 999.0

        phases = [_wrap_phase(s.measured_phase) for s in recent]
        phases.sort()

        gaps: List[float] = []
        for i in range(len(phases) - 1):
            gaps.append(phases[i + 1] - phases[i])
        gaps.append((phases[0] + TWO_PI) - phases[-1])

        largest_gap = max(gaps)
        covered_arc = TWO_PI - largest_gap
        return covered_arc

    def is_locked(self, window: int = 20, drift_threshold: float = 0.05) -> bool:
        recent = self.feedback_history[-window:]
        if len(recent) < window:
            return False

        mean_stability = sum(s.stability_score for s in recent) / len(recent)
        mean_voltage = sum(s.measured_voltage for s in recent) / len(recent)
        drift_value = self.drift(window)

        if mean_stability >= self.target_stability and drift_value <= drift_threshold:
            return True

        if mean_voltage <= 0.08 and drift_value <= drift_threshold:
            return True

        return False

    def refine(self, profile: EmissionProfile, sample: FeedbackSample) -> EmissionProfile:
        semantic_state = profile.metadata.get("semantic_phi_state", "intermediate")

        if semantic_state == "destructive":
            new_amplitude = min(profile.amplitude, 0.25)
            new_frequency = profile.frequency
            new_phi = profile.phi
            return EmissionProfile(
                label=profile.label,
                phi=new_phi,
                amplitude=max(0.0, new_amplitude),
                frequency=max(0.001, new_frequency),
                harmonics=profile.harmonics[:],
                duty_cycle=profile.duty_cycle,
                envelope=profile.envelope,
                duration_s=profile.duration_s,
                interference_factor=(1.0 + math.cos(new_phi)),
                metadata={**profile.metadata, "refined": True, "destructive_hold": True},
            )

        voltage_error = self.target_voltage - sample.measured_voltage
        stability_error = self.target_stability - sample.stability_score

        new_amplitude = profile.amplitude + (voltage_error * self.amplitude_blend)
        new_frequency = profile.frequency + (stability_error * self.frequency_blend)

        new_amplitude = _clamp(new_amplitude, 0.0, 1.5)
        new_frequency = _clamp(new_frequency, 0.5, 3.0)

        phase_error = (_wrap_phase(profile.phi) - _wrap_phase(sample.measured_phase))
        if phase_error > math.pi:
            phase_error -= TWO_PI
        elif phase_error < -math.pi:
            phase_error += TWO_PI

        new_phi = _wrap_phase(profile.phi - (phase_error * self.phase_nudge * 0.2))

        return EmissionProfile(
            label=profile.label,
            phi=new_phi,
            amplitude=new_amplitude,
            frequency=new_frequency,
            harmonics=profile.harmonics[:],
            duty_cycle=profile.duty_cycle,
            envelope=profile.envelope,
            duration_s=profile.duration_s,
            interference_factor=(1.0 + math.cos(new_phi)),
            metadata={**profile.metadata, "refined": True},
        )


class NullEmitter:
    """
    Safe default emitter for software-only testing.
    It stores last profile and fabricates deterministic feedback.
    """

    def __init__(self):
        self.last_profile: Optional[EmissionProfile] = None
        self._emit_tick = 0
        self._last_feedback = FeedbackSample(timestamp=0.0)

    def emit(self, profile: EmissionProfile) -> None:
        self.last_profile = profile
        self._emit_tick += 1

        semantic_state = profile.metadata.get("semantic_phi_state", "intermediate")
        if semantic_state == "destructive":
            target_voltage = 0.05
        else:
            target_voltage = max(0.05, profile.amplitude)

        # deterministic safe-mode phase wobble
        phase_noise = math.sin(self._emit_tick * 0.17) * 0.02
        measured_phase = _wrap_phase(profile.phi + phase_noise)

        voltage_error = abs(target_voltage - profile.amplitude)
        stability = 1.0 - min(1.0, voltage_error / max(0.25, profile.amplitude + 0.25))

        self._last_feedback = FeedbackSample(
            timestamp=float(self._emit_tick),
            measured_voltage=target_voltage,
            measured_phase=measured_phase,
            measured_amplitude=profile.amplitude,
            measured_frequency=profile.frequency,
            stability_score=_clamp(stability, 0.0, 1.0),
            notes={
                "mode": "null_emitter",
                "emit_tick": self._emit_tick,
            },
        )

    def sample_feedback(self) -> FeedbackSample:
        return self._last_feedback


class FieldBridgeEmitter:
    """
    Adapter for the qwave_engine FieldBridge.

    Bridge capabilities supported:
    - emit_symatics_wave(...)
    - emit_exhaust_wave(...)
    - get_feedback_voltage()
    """

    def __init__(self, field_bridge: Any):
        self.field_bridge = field_bridge
        self.last_profile: Optional[EmissionProfile] = None
        self._sample_tick = 0

    def emit(self, profile: EmissionProfile) -> None:
        self.last_profile = profile

        if hasattr(self.field_bridge, "emit_symatics_wave"):
            self.field_bridge.emit_symatics_wave(
                phi=profile.phi,
                amplitude=profile.amplitude,
                frequency=profile.frequency,
                harmonic_signature=profile.harmonics,
                duty_cycle=profile.duty_cycle,
                envelope=profile.envelope,
            )
            return

        if hasattr(self.field_bridge, "emit_exhaust_wave"):
            energy_proxy = max(0.0, profile.amplitude * profile.frequency)
            self.field_bridge.emit_exhaust_wave(
                phase=profile.phi,
                energy=energy_proxy,
                harmonics=max(profile.harmonics) if profile.harmonics else 1,
                burst=(profile.envelope in {"burst", "pulsed", "ignite"}),
            )
            return

        raise RuntimeError("Field bridge has no supported emission method.")

    def sample_feedback(self) -> FeedbackSample:
        self._sample_tick += 1

        measured_voltage = 0.0
        if hasattr(self.field_bridge, "get_feedback_voltage"):
            measured_voltage = self.field_bridge.get_feedback_voltage() or 0.0

        if self.last_profile is None:
            return FeedbackSample(
                timestamp=float(self._sample_tick),
                measured_voltage=measured_voltage,
            )

        phase_noise = 0.0
        if hasattr(self.field_bridge, "safe_mode") and self.field_bridge.safe_mode:
            # deterministic tick-based phase wobble instead of wall-clock
            phase_noise = math.sin(self._sample_tick * 0.17) * 0.02

        measured_phase = _wrap_phase(self.last_profile.phi + phase_noise)

        semantic_state = self.last_profile.metadata.get("semantic_phi_state", "intermediate")
        if semantic_state == "destructive":
            target_voltage = 0.05
        else:
            target_voltage = max(0.05, self.last_profile.amplitude)

        voltage_error = abs(measured_voltage - target_voltage)
        stability_guess = 1.0 - min(1.0, voltage_error / max(0.25, target_voltage + 0.25))

        return FeedbackSample(
            timestamp=float(self._sample_tick),
            measured_voltage=measured_voltage,
            measured_phase=measured_phase,
            measured_amplitude=measured_voltage,
            measured_frequency=self.last_profile.frequency,
            stability_score=_clamp(stability_guess, 0.0, 1.0),
            notes={
                "mode": "field_bridge",
                "sample_tick": self._sample_tick,
                "target_voltage": target_voltage,
                "interference_factor": self.last_profile.interference_factor,
            },
        )


class SymaticsEngine:
    """Minimal runtime for compiling, emitting, and stabilizing symbolic words."""

    def __init__(
        self,
        emitter: Emitter,
        compiler: Optional[SymaticsCompiler] = None,
        stabilizer: Optional[SQIStabilizer] = None,
        tick_delay_s: float = 0.1,
        deterministic_timestamps: bool = True,
    ):
        self.emitter = emitter
        self.compiler = compiler or SymaticsCompiler()
        self.stabilizer = stabilizer or SQIStabilizer()
        self.tick_delay_s = float(tick_delay_s)
        self.deterministic_timestamps = bool(deterministic_timestamps)

        self.current_expression: Optional[SymaticsExpression] = None
        self.current_profile: Optional[EmissionProfile] = None

        self.tick_count: int = 0
        self.events: List[str] = []

    def log(self, msg: str) -> None:
        self.events.append(msg)

    def reset_runtime(self, clear_feedback: bool = True) -> None:
        self.current_expression = None
        self.current_profile = None
        self.tick_count = 0
        self.events.clear()
        if clear_feedback:
            self.stabilizer.feedback_history.clear()

    def load_expression(self, expr: SymaticsExpression) -> EmissionProfile:
        self.current_expression = expr
        self.current_profile = self.compiler.compile(expr)
        self.log(
            f"loaded:{expr.name} "
            f"phi={self.current_profile.phi:.6f} "
            f"A={self.current_profile.amplitude:.6f} "
            f"f={self.current_profile.frequency:.6f} "
            f"state={self.current_profile.metadata.get('semantic_phi_state')}"
        )
        return self.current_profile

    def emit_once(self) -> FeedbackSample:
        if self.current_profile is None:
            raise RuntimeError("No expression/profile loaded.")

        self.tick_count += 1
        self.emitter.emit(self.current_profile)

        sample = self.emitter.sample_feedback()
        self.stabilizer.observe(sample)

        self.log(
            f"emit:{self.current_profile.label} "
            f"tick={self.tick_count} "
            f"phi={self.current_profile.phi:.6f} "
            f"V={sample.measured_voltage:.6f} "
            f"S={sample.stability_score:.6f}"
        )
        return sample

    def stabilize_step(self) -> FeedbackSample:
        sample = self.emit_once()

        if self.current_profile is None:
            return sample

        self.current_profile = self.stabilizer.refine(self.current_profile, sample)
        self.log(
            f"refine:{self.current_profile.label} "
            f"phi={self.current_profile.phi:.6f} "
            f"A={self.current_profile.amplitude:.6f} "
            f"f={self.current_profile.frequency:.6f}"
        )
        return sample

    def run_until_lock(self, max_ticks: int = 100, drift_threshold: float = 0.05) -> Dict[str, Any]:
        if self.current_profile is None:
            raise RuntimeError("No expression/profile loaded.")

        start = self.tick_count if self.deterministic_timestamps else time.time()
        locked = False
        sample: Optional[FeedbackSample] = None

        for _ in range(max_ticks):
            sample = self.stabilize_step()

            if self.stabilizer.is_locked(drift_threshold=drift_threshold):
                locked = True
                self.log(
                    f"locked:{self.current_profile.label} "
                    f"drift={self.stabilizer.drift():.6f}"
                )
                break

            if self.tick_delay_s > 0 and not self.deterministic_timestamps:
                time.sleep(self.tick_delay_s)

        end = self.tick_count if self.deterministic_timestamps else time.time()
        elapsed = float(end - start)

        return {
            "ok": True,
            "locked": locked,
            "ticks": self.tick_count,
            "elapsed_s": elapsed,
            "final_profile": self.current_profile,
            "last_feedback": sample,
            "drift": self.stabilizer.drift(),
            "events": self.events[-25:],
        }

    def run_expression(
        self,
        expr: SymaticsExpression,
        max_ticks: int = 100,
        reset_feedback: bool = False,
    ) -> Dict[str, Any]:
        if reset_feedback:
            self.stabilizer.feedback_history.clear()
        self.load_expression(expr)
        return self.run_until_lock(max_ticks=max_ticks)

    def phase_sweep(
        self,
        phases: List[float],
        frequency: float = 1.0,
        amplitude: float = 1.0,
        ticks_per_phase: int = 30,
        reset_feedback_per_phase: bool = True,
    ) -> List[Dict[str, Any]]:
        out: List[Dict[str, Any]] = []

        for phi in phases:
            if reset_feedback_per_phase:
                self.stabilizer.feedback_history.clear()

            expr = self.compiler.phase_probe(
                phi=phi,
                frequency=frequency,
                amplitude=amplitude,
            )
            result = self.run_expression(expr, max_ticks=ticks_per_phase)

            out.append(
                {
                    "phi": phi,
                    "locked": result["locked"],
                    "drift": result["drift"],
                    "final_profile": result["final_profile"],
                    "last_feedback": result["last_feedback"],
                }
            )

        return out

    def live_state_packet(self) -> Dict[str, Any]:
        """
        Export a HexCore-friendly live state packet from the current engine state.
        """
        profile = self.current_profile
        feedback = self.stabilizer.feedback_history[-1] if self.stabilizer.feedback_history else None

        if profile is None:
            return {
                "S1": 0.0,
                "S2": 0.0,
                "S4": 1.0,
                "E": 0.0,
                "H": 0.0,
                "resonance": 0.0,
                "coherence": 0.0,
                "entropy": 1.0,
                "delta_phi": 1.0,
                "phase": 0.0,
                "frequency": 0.0,
                "amplitude": 0.0,
                "interference_factor": 0.0,
                "stability_score": 0.0,
                "drift": float(self.stabilizer.drift()),
                "locked": False,
                "tick_count": self.tick_count,
                "observed_regime": "engine_unloaded",
                "predicted_symbol": None,
                "source": "symatics_engine_live",
            }

        phi = _wrap_phase(profile.phi)
        semantic_state = profile.metadata.get("semantic_phi_state", "intermediate")

        s1 = 1.0 if semantic_state == "constructive" else 0.0
        s2 = 1.0 if semantic_state in {"beyond_boolean_positive", "beyond_boolean_negative"} else 0.0
        s4 = 1.0 if semantic_state == "destructive" else 0.0

        coherence = float(feedback.stability_score) if feedback else 0.0
        drift = float(self.stabilizer.drift())
        locked = bool(self.stabilizer.is_locked()) if self.stabilizer.feedback_history else False
        amplitude = float(profile.amplitude)
        frequency = float(profile.frequency)
        resonance = float(profile.interference_factor / 2.0)
        entropy = float(_clamp(abs(drift) / math.pi, 0.0, 1.0))
        delta_phi = float(_clamp(abs(phi - (feedback.measured_phase if feedback else phi)) / math.pi, 0.0, 1.0))

        predicted_symbol = None
        if semantic_state == "constructive":
            predicted_symbol = "S1"
        elif semantic_state in {"beyond_boolean_positive", "beyond_boolean_negative"}:
            predicted_symbol = "S2"
        elif semantic_state == "destructive":
            predicted_symbol = "S4"

        return {
            "S1": s1,
            "S2": s2,
            "S4": s4,
            "E": amplitude,
            "H": float(max(profile.harmonics) if profile.harmonics else 1.0),
            "resonance": resonance,
            "coherence": coherence,
            "entropy": entropy,
            "delta_phi": delta_phi,
            "phase": phi,
            "frequency": frequency,
            "amplitude": amplitude,
            "interference_factor": float(profile.interference_factor),
            "stability_score": coherence,
            "drift": drift,
            "locked": locked,
            "tick_count": self.tick_count,
            "observed_regime": semantic_state,
            "predicted_symbol": predicted_symbol,
            "source": "symatics_engine_live",
        }


def build_hello_world_engine(
    field_bridge: Any | None = None,
    safe_mode: bool = True,
    tick_delay_s: float = 0.0,
    deterministic_timestamps: bool = True,
) -> SymaticsEngine:
    emitter: Emitter

    if field_bridge is None:
        try:
            field_bridge = FieldBridge(safe_mode=safe_mode)
        except Exception:
            field_bridge = None

    if field_bridge is None:
        emitter = NullEmitter()
    else:
        emitter = FieldBridgeEmitter(field_bridge)

    return SymaticsEngine(
        emitter=emitter,
        tick_delay_s=tick_delay_s,
        deterministic_timestamps=deterministic_timestamps,
    )

_ENGINE_SINGLETON: Optional[SymaticsEngine] = None


def get_engine() -> SymaticsEngine:
    global _ENGINE_SINGLETON
    if _ENGINE_SINGLETON is None:
        _ENGINE_SINGLETON = build_hello_world_engine()
    return _ENGINE_SINGLETON


def get_state() -> Dict[str, Any]:
    return get_engine().live_state_packet()


def run_step(_: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    engine = get_engine()

    if engine.current_profile is None:
        engine.load_expression(engine.compiler.hello_world_constructive())

    engine.stabilize_step()
    return engine.live_state_packet()
    

if __name__ == "__main__":
    engine = build_hello_world_engine()
    compiler = engine.compiler

    print("=== Constructive ===")
    res1 = engine.run_expression(
        compiler.hello_world_constructive(),
        max_ticks=20,
        reset_feedback=True,
    )
    print(res1["locked"], res1["drift"])

    print("=== Destructive ===")
    res2 = engine.run_expression(
        compiler.hello_world_destructive(),
        max_ticks=20,
        reset_feedback=True,
    )
    print(res2["locked"], res2["drift"])

    print("=== Beyond Boolean ===")
    res3 = engine.run_expression(
        compiler.hello_world_beyond_boolean(),
        max_ticks=20,
        reset_feedback=True,
    )
    print(res3["locked"], res3["drift"])