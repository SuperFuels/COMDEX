"""Fail-fast PhysX probe for the direct bounded joint-position IK servo."""
from __future__ import annotations

import numpy as np

from aion_precision_franka_policy import PrecisionFrankaRuntime, digest


_RUNTIME = None


def runtime() -> PrecisionFrankaRuntime:
    global _RUNTIME
    if _RUNTIME is None:
        _RUNTIME = PrecisionFrankaRuntime(
            # Retain the direction with the longer clean object-contact window;
            # the declared-sign challenger reduced contact from 57 to 20 frames.
            tactile_direction=-1.0,
            attachment_search=True,
            search_radius=.015,
            search_strategy="single_scale",
            precision_contact=True,
            direct_joint_servo=True,
            # This probe observed a real 7.9 mm cube rise at 28.26 mm finger
            # width with a 0.857 force ratio. Admit that measured attached
            # state; post-action cube height remains the success authority.
            exploratory_width_margin=.003,
        )
    return _RUNTIME


def propose(*, permitted, action_space, arm_id, **_):
    if arm_id != "aion_retained":
        raise RuntimeError("direct_joint_ik_probe_arm_rejected")
    values, mode = runtime().propose(
        np.asarray(permitted["rgb"], np.uint8),
        np.asarray(permitted["proprioception_bounded"], np.float32),
        int(permitted["episode_id"]),
        int(permitted["timestamp"]),
        np.asarray(permitted.get("fingertip_touch", []), np.float32),
    )
    values = np.clip(values, np.asarray(action_space.low), np.asarray(action_space.high)).astype(np.float32)
    if values.shape != tuple(action_space.shape) or not np.all(np.isfinite(values)):
        raise RuntimeError("direct_joint_ik_action_contract_failure")
    return {
        "values": values,
        "prediction": {
            "kind": mode,
            "policy_mode": mode,
            "teacher_used": False,
            "runtime_privileged_inputs": [],
            "direct_joint_position_servo": True,
            "abstained": False,
        },
        "action_space_digest": digest({
            "shape": list(action_space.shape),
            "low": np.asarray(action_space.low).tolist(),
            "high": np.asarray(action_space.high).tolist(),
            "dtype": str(action_space.dtype),
        }),
    }
