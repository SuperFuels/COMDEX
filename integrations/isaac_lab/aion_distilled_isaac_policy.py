"""Teacher-absent Isaac policy adapter for verified AION skill capsules."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any, Mapping

import numpy as np

from backend.modules.hexcore.verified_embodied_skill_distillation import reconstruct


_LOADED: tuple[str, Any] | None = None


def _digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                                     default=str).encode()).hexdigest()


def _load():
    global _LOADED
    path = Path(os.environ["AION_EMBODIED_CAPSULE"])
    raw = path.read_bytes()
    identity = hashlib.sha256(raw).hexdigest()
    if _LOADED is None or _LOADED[0] != identity:
        _LOADED = (identity, reconstruct(json.loads(raw)))
    return _LOADED


def propose(*, permitted: Mapping[str, Any], action_space: Any, arm_id: str, **_: Any) -> dict[str, Any]:
    if arm_id == "aion_cold":
        values = np.zeros(action_space.shape, dtype=np.float32)
        flat = values.reshape(-1)
        if flat.size:
            index = (int(permitted["timestamp"]) * 5 + int(permitted["episode_id"])) % flat.size
            flat[index] = 0.08 if int(permitted["timestamp"]) % 2 == 0 else -0.08
        return {
            "values": np.clip(values, np.asarray(action_space.low), np.asarray(action_space.high)),
            "prediction": {"kind": "matched_memory_free_cold_control", "teacher_used": False},
            "action_space_digest": _digest({
                "shape": list(action_space.shape), "low": np.asarray(action_space.low).tolist(),
                "high": np.asarray(action_space.high).tolist(), "dtype": str(action_space.dtype),
            }),
        }
    if arm_id != "aion_distilled":
        raise RuntimeError("distilled_adapter_arm_mismatch")
    capsule_sha, policy = _load()
    result = policy.propose(np.asarray(permitted["rgb"], dtype=np.uint8),
                            np.asarray(permitted["proprioception_bounded"], dtype=np.float32),
                            episode_id=int(permitted["episode_id"]), step=int(permitted["timestamp"]))
    if result.get("abstain"):
        values = np.zeros(action_space.shape, dtype=np.float32)
    else:
        values = np.asarray(result["values"], dtype=np.float32).reshape(action_space.shape)
    values = np.clip(values, np.asarray(action_space.low), np.asarray(action_space.high)).astype(np.float32)
    return {
        "values": values,
        "prediction": {
            "kind": "verified_teacher_removed_skill_capsule", "abstained": bool(result.get("abstain")),
            "capsule_file_sha256": capsule_sha, "capsule_digest": result.get("capsule_digest"),
            "teacher_used": False, "distance": result.get("distance"), "reason": result.get("reason"),
            "policy_mode": result.get("policy_mode"), "sequence_index": result.get("sequence_index"),
        },
        "action_space_digest": _digest({
            "shape": list(action_space.shape), "low": np.asarray(action_space.low).tolist(),
            "high": np.asarray(action_space.high).tolist(), "dtype": str(action_space.dtype),
        }),
    }
