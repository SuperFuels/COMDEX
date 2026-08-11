"""Outcome-grounded active grasp search versus the protected v13 control."""
from __future__ import annotations

from typing import Any, Mapping

import numpy as np

from aion_precision_franka_policy import PrecisionFrankaRuntime, digest


_SEARCH: PrecisionFrankaRuntime | None = None
_CONTROL: PrecisionFrankaRuntime | None = None


def propose(*, permitted: Mapping[str, Any], action_space: Any, arm_id: str, **_: Any):
    global _SEARCH, _CONTROL
    rgb = np.asarray(permitted["rgb"], np.uint8)
    pro = np.asarray(permitted["proprioception_bounded"], np.float32)
    episode, step = int(permitted["episode_id"]), int(permitted["timestamp"])
    touch = np.asarray(permitted.get("fingertip_touch", []), np.float32)
    if arm_id == "aion_retained":
        _SEARCH = _SEARCH or PrecisionFrankaRuntime(tactile_direction=-1.0, attachment_search=True)
        values, mode = _SEARCH.propose(rgb, pro, episode, step, touch)
    elif arm_id == "aion_distilled":
        _CONTROL = _CONTROL or PrecisionFrankaRuntime()
        values, mode = _CONTROL.fallback(rgb, pro, episode, step, "protected_v13_comparison")
    else:
        raise RuntimeError("attachment_search_arm_rejected")
    values = np.clip(values, np.asarray(action_space.low), np.asarray(action_space.high)).astype(np.float32)
    if values.shape != tuple(action_space.shape) or not np.all(np.isfinite(values)):
        raise RuntimeError("attachment_search_action_rejected")
    return {
        "values": values,
        "prediction": {"kind": mode, "policy_mode": mode, "teacher_used": False,
                       "runtime_privileged_inputs": [], "abstained": False},
        "action_space_digest": digest({"shape": list(action_space.shape),
                                        "low": np.asarray(action_space.low).tolist(),
                                        "high": np.asarray(action_space.high).tolist(),
                                        "dtype": str(action_space.dtype)}),
    }
