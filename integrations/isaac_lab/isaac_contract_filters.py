"""Pure fail-closed filters shared by local tests and the Isaac cloud runner."""
from __future__ import annotations

import hashlib
from collections.abc import Mapping
from typing import Any, Callable

import numpy as np


PROHIBITED = {"privileged_object_pose", "privileged_target_pose", "simulator_reward",
              "ground_truth_contact_graph", "future_outcome"}


def permitted_observation(observation: Mapping[str, Any], rgb_value: Any,
                          proprioception: Any, episode: int, step: int,
                          convert: Callable[[Any], Any] | None = None,
                          fingertip_touch: Any | None = None) -> dict[str, Any]:
    convert = convert or (lambda value: value)
    if PROHIBITED & set(observation):
        raise RuntimeError("privileged_observation_field_detected")
    flattened = convert(observation)
    images: list[np.ndarray] = [np.asarray(convert(rgb_value))]

    def visit(value: Any) -> None:
        if isinstance(value, Mapping):
            for key, item in value.items():
                if key in PROHIBITED:
                    raise RuntimeError("privileged_observation_field_detected")
                visit(item)
        elif isinstance(value, np.ndarray) and value.ndim >= 3 and value.shape[-1] in (3, 4):
            images.append(value[..., :3])

    visit(flattened)
    valid = [image for image in images if image.ndim in (3, 4) and image.shape[-1] in (3, 4)]
    if not valid:
        raise RuntimeError("rgb_observation_required_by_frozen_contract")
    rgb = np.asarray(valid[0])[..., :3]
    if rgb.ndim == 4:
        rgb = rgb[0]
    if min(rgb.shape[:2]) < 64:
        raise RuntimeError("rgb_resolution_below_contract")
    if rgb.dtype != np.uint8:
        if np.issubdtype(rgb.dtype, np.floating) and float(np.max(rgb)) <= 1.0:
            rgb = np.clip(rgb * 255.0, 0, 255).astype(np.uint8)
        else:
            rgb = np.clip(rgb, 0, 255).astype(np.uint8)
    proprio = np.asarray(convert(proprioception), dtype=np.float32).reshape(-1)
    if not np.all(np.isfinite(proprio)) or proprio.size > 128:
        raise RuntimeError("invalid_bounded_proprioception")
    result = {"rgb": rgb, "timestamp": step, "episode_id": episode,
            "observation_sha256": hashlib.sha256(rgb.tobytes()).hexdigest(),
            "proprioception_bounded": proprio,
            "proprioception_sha256": hashlib.sha256(proprio.tobytes()).hexdigest()}
    if fingertip_touch is not None:
        touch = np.asarray(convert(fingertip_touch), dtype=np.float32).reshape(-1)
        if touch.size not in (2, 3, 4, 5, 10) or not np.all(np.isfinite(touch)):
            raise RuntimeError("invalid_bounded_fingertip_touch")
        if np.any(touch < 0.0) or np.any(touch > 250.0):
            raise RuntimeError("fingertip_touch_outside_safety_contract")
        result["fingertip_touch"] = touch
        result["fingertip_touch_sha256"] = hashlib.sha256(touch.tobytes()).hexdigest()
    return result
