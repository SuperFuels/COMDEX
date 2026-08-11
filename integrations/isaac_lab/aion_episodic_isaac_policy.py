"""Isaac adapter for AION's teacher-removed episodic skill memory."""
from __future__ import annotations
import hashlib, json, os
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Mapping
import numpy as np
import torch
from backend.modules.hexcore.episodic_embodied_skill_memory import load_runtime

_LOADED = None
def _digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode()).hexdigest()
def _runtime():
    global _LOADED
    manifest, archive = Path(os.environ["AION_EPISODIC_MANIFEST"]), Path(os.environ["AION_EPISODIC_ARCHIVE"])
    identity = hashlib.sha256(manifest.read_bytes() + archive.read_bytes()).hexdigest()
    if _LOADED is None or _LOADED.identity != identity:
        _LOADED = SimpleNamespace(identity=identity, runtime=load_runtime(
            manifest, archive, device=("cuda" if torch.cuda.is_available() else "cpu")))
    return _LOADED
def propose(*, permitted: Mapping[str, Any], action_space: Any, arm_id: str, **_: Any):
    if arm_id == "aion_cold":
        result = {"abstain": False, "values": np.zeros(action_space.shape, dtype=np.float32),
                  "teacher_used": False, "policy_mode": "matched_memory_free_cold_control"}
    elif arm_id == "aion_distilled":
        result = _runtime().runtime.propose(np.asarray(permitted["rgb"], dtype=np.uint8),
            np.asarray(permitted["proprioception_bounded"], dtype=np.float32),
            episode_id=int(permitted["episode_id"]), step=int(permitted["timestamp"]))
    else: raise RuntimeError("episodic_adapter_arm_mismatch")
    values = (np.zeros(action_space.shape, dtype=np.float32) if result.get("abstain") else
              np.asarray(result["values"], dtype=np.float32).reshape(action_space.shape))
    values = np.clip(values, np.asarray(action_space.low), np.asarray(action_space.high)).astype(np.float32)
    return {"values": values, "prediction": {"kind": result.get("policy_mode"),
            "teacher_used": False, "abstained": bool(result.get("abstain")),
            "reason": result.get("reason"), "distance": result.get("distance"),
            "policy_mode": result.get("policy_mode"), "capsule_digest": result.get("capsule_digest")},
            "action_space_digest": _digest({"shape": list(action_space.shape),
            "low": np.asarray(action_space.low).tolist(), "high": np.asarray(action_space.high).tolist(),
            "dtype": str(action_space.dtype)})}
