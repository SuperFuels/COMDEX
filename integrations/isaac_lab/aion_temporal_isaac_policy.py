"""Isaac plugin for AION's teacher-removed temporal skill capsule."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Mapping

import numpy as np
import torch

from backend.modules.hexcore.temporal_object_centric_embodied_policy import load_runtime


_LOADED: SimpleNamespace | None = None


def _digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                                     default=str).encode()).hexdigest()


def _runtime():
    global _LOADED
    manifest = Path(os.environ["AION_TEMPORAL_MANIFEST"])
    weights = Path(os.environ["AION_TEMPORAL_WEIGHTS"])
    identity = hashlib.sha256(manifest.read_bytes() + weights.read_bytes()).hexdigest()
    if _LOADED is None or _LOADED.identity != identity:
        device = "cuda" if torch.cuda.is_available() else "cpu"
        _LOADED = SimpleNamespace(identity=identity,
                                  runtime=load_runtime(manifest, weights, device=device))
    return _LOADED


def propose(*, permitted: Mapping[str, Any], action_space: Any, arm_id: str, **_: Any):
    if arm_id == "aion_cold":
        values = np.zeros(action_space.shape, dtype=np.float32)
        return {"values": values,
                "prediction": {"kind": "matched_memory_free_cold_control", "teacher_used": False},
                "action_space_digest": _digest({"shape": list(action_space.shape),
                                                 "low": np.asarray(action_space.low).tolist(),
                                                 "high": np.asarray(action_space.high).tolist(),
                                                 "dtype": str(action_space.dtype)})}
    if arm_id != "aion_distilled":
        raise RuntimeError("temporal_adapter_arm_mismatch")
    loaded = _runtime()
    result = loaded.runtime.propose(
        np.asarray(permitted["rgb"], dtype=np.uint8),
        np.asarray(permitted["proprioception_bounded"], dtype=np.float32),
        episode_id=int(permitted["episode_id"]), step=int(permitted["timestamp"]),
    )
    values = (np.zeros(action_space.shape, dtype=np.float32) if result.get("abstain")
              else np.asarray(result["values"], dtype=np.float32).reshape(action_space.shape))
    values = np.clip(values, np.asarray(action_space.low), np.asarray(action_space.high)).astype(np.float32)
    return {"values": values,
            "prediction": {"kind": "teacher_removed_temporal_object_policy",
                           "teacher_used": False, "abstained": bool(result.get("abstain")),
                           "reason": result.get("reason"), "policy_mode": result.get("policy_mode"),
                           "capsule_digest": result.get("capsule_digest")},
            "action_space_digest": _digest({"shape": list(action_space.shape),
                                             "low": np.asarray(action_space.low).tolist(),
                                             "high": np.asarray(action_space.high).tolist(),
                                             "dtype": str(action_space.dtype)})}
