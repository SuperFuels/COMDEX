"""Digest-bound episodic visual skill memory for teacher-removed control."""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

import numpy as np
import torch
from torch.nn import functional as F


SCHEMA = "aion.episodic_embodied_skill_memory.v1"


def sha256(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            value.update(block)
    return value.hexdigest()


def digest(value: Mapping[str, Any]) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                                     default=str).encode()).hexdigest()


def spatial_state(rgb: np.ndarray, previous: np.ndarray, proprio: np.ndarray, step: int,
                  *, proprio_mean: np.ndarray, proprio_scale: np.ndarray) -> np.ndarray:
    pair = np.concatenate((np.asarray(rgb)[..., :3], np.asarray(previous)[..., :3]), axis=-1)
    tensor = torch.as_tensor(pair[None]).permute(0, 3, 1, 2).float() / 255.0
    pooled = F.interpolate(tensor, size=(24, 32), mode="bilinear", align_corners=False)[0]
    # Preserve spatial geometry; per-channel centering removes global lighting
    # shifts without erasing the cube, gripper or goal marker.
    pooled = pooled - pooled.mean(dim=(1, 2), keepdim=True)
    visual = pooled.reshape(-1).numpy()
    sensed = (np.asarray(proprio, dtype=np.float32) - proprio_mean) / proprio_scale
    phase = np.asarray([min(max(step, 0), 250) / 250.0], dtype=np.float32)
    return np.concatenate((visual, sensed * 2.0, phase)).astype(np.float32)


@dataclass
class EpisodicSkillRuntime:
    manifest: Mapping[str, Any]
    states: torch.Tensor
    actions: torch.Tensor
    steps: torch.Tensor
    device: torch.device
    previous_rgb: np.ndarray | None = None
    episode_id: int | None = None

    def propose(self, rgb: np.ndarray, proprioception: np.ndarray, *, episode_id: int,
                step: int) -> dict[str, Any]:
        rgb = np.asarray(rgb, dtype=np.uint8)[..., :3]
        proprio = np.asarray(proprioception, dtype=np.float32).reshape(-1)
        if self.episode_id != episode_id or step == 0:
            self.previous_rgb = rgb
            self.episode_id = episode_id
        if proprio.size != len(self.manifest["proprio_mean"]):
            return {"abstain": True, "reason": "proprioception_shape_ood"}
        low, high = np.asarray(self.manifest["proprio_low"]), np.asarray(self.manifest["proprio_high"])
        if np.any(proprio < low) or np.any(proprio > high):
            return {"abstain": True, "reason": "proprioception_distribution_ood"}
        state = spatial_state(rgb, self.previous_rgb, proprio, step,
                              proprio_mean=np.asarray(self.manifest["proprio_mean"]),
                              proprio_scale=np.asarray(self.manifest["proprio_scale"]))
        query = torch.as_tensor(state, device=self.device, dtype=torch.float32)
        # Squared Euclidean distance without materializing [N,D] differences.
        phase_mask = (self.steps - int(step)).abs() <= int(self.manifest["phase_window"])
        candidate_indices = torch.nonzero(phase_mask, as_tuple=False).reshape(-1)
        if not len(candidate_indices):
            return {"abstain": True, "reason": "episodic_phase_unrepresented"}
        candidate_states = self.states[candidate_indices]
        distances = (candidate_states.square().sum(1) - 2 * (candidate_states @ query)
                     + query.square().sum()).clamp_min_(0)
        count = min(int(self.manifest["neighbour_count"]), len(distances))
        values, local_indices = torch.topk(distances, count, largest=False)
        indices = candidate_indices[local_indices]
        nearest = float(torch.sqrt(values[0]).cpu())
        if not np.isfinite(nearest) or nearest > float(self.manifest["ood_radius"]):
            return {"abstain": True, "reason": "episodic_state_ood", "distance": nearest}
        weights = torch.softmax(-values / float(self.manifest["retrieval_temperature"]), dim=0)
        action = (self.actions[indices] * weights[:, None]).sum(0).cpu().numpy()
        action = np.clip(action, np.asarray(self.manifest["action_low"]),
                         np.asarray(self.manifest["action_high"])).astype(np.float32)
        self.previous_rgb = rgb
        return {"abstain": False, "values": action, "teacher_used": False,
                "policy_mode": "closed_loop_episodic_skill_memory", "distance": nearest,
                "capsule_digest": self.manifest["capsule_digest"]}


def load_runtime(manifest_path: Path, archive_path: Path,
                 *, device: str | torch.device = "cpu") -> EpisodicSkillRuntime:
    manifest = json.loads(manifest_path.read_text())
    unsigned = {key: value for key, value in manifest.items() if key != "capsule_digest"}
    if manifest.get("schema_version") != SCHEMA or manifest.get("capsule_digest") != digest(unsigned):
        raise ValueError("episodic_capsule_integrity_failure")
    if sha256(archive_path) != manifest.get("archive_sha256"):
        raise ValueError("episodic_archive_integrity_failure")
    with np.load(archive_path, allow_pickle=False) as raw:
        states = np.asarray(raw["states"], dtype=np.float32)
        actions = np.asarray(raw["actions"], dtype=np.float32)
        steps = np.asarray(raw["steps"], dtype=np.int64)
    if len(states) != len(actions) or len(states) != len(steps) or states.ndim != 2 or actions.ndim != 2:
        raise ValueError("episodic_archive_schema_failure")
    target = torch.device(device)
    return EpisodicSkillRuntime(manifest=manifest,
                                states=torch.as_tensor(states, device=target),
                                actions=torch.as_tensor(actions, device=target),
                                steps=torch.as_tensor(steps, device=target), device=target)
