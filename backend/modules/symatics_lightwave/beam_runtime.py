"""
BeamRuntime - Photonic Execution Core (v0.5-B3)
-----------------------------------------------
Executes WaveCapsules with mode-specific kernel behavior.

Determinism:
- If TESSARIS_DETERMINISTIC_TIME=1:
  - MUST NOT use wall-clock / perf_counter / sleep for behavior.
  - collapse_time_ms is a deterministic surrogate derived from stable inputs.
"""

from __future__ import annotations

import os
import hashlib
import time

from backend.codexcore_virtual.virtual_wave_engine import VirtualWaveEngine
from backend.modules.codex.beam_event_bus import beam_event_bus, BeamEvent


_DETERMINISTIC_TIME = os.getenv("TESSARIS_DETERMINISTIC_TIME", "") == "1"


def _stable_collapse_time_ms(*parts: object) -> float:
    """
    Deterministic surrogate for collapse latency (ms).
    Used ONLY when deterministic time is enabled.

    Produces a stable value in [1.0, 20.0] ms (3dp).
    """
    blob = "|".join(str(p) for p in parts).encode("utf-8")
    d = hashlib.sha256(blob).digest()
    n = int.from_bytes(d[:8], "big", signed=False)
    ms = 1.0 + (n % 190) / 10.0  # 1.0 .. 20.0 step 0.1
    return float(f"{ms:.3f}")


class BeamRuntime:
    def __init__(self):
        self.engine = VirtualWaveEngine(container_id="symatics.sle.runtime")

    def execute_capsule(self, capsule, mode: str = "generic"):
        # Attach wave to the virtual engine (note: engine itself may print; quieting is separate)
        self.engine.attach_wave(capsule.wave_state)

        # Pull deterministic context from capsule metadata when available
        meta = getattr(capsule, "metadata", {}) or {}
        tick = meta.get("tick")
        t = meta.get("t")
        seed = meta.get("seed")
        scenario_id = meta.get("scenario_id")
        channel = meta.get("channel")

        if not _DETERMINISTIC_TIME:
            start = time.perf_counter()

        # 🛰 Dispatch Event
        beam_event_bus.publish(
            BeamEvent(
                f"{mode}_dispatch",
                source="SymaticsDispatcher",
                target="VirtualWaveEngine",
                qscore=capsule.wave_state.coherence,
                drift=getattr(capsule.wave_state, "drift", 0.0),
                metadata=dict(meta),
            )
        )

        # Simulate photonic kernel
        # Deterministic mode MUST NOT sleep or consult timers.
        if not _DETERMINISTIC_TIME:
            time.sleep(0.01)

        # Apply a stable kernel effect (keep simple + deterministic)
        capsule.wave_state.coherence *= 0.99

        if _DETERMINISTIC_TIME:
            collapse_time_ms = _stable_collapse_time_ms(
                "collapse_time_ms",
                mode,
                getattr(capsule, "opcode", ""),
                seed,
                scenario_id,
                channel,
                tick,
                t,
            )
        else:
            collapse_time_ms = round((time.perf_counter() - start) * 1000, 3)

        # ⚡ Collapse Event
        beam_event_bus.publish(
            BeamEvent(
                f"{mode}_collapse",
                source="VirtualWaveEngine",
                target="SymaticsDispatcher",
                qscore=capsule.wave_state.coherence,
                drift=getattr(capsule.wave_state, "drift", 0.0),
                metadata={
                    "collapse_time_ms": collapse_time_ms,
                    "mode": mode,
                    # preserve capsule meta for downstream consumers
                    "capsule_meta": dict(meta),
                },
            )
        )

        return {
            "opcode": getattr(capsule, "opcode", None),
            "mode": mode,
            "coherence": capsule.wave_state.coherence,
            "collapse_time_ms": collapse_time_ms,
            "status": "executed",
        }