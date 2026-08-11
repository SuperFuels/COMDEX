"""Outcome-weighted relevance routing over protected embodied experience."""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

import numpy as np
import torch

from backend.modules.hexcore.episodic_embodied_skill_memory import spatial_state


SCHEMA = "aion.governed_embodied_experience_router.v1"
VISUAL_DIM = 6 * 24 * 32


def sha256(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            value.update(block)
    return value.hexdigest()


def digest(value: Mapping[str, Any]) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                                     default=str).encode()).hexdigest()


@dataclass
class GovernedExperienceRuntime:
    manifest: Mapping[str, Any]
    states: torch.Tensor
    actions: torch.Tensor
    steps: torch.Tensor
    protected: torch.Tensor
    device: torch.device
    previous_rgb: np.ndarray | None = None
    episode_id: int | None = None

    def _cost(self, states: torch.Tensor, query: torch.Tensor) -> torch.Tensor:
        visual = (states[:, :VISUAL_DIM] - query[:VISUAL_DIM]).square().mean(1)
        proprio = (states[:, VISUAL_DIM:-1] - query[VISUAL_DIM:-1]).square().mean(1)
        return (visual * float(self.manifest["visual_weight"])
                + proprio * float(self.manifest["proprio_weight"]))

    def propose(self, rgb: np.ndarray, proprioception: np.ndarray, *, episode_id: int,
                step: int) -> dict[str, Any]:
        image = np.asarray(rgb, dtype=np.uint8)[..., :3]
        proprio = np.asarray(proprioception, dtype=np.float32).reshape(-1)
        if self.episode_id != episode_id or step == 0:
            self.previous_rgb, self.episode_id = image, episode_id
        if proprio.size != len(self.manifest["proprio_mean"]):
            return {"abstain": True, "reason": "proprioception_shape_ood"}
        low, high = np.asarray(self.manifest["proprio_low"]), np.asarray(self.manifest["proprio_high"])
        if np.any(proprio < low) or np.any(proprio > high):
            return {"abstain": True, "reason": "proprioception_distribution_ood"}
        state = spatial_state(image, self.previous_rgb, proprio, step,
                              proprio_mean=np.asarray(self.manifest["proprio_mean"]),
                              proprio_scale=np.asarray(self.manifest["proprio_scale"]))
        query = torch.as_tensor(state, dtype=torch.float32, device=self.device)
        phase = (self.steps - int(step)).abs() <= int(self.manifest["phase_window"])
        protected_indices = torch.nonzero(phase & self.protected, as_tuple=False).reshape(-1)
        corrective_indices = torch.nonzero(phase & ~self.protected, as_tuple=False).reshape(-1)
        if not len(protected_indices):
            return {"abstain": True, "reason": "protected_phase_unrepresented"}
        protected_cost = self._cost(self.states[protected_indices], query)
        p_value, p_local = torch.min(protected_cost, dim=0)
        selected = protected_indices[p_local]
        mode = "protected_success_experience"
        correction_cost = None
        if len(corrective_indices):
            costs = self._cost(self.states[corrective_indices], query)
            c_value, c_local = torch.min(costs, dim=0)
            correction_cost = float(c_value.cpu())
            if c_value < p_value * float(self.manifest["correction_margin"]):
                candidate = corrective_indices[c_local]
                disagreement = torch.linalg.vector_norm(self.actions[candidate] - self.actions[selected])
                if disagreement <= float(self.manifest["maximum_action_disagreement"]):
                    selected = candidate
                    mode = "relevance_authorized_correction"
        distance = float(torch.sqrt(torch.minimum(p_value, torch.as_tensor(
            correction_cost if correction_cost is not None else float("inf"), device=self.device))).cpu())
        if not np.isfinite(distance) or distance > float(self.manifest["ood_radius"]):
            return {"abstain": True, "reason": "governed_experience_ood", "distance": distance}
        action = self.actions[selected].cpu().numpy()
        action = np.clip(action, np.asarray(self.manifest["action_low"]),
                         np.asarray(self.manifest["action_high"])).astype(np.float32)
        self.previous_rgb = image
        return {"abstain": False, "values": action, "teacher_used": False,
                "policy_mode": mode, "distance": distance,
                "capsule_digest": self.manifest["capsule_digest"]}


def load_runtime(manifest_path: Path, archive_path: Path,
                 *, device: str | torch.device = "cpu") -> GovernedExperienceRuntime:
    manifest = json.loads(manifest_path.read_text())
    unsigned = {key: value for key, value in manifest.items() if key != "capsule_digest"}
    if manifest.get("schema_version") != SCHEMA or manifest.get("capsule_digest") != digest(unsigned):
        raise ValueError("governed_router_integrity_failure")
    if sha256(archive_path) != manifest.get("archive_sha256"):
        raise ValueError("governed_router_archive_integrity_failure")
    with np.load(archive_path, allow_pickle=False) as raw:
        states, actions = np.asarray(raw["states"], dtype=np.float32), np.asarray(raw["actions"], dtype=np.float32)
        steps, protected = np.asarray(raw["steps"], dtype=np.int64), np.asarray(raw["protected"], dtype=bool)
    if not (len(states) == len(actions) == len(steps) == len(protected)) or not np.any(protected):
        raise ValueError("governed_router_archive_schema_failure")
    target = torch.device(device)
    return GovernedExperienceRuntime(manifest, torch.as_tensor(states, device=target),
                                     torch.as_tensor(actions, device=target),
                                     torch.as_tensor(steps, device=target),
                                     torch.as_tensor(protected, device=target), target)
