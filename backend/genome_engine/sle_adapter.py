from __future__ import annotations

import os
import hashlib
from typing import Any, Dict, List

from .determinism import TickClock, SeededRNG
from .event_envelope import beam_event_envelope

from backend.modules.symatics_lightwave.symatics_dispatcher import SymaticsDispatcher
from backend.modules.symatics_lightwave.wave_capsule import WaveCapsule
from backend.modules.codex.beam_event_bus import beam_event_bus, BeamEvent


OPCODE_PLAN: Dict[str, List[str]] = {
    "matched": ["⊕", "⟲", "π"],
    "mismatch": ["μ", "μ", "π"],
    "multiplex": ["⊕", "↔", "⟲", "π"],
    "mutation": ["⊕", "⟲", "μ", "π"],
}

_DETERMINISTIC_TRACE = os.getenv("TESSARIS_DETERMINISTIC_TIME", "") == "1"


def _stable_unit_float(*parts: Any) -> float:
    blob = "|".join(str(p) for p in parts).encode("utf-8")
    digest = hashlib.sha256(blob).digest()
    n = int.from_bytes(digest[:8], "big", signed=False)
    return n / 2**64


class SLEAdapter:
    """
    Deterministic SLE/Beam execution adapter for GX1.

    B03 path (explicit):
      SLEAdapter plan → WaveCapsule.from_symbolic_instruction →
      SymaticsDispatcher.dispatch_capsule → BeamRuntime → BeamEventBus

    TRACE remains normalized through beam_event_envelope (contract surface).
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
        total_ticks = max(warmup_ticks + eval_ticks, warmup_ticks)

        trace: List[Dict[str, Any]] = []
        q_series_ch0: List[float] = []

        ops = self._scenario_ops(mode)
        k = max(1, int(k))

        # B03c: capture BeamEventBus stream during this scenario only
        def _beam_to_gx1_envelope(ev: BeamEvent) -> Dict[str, Any] | None:
            md = getattr(ev, "metadata", None) or {}

            # Filter strictly to this scenario to avoid global noise
            if str(md.get("scenario_id", "")) != str(scenario_id):
                return None

            # Require tick to anchor determinism + GX1 envelope
            if "tick" not in md:
                return None
            try:
                tick_i = int(md["tick"])
            except Exception:
                return None

            # Channel is optional; default 0
            try:
                ch_i = int(md.get("channel", md.get("ch", 0)))
            except Exception:
                ch_i = 0

            # Prefer explicit 't', else derive from tick*dt (fall back to clock.dt)
            if "t" in md:
                try:
                    t_f = float(md["t"])
                except Exception:
                    t_f = float(tick_i) * float(md.get("dt", self.clock.dt))
            else:
                try:
                    t_f = float(tick_i) * float(md.get("dt", self.clock.dt))
                except Exception:
                    t_f = float(tick_i)

            meta_out = dict(md)
            meta_out.setdefault("beam_event_id", getattr(ev, "id", None))
            meta_out.setdefault("beam_timestamp", getattr(ev, "timestamp", None))
            meta_out.setdefault("mode", mode)

            return beam_event_envelope(
                tick=tick_i,
                t=t_f,
                event_type=str(getattr(ev, "event_type", "")),
                source=str(getattr(ev, "source", "")),
                target=str(getattr(ev, "target", "")),
                qscore=float(getattr(ev, "qscore", 1.0)),
                drift=float(getattr(ev, "drift", 0.0)),
                scenario_id=str(scenario_id),
                channel=ch_i,
                meta=meta_out,
            )

        def _collector(ev: BeamEvent) -> None:
            env = _beam_to_gx1_envelope(ev)
            if env is not None:
                trace.append(env)

        beam_event_bus.subscribe("*", _collector)
        try:
            for tick in range(int(total_ticks)):
                t = self.clock.t(tick)

                for ch in range(k):
                    opcode = ops[(tick + ch) % len(ops)]

                    instr = {
                        "opcode": opcode,
                        "args": [scenario_id, ch, tick],
                        # determinism context (propagates into capsule metadata + BeamRuntime)
                        "seed": self.rng.seed,
                        "tick": tick,
                        "t": t,
                        "dt": self.clock.dt,
                        "scenario_id": scenario_id,
                        "channel": ch,
                        "mode": mode,
                    }

                    # B03: build capsule explicitly, then dispatch it
                    capsule = WaveCapsule.from_symbolic_instruction(instr)
                    result = self.dispatcher.dispatch_capsule(capsule)

                    # Keep deterministic qscore series for metrics window (independent of bus capture)
                    if _DETERMINISTIC_TRACE:
                        qscore = 0.5 + 0.5 * _stable_unit_float(
                            self.rng.seed, scenario_id, mode, opcode, ch, tick, "q"
                        )
                    else:
                        qscore = float(result.get("coherence", 1.0)) if isinstance(result, dict) else 1.0

                    if ch == 0:
                        q_series_ch0.append(float(qscore))
        finally:
            beam_event_bus.unsubscribe("*", _collector)

        eval_window = q_series_ch0[-eval_ticks:] if int(eval_ticks) > 0 else list(q_series_ch0)
        coherence_mean = float(sum(eval_window) / max(1, len(eval_window)))

        # --- GX1 legacy contract pair (keep Mode B compatible with SIM trace expectations)
        # Append at end so consumers can find summaries even if TRACE is mostly beam_event lines.
        trace.append(
            {
                "trace_kind": "scenario_summary",
                "scenario_id": str(scenario_id),
                "mode": str(mode),
                "k": int(k),
                # Benchmark proxy: we treat coherence_mean as rho_primary for Mode B
                "rho_primary": float(coherence_mean),
                "coherence_mean": float(coherence_mean),
                "drift_mean": 0.0,
                "crosstalk_max": 0.0,
            }
        )
        trace.append(
            {
                "trace_kind": "rho_trace_eval_window",
                "scenario_id": str(scenario_id),
                "warmup_ticks": int(warmup_ticks),
                "eval_ticks": int(eval_ticks),
                # Mode B: qscore series is the eval window proxy
                "rho_trace": [float(x) for x in eval_window],
            }
        )

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