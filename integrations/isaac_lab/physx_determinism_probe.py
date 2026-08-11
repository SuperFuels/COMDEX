"""Identical frozen controllers for matched PhysX repeatability audits."""
from __future__ import annotations

from typing import Any, Mapping

import numpy as np

from aion_precision_franka_policy import PrecisionFrankaRuntime, digest


_RUNTIMES: dict[str, PrecisionFrankaRuntime] = {}


def propose(*, permitted: Mapping[str, Any], action_space: Any, arm_id: str, **_: Any):
    if arm_id not in {"aion_retained", "aion_distilled"}:
        raise RuntimeError("determinism_probe_arm_rejected")
    if arm_id not in _RUNTIMES:
        _RUNTIMES[arm_id] = PrecisionFrankaRuntime(
            tactile_direction=-1.0,
            attachment_search=True,
            search_radius=.015,
            search_strategy="single_scale",
        )
    values, mode = _RUNTIMES[arm_id].propose(
        np.asarray(permitted["rgb"], np.uint8),
        np.asarray(permitted["proprioception_bounded"], np.float32),
        int(permitted["episode_id"]),
        int(permitted["timestamp"]),
        np.asarray(permitted.get("fingertip_touch", []), np.float32),
    )
    values = np.clip(values, np.asarray(action_space.low), np.asarray(action_space.high)).astype(np.float32)
    return {
        "values": values,
        "prediction": {"policy_mode": mode, "teacher_used": False,
                       "runtime_privileged_inputs": [], "abstained": False},
        "action_space_digest": digest({
            "shape": list(action_space.shape), "low": np.asarray(action_space.low).tolist(),
            "high": np.asarray(action_space.high).tolist(), "dtype": str(action_space.dtype),
        }),
    }
