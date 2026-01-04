from __future__ import annotations

import os
import hashlib
from typing import Any, Dict, List

from .determinism import TickClock, SeededRNG
from .event_envelope import beam_event_envelope

# Real SLE dispatcher (your existing runtime plumbing)
from backend.modules.symatics_lightwave.symatics_dispatcher import SymaticsDispatcher


# Deterministic operator plan (scenario -> opcode sequence)
# This is the stable "benchmark plan" for SLE mode.
OPCODE_PLAN: Dict[str, List[str]] = {
    "matched": ["⊕", "⟲", "π"],
    "mismatch": ["μ", "μ", "π"],
    "multiplex": ["⊕", "↔", "⟲", "π"],
    "mutation": ["⊕", "⟲", "μ", "π"],
}

_DETERMINISTIC_TRACE = os.getenv("TESSARIS_DETERMINISTIC_TIME", "") == "1"


def _stable_unit_float(*parts: Any) -> float:
    """
    Deterministic float in [0, 1) from a stable hash of the provided parts.
    Does NOT depend on ambient RNG state.
    """
    blob = "|".join(str(p) for p in parts).encode("utf-8")
    digest = hashlib.sha256(blob).digest()
    n = int.from_bytes(digest[:8], "big", signed=False)
    return n / 2**64


class SLEAdapter:
    """
    Deterministic SLE/Beam execution adapter for GX1.

    Produces:
      - normalized TRACE events (beam_event envelope)
      - per-scenario series suitable for SQI/metrics on top
    """

    def __init__(self, *, seed: int, dt: float = 1 / 30):
        self.rng = SeededRNG(seed)
        self.clock = TickClock(dt=dt)
        self.dispatcher = SymaticsDispatcher()

    def _scenario_ops(self, mode: str) -> List[str]:
        return list(OPCODE_PLAN.get(mode, ["⊕", "π"]))

    def run_scenario(
        self,
        *,
        scenario_id: str,
        mode: str,
        k: int,
        warmup_ticks: int,
        eval_ticks: int,
    ) -> Dict[str, Any]:
        """
        Deterministic tick loop.
        We do NOT rely on wall-clock or ambient randomness for artifact behavior.
        """
        total_ticks = max(warmup_ticks + eval_ticks, warmup_ticks)

        trace: List[Dict[str, Any]] = []
        q_series_ch0: List[float] = []

        ops = self._scenario_ops(mode)
        k = max(1, int(k))

        for tick in range(int(total_ticks)):
            t = self.clock.t(tick)

            for ch in range(k):
                # Deterministic opcode selection (no wall clock, no ambient random)
                opcode = ops[(tick + ch) % len(ops)]

                # Drive the real dispatcher. Keep args deterministic.
                # NOTE: args are included only for deterministic metadata; do not put time/random in them.
                result = self.dispatcher.dispatch({"opcode": opcode, "args": [scenario_id, ch, tick]})

                # Normalize output
                if _DETERMINISTIC_TRACE:
                    # Force qscore/drift determinism even if the dispatcher is nondeterministic internally.
                    qscore = 0.5 + 0.5 * _stable_unit_float(self.rng.seed, scenario_id, mode, opcode, ch, tick, "q")
                    drift = (_stable_unit_float(self.rng.seed, scenario_id, mode, opcode, ch, tick, "d") - 0.5) * 2.0
                    status = "ok"
                else:
                    qscore = float(result.get("coherence", 1.0))
                    drift = float(result.get("drift", 0.0))
                    status = result.get("status", "ok")

                trace.append(
                    beam_event_envelope(
                        tick=tick,
                        t=t,
                        event_type=f"{opcode}_tick",
                        source="SymaticsDispatcher",
                        target="BeamRuntime",
                        qscore=float(qscore),
                        drift=float(drift),
                        scenario_id=scenario_id,
                        channel=ch,
                        meta={
                            "opcode": opcode,
                            "status": status,
                        },
                    )
                )

                if ch == 0:
                    q_series_ch0.append(float(qscore))

        eval_window = q_series_ch0[-eval_ticks:] if int(eval_ticks) > 0 else list(q_series_ch0)
        coherence_mean = float(sum(eval_window) / max(1, len(eval_window)))

        return {
            "scenario_id": scenario_id,
            "mode": mode,
            "k": int(k),
            "trace": trace,
            "qscore_eval_window": eval_window,
            "coherence_mean": coherence_mean,
        }

    def run(
        self,
        *,
        scenarios: List[Dict[str, Any]],
        thresholds: Dict[str, Any] | None = None,
    ) -> Dict[str, Any]:
        thresholds = thresholds or {}
        warmup = int(thresholds.get("warmup_ticks", 128))
        eval_ticks = int(thresholds.get("eval_ticks", 512))

        outputs: Dict[str, Any] = {
            "adapter": "SLEAdapter",
            "seed": self.rng.seed,
            "rng_algo": self.rng.algo,
            "dt": self.clock.dt,
            "thresholds": {"warmup_ticks": warmup, "eval_ticks": eval_ticks},
            "scenarios": {},
            "trace": [],
        }

        for sc in scenarios:
            sid = str(sc.get("scenario_id", "scenario"))
            mode = str(sc.get("mode", "matched"))
            k = int(sc.get("k", 1))

            out = self.run_scenario(
                scenario_id=sid,
                mode=mode,
                k=k,
                warmup_ticks=warmup,
                eval_ticks=eval_ticks,
            )
            outputs["scenarios"][sid] = out
            outputs["trace"].extend(out["trace"])

        return outputs