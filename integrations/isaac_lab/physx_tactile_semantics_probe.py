"""Matched causal probe for the sign of Franka tactile corrections."""
from __future__ import annotations

from typing import Any, Mapping

import numpy as np

from aion_precision_franka_policy import (
    PrecisionFrankaRuntime,
    digest,
)


_RUNTIMES: dict[str, PrecisionFrankaRuntime] = {}


def _runtime(arm_id: str) -> PrecisionFrankaRuntime:
    # Reuse the runner's governed arm vocabulary; within this development-only
    # plugin the two IDs denote opposite causal hypotheses, not champions.
    direction = {"aion_retained": 1.0, "aion_distilled": -1.0}.get(arm_id)
    if direction is None:
        raise RuntimeError("tactile_semantics_probe_arm_rejected")
    if arm_id not in _RUNTIMES:
        _RUNTIMES[arm_id] = PrecisionFrankaRuntime(tactile_direction=direction)
        # Isaac contact bursts are usually 1--3 frames.  This development-only
        # causal probe shortens persistence; the production capsule is never
        # mutated by the experiment.
        _RUNTIMES[arm_id].tactile.capsule["persistent_one_sided_steps"] = 2
    return _RUNTIMES[arm_id]


def propose(*, permitted: Mapping[str, Any], action_space: Any, arm_id: str, **_: Any):
    rgb = np.asarray(permitted["rgb"], np.uint8)
    pro = np.asarray(permitted["proprioception_bounded"], np.float32)
    values, mode = _runtime(arm_id).propose(
        rgb, pro, int(permitted["episode_id"]), int(permitted["timestamp"]),
        np.asarray(permitted.get("fingertip_touch", []), np.float32),
    )
    values = np.clip(values, np.asarray(action_space.low), np.asarray(action_space.high)).astype(np.float32)
    if values.shape != tuple(action_space.shape) or not np.all(np.isfinite(values)):
        raise RuntimeError("tactile_semantics_probe_action_rejected")
    return {
        "values": values,
        "prediction": {"kind": mode, "policy_mode": mode, "teacher_used": False,
                       "runtime_privileged_inputs": [], "abstained": False},
        "action_space_digest": digest({"shape": list(action_space.shape),
                                        "low": np.asarray(action_space.low).tolist(),
                                        "high": np.asarray(action_space.high).tolist(),
                                        "dtype": str(action_space.dtype)}),
    }
