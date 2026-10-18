"""Asymmetric visual apprenticeship with privileged labels quarantined to training.

The deployed runtime accepts RGB, bounded proprioception and its own prior action.
Simulator geometry exists only as an auxiliary target during private training and
is neither serialized into the runtime state nor accepted by :meth:`propose`.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

import numpy as np
import torch
from torch import nn
from torch.nn import functional as F

SCHEMA = "aion.privileged_visual_distillation.v1"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def digest(value: Mapping[str, Any]) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                                     default=str).encode()).hexdigest()


class PrivilegedVisualPolicy(nn.Module):
    """Infer a visual geometry belief, then act through a recurrent controller."""

    def __init__(self, proprio_dim: int = 18, action_dim: int = 8,
                 label_dim: int = 10, hidden_dim: int = 256) -> None:
        super().__init__()
        self.proprio_dim, self.action_dim = int(proprio_dim), int(action_dim)
        self.label_dim, self.hidden_dim = int(label_dim), int(hidden_dim)
        self.vision = nn.Sequential(
            nn.Conv2d(6, 32, 5, 2, 2), nn.SiLU(),
            nn.Conv2d(32, 64, 3, 2, 1), nn.SiLU(),
            nn.Conv2d(64, 128, 3, 2, 1), nn.SiLU(),
            nn.Conv2d(128, 128, 3, 2, 1), nn.SiLU(),
            nn.AdaptiveAvgPool2d((4, 4)), nn.Flatten(),
            nn.Linear(2048, 320), nn.SiLU(),
        )
        self.belief_head = nn.Sequential(nn.Linear(320, 192), nn.SiLU(),
                                         nn.Linear(192, self.label_dim))
        self.recurrent = nn.GRUCell(320 + self.label_dim + self.proprio_dim + self.action_dim,
                                    self.hidden_dim)
        self.action_head = nn.Sequential(nn.Linear(self.hidden_dim, 192), nn.SiLU(),
                                         nn.Linear(192, self.action_dim))

    @staticmethod
    def prepare(rgb: torch.Tensor) -> torch.Tensor:
        if rgb.ndim != 4:
            raise ValueError("rgb_batch_shape_invalid")
        if rgb.shape[-1] in (3, 4):
            rgb = rgb[..., :3].permute(0, 3, 1, 2)
        elif rgb.shape[1] != 3:
            raise ValueError("rgb_channels_invalid")
        rgb = rgb.float() / 255.0 if rgb.dtype == torch.uint8 else rgb.float()
        return F.interpolate(rgb, (64, 64), mode="bilinear", align_corners=False)

    def encode(self, current: torch.Tensor, previous: torch.Tensor):
        visual = self.vision(torch.cat((self.prepare(current), self.prepare(previous)), 1))
        return visual, self.belief_head(visual)

    def step(self, current: torch.Tensor, previous: torch.Tensor, proprio: torch.Tensor,
             prior_action: torch.Tensor, hidden: torch.Tensor | None = None):
        visual, belief = self.encode(current, previous)
        combined = torch.cat((visual, belief, proprio.float(), prior_action.float()), 1)
        if hidden is None:
            hidden = torch.zeros((len(combined), self.hidden_dim), device=combined.device,
                                 dtype=combined.dtype)
        hidden = self.recurrent(combined, hidden)
        return self.action_head(hidden), belief, hidden

    def sequence(self, rgb: torch.Tensor, proprio: torch.Tensor, prior_action: torch.Tensor,
                 valid: torch.Tensor):
        batch, steps = rgb.shape[:2]
        previous = torch.cat((rgb[:, :1], rgb[:, :-1]), 1)
        visual, belief = self.encode(rgb.reshape((-1,) + tuple(rgb.shape[2:])),
                                     previous.reshape((-1,) + tuple(rgb.shape[2:])))
        visual, belief = visual.reshape(batch, steps, -1), belief.reshape(batch, steps, -1)
        hidden = torch.zeros((batch, self.hidden_dim), device=visual.device)
        actions = []
        for index in range(steps):
            candidate = self.recurrent(torch.cat((visual[:, index], belief[:, index],
                proprio[:, index].float(), prior_action[:, index].float()), 1), hidden)
            mask = valid[:, index:index + 1].to(candidate.dtype)
            hidden = candidate * mask + hidden * (1 - mask)
            actions.append(self.action_head(hidden))
        return torch.stack(actions, 1), belief


@dataclass
class Runtime:
    model: PrivilegedVisualPolicy
    manifest: Mapping[str, Any]
    device: torch.device
    hidden: torch.Tensor | None = None
    previous_rgb: np.ndarray | None = None
    previous_action: np.ndarray | None = None
    episode_id: int | None = None

    def propose(self, rgb: np.ndarray, proprioception: np.ndarray, *, episode_id: int,
                step: int) -> dict[str, Any]:
        image = np.asarray(rgb, dtype=np.uint8)[..., :3]
        proprio = np.asarray(proprioception, dtype=np.float32).reshape(-1)
        if image.ndim != 3 or image.shape[-1] != 3 or proprio.size != self.model.proprio_dim:
            return {"abstain": True, "reason": "runtime_observation_contract_failure"}
        if not np.all(np.isfinite(proprio)):
            return {"abstain": True, "reason": "nonfinite_proprioception"}
        if self.episode_id != episode_id or step == 0:
            self.hidden, self.previous_rgb, self.previous_action = None, image, np.zeros(self.model.action_dim, np.float32)
            self.episode_id = episode_id
        low, high = np.asarray(self.manifest["proprio_low"]), np.asarray(self.manifest["proprio_high"])
        if np.any(proprio < low) or np.any(proprio > high):
            return {"abstain": True, "reason": "proprioception_distribution_ood"}
        with torch.inference_mode():
            prior = ((self.previous_action - np.asarray(self.manifest["action_mean"], dtype=np.float32))
                     / np.asarray(self.manifest["action_scale"], dtype=np.float32))
            action, belief, self.hidden = self.model.step(
                torch.as_tensor(image[None], device=self.device),
                torch.as_tensor(self.previous_rgb[None], device=self.device),
                torch.as_tensor(proprio[None], device=self.device),
                torch.as_tensor(prior[None], device=self.device), self.hidden)
        values = action[0].cpu().numpy() * np.asarray(self.manifest["action_scale"]) + np.asarray(self.manifest["action_mean"])
        values = np.clip(values, self.manifest["action_low"], self.manifest["action_high"]).astype(np.float32)
        self.previous_rgb, self.previous_action = image, values
        return {"abstain": False, "values": values, "teacher_used": False,
                "policy_mode": "pixel_inferred_geometry_belief", "belief": belief[0].cpu().numpy().tolist(),
                "capsule_digest": self.manifest["capsule_digest"]}


def load_runtime(manifest_path: Path, weights_path: Path, *, device: str = "cpu") -> Runtime:
    manifest = json.loads(manifest_path.read_text())
    unsigned = {k: v for k, v in manifest.items() if k != "capsule_digest"}
    if manifest.get("schema_version") != SCHEMA or manifest.get("capsule_digest") != digest(unsigned):
        raise ValueError("privileged_distillation_capsule_integrity_failure")
    if sha256(weights_path) != manifest.get("weights_sha256"):
        raise ValueError("privileged_distillation_weights_integrity_failure")
    if manifest.get("runtime_privileged_inputs") != []:
        raise ValueError("privileged_runtime_channel_forbidden")
    target = torch.device(device)
    model = PrivilegedVisualPolicy(int(manifest["proprio_dim"]), int(manifest["action_dim"]),
                                   int(manifest["label_dim"]), int(manifest["hidden_dim"]))
    model.load_state_dict(torch.load(weights_path, map_location=target, weights_only=True), strict=True)
    return Runtime(model.to(target).eval(), manifest, target)
