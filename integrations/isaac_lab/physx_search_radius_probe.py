"""Matched development probe for contact-search spatial coverage."""
from __future__ import annotations

from typing import Any, Mapping

import numpy as np

from aion_precision_franka_policy import PrecisionFrankaRuntime, digest


_RUNTIMES: dict[str, PrecisionFrankaRuntime] = {}


def propose(*, permitted: Mapping[str, Any], action_space: Any, arm_id: str, **_: Any):
    configuration = {
        "aion_retained": (.015, "single_scale"),
        "aion_distilled": (.015, "coarse_to_fine"),
    }.get(arm_id)
    if configuration is None:
        raise RuntimeError("search_radius_probe_arm_rejected")
    if arm_id not in _RUNTIMES:
        radius, strategy = configuration
        _RUNTIMES[arm_id] = PrecisionFrankaRuntime(
            tactile_direction=-1.0, attachment_search=True,
            search_radius=radius, search_strategy=strategy,
        )
    rgb = np.asarray(permitted["rgb"], np.uint8)
    pro = np.asarray(permitted["proprioception_bounded"], np.float32)
    values, mode = _RUNTIMES[arm_id].propose(
        rgb, pro, int(permitted["episode_id"]), int(permitted["timestamp"]),
        np.asarray(permitted.get("fingertip_touch", []), np.float32),
    )
    values = np.clip(values, np.asarray(action_space.low), np.asarray(action_space.high)).astype(np.float32)
    return {"values": values,
            "prediction": {"policy_mode": mode, "teacher_used": False,
                           "runtime_privileged_inputs": [], "abstained": False},
            "action_space_digest": digest({"shape": list(action_space.shape),
                                            "low": np.asarray(action_space.low).tolist(),
                                            "high": np.asarray(action_space.high).tolist(),
                                            "dtype": str(action_space.dtype)})}
