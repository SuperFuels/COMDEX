"""
Tessaris * Symatics Lightwave Capsule (WaveCapsule API)
-------------------------------------------------------
Encapsulates symbolic->photonic wave execution
for ⊕ μ ↔ ⟲ π operators via SymaticsDispatcher.

Determinism:
- If TESSARIS_DETERMINISTIC_TIME=1:
  - MUST NOT use wall-clock time or ambient random for capsule state.
  - MUST avoid non-deterministic side effects (GHX async broadcast) in test/CI paths.
"""

from __future__ import annotations

import os
import hashlib
import logging
from typing import Any, Dict, List

from backend.modules.glyphwave.core.wave_state import WaveState
from backend.modules.codex.beam_event_bus import beam_event_bus, BeamEvent

logger = logging.getLogger(__name__)

_DETERMINISTIC_TIME = os.getenv("TESSARIS_DETERMINISTIC_TIME", "") == "1"
_TEST_QUIET = os.getenv("TESSARIS_TEST_QUIET", "") == "1"


def _stable_unit_float(*parts: Any) -> float:
    """
    Deterministic float in [0,1) derived from stable hash of parts.
    """
    blob = "|".join("" if p is None else str(p) for p in parts).encode("utf-8")
    d = hashlib.sha256(blob).digest()
    n = int.from_bytes(d[:8], "big", signed=False)
    return n / 2**64


def _capsule_id(*parts: Any) -> str:
    blob = "|".join("" if p is None else str(p) for p in parts).encode("utf-8")
    h = hashlib.sha256(blob).hexdigest()
    return f"capsule_{h[:12]}"


class WaveCapsule:
    """
    Encapsulates symbolic operation data + photonic carrier (WaveState).

    NOTE: This class is used by SymaticsDispatcher -> BeamRuntime.
    We keep capsule construction stable under deterministic-time.
    """

    def __init__(
        self,
        opcode: str,
        args: List[Any] | None = None,
        metadata: Dict[str, Any] | None = None,
        container_id: str = "wavecapsule.default",
    ):
        self.opcode = str(opcode)
        self.args = list(args or [])
        self.metadata: Dict[str, Any] = dict(metadata or {})
        self.container_id = str(container_id)

        # Timestamp: deterministic surrogate when deterministic-time is enabled
        if _DETERMINISTIC_TIME:
            # prefer explicit 't' in metadata; otherwise derive from tick/dt; else 0
            if "t" in self.metadata:
                try:
                    self.timestamp = float(self.metadata["t"])
                except Exception:
                    self.timestamp = 0.0
            elif "tick" in self.metadata and "dt" in self.metadata:
                try:
                    self.timestamp = float(self.metadata["tick"]) * float(self.metadata["dt"])
                except Exception:
                    self.timestamp = 0.0
            else:
                self.timestamp = 0.0
        else:
            import time  # local import to avoid import-time side effects
            self.timestamp = time.time()

        # Build wave state with deterministic or ambient properties
        self.wave_state = WaveState()
        self.wave_state.amplitude = 1.0

        if _DETERMINISTIC_TIME:
            seed = self.metadata.get("seed", 0)
            scenario_id = self.metadata.get("scenario_id", "")
            channel = self.metadata.get("channel", 0)
            tick = self.metadata.get("tick", 0)
            # stable phase/coherence based on stable identifiers
            self.wave_state.phase = float(3.14 * _stable_unit_float("phase", seed, scenario_id, channel, tick, self.opcode))
            self.wave_state.coherence = float(0.8 + 0.2 * _stable_unit_float("coh", seed, scenario_id, channel, tick, self.opcode))
            capsule_id = _capsule_id(seed, scenario_id, channel, tick, self.opcode)
        else:
            import random  # local import
            self.wave_state.phase = random.uniform(0.0, 3.14)
            self.wave_state.coherence = random.uniform(0.8, 1.0)
            capsule_id = f"capsule_{int(random.random() * 1e6)}"

        # Ensure wave metadata includes determinism context for downstream runtime/event bus
        ws_meta = {
            "capsule_id": capsule_id,
            "opcode": self.opcode,
            "args": self.args,
            "container_id": self.container_id,
            "timestamp": self.timestamp,
        }
        ws_meta.update({k: self.metadata.get(k) for k in ("seed", "tick", "t", "dt", "scenario_id", "channel") if k in self.metadata})
        self.wave_state.metadata.update(ws_meta)

    @classmethod
    def from_symbolic_instruction(cls, instr: Dict[str, Any]):
        opcode = instr.get("opcode", "NOP")
        args = instr.get("args", [])

        # Preserve determinism context if provided by caller (GX1 SLEAdapter does this)
        meta: Dict[str, Any] = {
            "origin": "symatics_dispatcher",
        }
        for k in ("seed", "tick", "t", "dt", "scenario_id", "channel"):
            if k in instr:
                meta[k] = instr[k]

        return cls(opcode, args, meta)

    def run(self) -> Dict[str, Any]:
        """
        Execute the symbolic opcode via SymaticsDispatcher.
        In deterministic/test-quiet paths, avoid GHX async side effects.
        """
        # Import here to avoid import-time cycles
        from backend.modules.symatics_lightwave.symatics_dispatcher import SymaticsDispatcher

        dispatcher = SymaticsDispatcher()

        start_meta = {
            **(self.wave_state.metadata or {}),
            "opcode": self.opcode,
            "args": self.args,
            "container_id": self.container_id,
            "timestamp": self.timestamp,
            **(self.metadata or {}),
        }

        # Beam bus start (deterministic-safe; BeamEvent itself is gated)
        try:
            beam_event_bus.publish(
                BeamEvent(
                    event_type="wavecapsule_start",
                    source=self.container_id,
                    target="symatics_lightwave",
                    drift=0.0,
                    qscore=1.0,
                    metadata=dict(start_meta),
                )
            )
        except Exception:
            pass

        # GHX broadcasts are intentionally skipped in deterministic-time + quiet/test mode
        if not (_DETERMINISTIC_TIME and _TEST_QUIET):
            try:
                from backend.events.ghx_bus import broadcast as ghx_broadcast  # optional
                import asyncio
                import time as _time

                asyncio.create_task(
                    ghx_broadcast(self.container_id or "ucs_hub", {
                        "event": "wavecapsule_start",
                        "container_id": self.container_id or "ucs_hub",
                        "payload": dict(start_meta),
                        "ts": _time.time(),
                    })
                )
            except Exception:
                pass

        # Dispatch. Keep deterministic context in instruction.
        instr = {"opcode": self.opcode, "args": self.args, **(self.metadata or {})}
        result = dispatcher.dispatch(instr)

        if isinstance(result, dict):
            result.update({
                "wave_id": self.wave_state.metadata.get("wave_id", "anon"),
                "container_id": self.container_id,
                "timestamp": self.timestamp,
            })

        # Beam bus complete
        try:
            beam_event_bus.publish(
                BeamEvent(
                    event_type="wavecapsule_complete",
                    source=self.container_id,
                    target="symatics_lightwave",
                    drift=0.0,
                    qscore=float(getattr(self.wave_state, "coherence", 1.0)),
                    metadata=dict(result) if isinstance(result, dict) else {"result": str(result)},
                )
            )
        except Exception:
            pass

        if not (_DETERMINISTIC_TIME and _TEST_QUIET):
            try:
                from backend.events.ghx_bus import broadcast as ghx_broadcast  # optional
                import asyncio
                import time as _time

                asyncio.create_task(
                    ghx_broadcast(self.container_id or "ucs_hub", {
                        "event": "wavecapsule_complete",
                        "container_id": self.container_id or "ucs_hub",
                        "coherence": getattr(self.wave_state, "coherence", None),
                        "opcode": self.opcode,
                        "args": self.args,
                        "result": result,
                        "ts": _time.time(),
                    })
                )
            except Exception:
                pass

        if not _TEST_QUIET:
            logger.info(f"[WaveCapsule] {self.opcode} executed -> coherence={getattr(self.wave_state, 'coherence', None)!s}")
        return result if isinstance(result, dict) else {"status": "ok", "result": result}

    def __repr__(self):
        return f"<WaveCapsule opcode={self.opcode} phase={self.wave_state.phase:.2f} coh={self.wave_state.coherence:.2f}>"


def run_symatics_wavecapsule(spec: Dict[str, Any]) -> Dict[str, Any]:
    """
    Execute a single symbolic-photonic op via WaveCapsule API.
    """
    opcode = spec.get("opcode", "NOP")
    args = spec.get("args", [])
    container_id = spec.get("container_id", "wavecapsule.default")

    # Preserve determinism context
    meta: Dict[str, Any] = {}
    for k in ("seed", "tick", "t", "dt", "scenario_id", "channel"):
        if k in spec:
            meta[k] = spec[k]

    capsule = WaveCapsule(str(opcode), list(args), meta, str(container_id))
    return capsule.run()
