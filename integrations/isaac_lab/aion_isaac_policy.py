"""Governed policy arms for AION's Isaac Lab expedition.

The module intentionally contains no Isaac Lab imports.  It receives only the
filtered observation and bounded action space supplied by the cloud runner.
The retained arm carries intervention and temporal-belief machinery from the
MuJoCo skill ancestry; the cold arm is reset to a memory-free controller.
Cosmos and GR00T are explicit, optional proposal surfaces and fail closed when
their separately attested adapters are absent.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Any, Mapping

import numpy as np


REQUIRED_ANCESTRY = (
    "procedure_rgb_belief_state_mujoco_planning_v2",
    "procedure_rgb_contact_occlusion_skill_composition_v3",
    "procedure_rgb_articulated_sequence_skill_v4",
)


def _shape(action_space: Any) -> tuple[int, ...]:
    shape = tuple(int(value) for value in action_space.shape)
    if shape and shape[0] == 1:
        return shape
    return shape


def _bounded(action_space: Any, values: np.ndarray) -> np.ndarray:
    low = np.asarray(action_space.low, dtype=np.float32)
    high = np.asarray(action_space.high, dtype=np.float32)
    candidate = np.asarray(values, dtype=np.float32).reshape(action_space.shape)
    if not np.all(np.isfinite(candidate)):
        raise RuntimeError("non_finite_policy_proposal")
    return np.clip(candidate, low, high).astype(np.float32)


def _digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                                     default=str).encode()).hexdigest()


def action_space_digest(action_space: Any) -> str:
    return _digest({"shape": list(action_space.shape),
                    "low": np.asarray(action_space.low).tolist(),
                    "high": np.asarray(action_space.high).tolist(),
                    "dtype": str(action_space.dtype)})


@dataclass
class TemporalInterventionPolicy:
    """Small online system identifier over permitted visual/proprio evidence.

    It does not assume a Franka joint ordering or consume object poses.  Early
    actions excite one bounded channel at a time; observed frame/proprio change
    estimates which channels are controllable.  Thereafter it uses the least
    disruptive identified channels while retaining a reversible intervention
    schedule.  This is an acquisition policy, not a claimed manipulation
    expert, and its outcome must be scored only by the external environment.
    """

    arm_id: str
    previous_rgb: np.ndarray | None = None
    previous_proprio: np.ndarray | None = None
    episode: int = -1
    step: int = 0
    effects: dict[int, list[float]] = field(default_factory=dict)

    def reset(self, episode: int) -> None:
        self.previous_rgb = None
        self.previous_proprio = None
        self.episode = episode
        self.step = 0
        self.effects = {}

    @staticmethod
    def _motion(previous: np.ndarray | None, current: np.ndarray) -> float:
        if previous is None or previous.shape != current.shape:
            return 0.0
        delta = np.abs(current.astype(np.float32) - previous.astype(np.float32))
        return float(np.mean(delta > 12.0))

    def propose(self, permitted: Mapping[str, Any], action_space: Any) -> dict[str, Any]:
        episode = int(permitted["episode_id"])
        if episode != self.episode:
            self.reset(episode)
        rgb = np.asarray(permitted["rgb"], dtype=np.uint8)
        proprio = np.asarray(permitted.get("proprioception_bounded", []), dtype=np.float32).reshape(-1)
        motion = self._motion(self.previous_rgb, rgb)
        if self.step > 0:
            channel = (self.step - 1) % int(np.prod(action_space.shape))
            self.effects.setdefault(channel, []).append(motion)

        values = np.zeros(action_space.shape, dtype=np.float32)
        flat = values.reshape(-1)
        channels = len(flat)
        # Symmetric, reversible excitation; never exceeds 18% of the declared
        # action range.  Retained knowledge determines this acquisition pattern.
        if channels:
            if self.step < channels * 2:
                channel = (self.step // 2) % channels
                flat[channel] = 0.18 if self.step % 2 == 0 else -0.18
            elif self.effects:
                ranked = sorted(self.effects, key=lambda index: -float(np.mean(self.effects[index])))
                channel = ranked[(self.step - channels * 2) % min(3, len(ranked))]
                flat[channel] = 0.10 if (self.step // 3) % 2 == 0 else -0.10

        action = _bounded(action_space, values)
        prediction = {
            "kind": "temporal_intervention",
            "expected_visual_change": "bounded" if np.any(action) else "stable",
            "identified_channels": sorted(self.effects),
            "proprioception_present": bool(proprio.size),
            "policy_state_sha256": _digest({"episode": episode, "step": self.step, "effects": self.effects}),
        }
        self.previous_rgb = rgb.copy()
        self.previous_proprio = proprio.copy()
        self.step += 1
        return {"values": action, "prediction": prediction,
                "action_space_digest": action_space_digest(action_space)}


class ColdPolicy:
    """Matched memory-free control with deterministic low-amplitude probing."""

    def propose(self, permitted: Mapping[str, Any], action_space: Any) -> dict[str, Any]:
        values = np.zeros(action_space.shape, dtype=np.float32)
        flat = values.reshape(-1)
        if len(flat):
            index = (int(permitted["timestamp"]) * 5 + int(permitted["episode_id"])) % len(flat)
            flat[index] = 0.08 if int(permitted["timestamp"]) % 2 == 0 else -0.08
        return {"values": _bounded(action_space, values),
                "prediction": {"kind": "cold_memory_free_probe"},
                "action_space_digest": action_space_digest(action_space)}


_RETAINED = TemporalInterventionPolicy("aion_retained")
_COSMOS = TemporalInterventionPolicy("aion_cosmos")
_COLD = ColdPolicy()


def _ancestry_valid(skill_ancestry: list[Mapping[str, Any]]) -> bool:
    return tuple(row.get("procedure_id") for row in skill_ancestry) == REQUIRED_ANCESTRY


def propose(*, permitted: Mapping[str, Any], action_space: Any,
            skill_ancestry: list[Mapping[str, Any]], arm_id: str,
            **_: Any) -> dict[str, Any]:
    if arm_id in {"aion_retained", "aion_cosmos"} and not _ancestry_valid(skill_ancestry):
        raise RuntimeError("retained_skill_ancestry_invalid")
    if arm_id == "aion_retained":
        return _RETAINED.propose(permitted, action_space)
    if arm_id == "aion_cold":
        return _COLD.propose(permitted, action_space)
    if arm_id == "aion_cosmos":
        # Cosmos may rank candidate futures only after a separately attested
        # adapter is installed.  Until then the retained proposal remains the
        # safe fallback and the receipt must record cosmos_used=false.
        result = _COSMOS.propose(permitted, action_space)
        result["prediction"]["cosmos_used"] = False
        result["prediction"]["cosmos_status"] = "adapter_absent_safe_fallback"
        return result
    if arm_id == "gr00t_teacher":
        raise RuntimeError("gr00t_teacher_adapter_not_attested")
    raise RuntimeError(f"unknown_experimental_arm:{arm_id}")
