"""Fail-closed tactile contract for AION hand transfer into Isaac Lab.

This module intentionally contains no simulator-state fallback.  It accepts
only body-local contact-force reports from declared fingertip bodies and emits
bounded tactile magnitudes suitable for the proposal boundary.
"""
from __future__ import annotations

import hashlib
from collections.abc import Mapping, Sequence
from typing import Any

import numpy as np


MAX_DIGITS = 24
MAX_FORCE_NEWTONS = 250.0


def bounded_fingertip_touch(
    body_forces: Mapping[str, Any],
    discovered_digit_order: Sequence[str],
    *,
    maximum_force: float = MAX_FORCE_NEWTONS,
) -> dict[str, Any]:
    """Normalize only predeclared fingertip force vectors; reject all extras."""
    names = tuple(str(name) for name in discovered_digit_order)
    if not names or len(names) > MAX_DIGITS or len(set(names)) != len(names):
        raise RuntimeError("invalid_discovered_digit_order")
    if set(body_forces) != set(names):
        raise RuntimeError("tactile_body_contract_mismatch")
    magnitudes = []
    for name in names:
        vector = np.asarray(body_forces[name], dtype=np.float32).reshape(-1)
        if vector.shape not in {(3,), (6,)} or not np.all(np.isfinite(vector)):
            raise RuntimeError("invalid_fingertip_force_vector")
        magnitude = float(np.linalg.norm(vector[:3]))
        if magnitude > maximum_force:
            raise RuntimeError("fingertip_force_exceeds_safety_contract")
        magnitudes.append(magnitude)
    bounded = np.asarray(magnitudes, dtype=np.float32)
    return {
        "fingertip_touch": bounded,
        "digit_order": names,
        "touch_sha256": hashlib.sha256(bounded.tobytes()).hexdigest(),
        "contact_threshold_newtons": 0.5,
        "privileged_contact_geometry": False,
    }


def isaac_contact_sensor_config(prim_path: str, target_filter: str | None = None):
    """Construct the official Isaac Lab sensor lazily inside its GPU runtime."""
    if not prim_path.startswith("/World/envs/env_.*/") or ".." in prim_path:
        raise RuntimeError("unsafe_contact_sensor_prim_path")
    from isaaclab.sensors import ContactSensorCfg

    kwargs: dict[str, Any] = {
        "prim_path": prim_path,
        "update_period": 0.0,
        "history_length": 3,
        "debug_vis": False,
    }
    if target_filter:
        if not target_filter.startswith("/World/envs/env_.*/") or ".." in target_filter:
            raise RuntimeError("unsafe_contact_filter_path")
        kwargs["filter_prim_paths_expr"] = [target_filter]
    return ContactSensorCfg(**kwargs)

