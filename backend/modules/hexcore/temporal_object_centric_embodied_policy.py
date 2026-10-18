"""Teacher-removable temporal visual policy for contact-rich manipulation.

The component receives pixels and bounded robot proprioception only.  Spatial
convolutions, generic soft visual keypoints and a recurrent belief state retain
geometry and motion that colour-grid summaries discard.  Torch is replaceable:
weights are hash-bound and the teacher is never loaded by the runtime adapter.
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


SCHEMA = "aion.temporal_object_centric_skill_capsule.v1"


def file_sha256(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            value.update(block)
    return value.hexdigest()


def canonical_digest(value: Mapping[str, Any]) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                                     default=str).encode()).hexdigest()


class TemporalObjectPolicy(nn.Module):
    """Recurrent RGB/proprio policy with label-free spatial keypoints."""

    def __init__(self, *, proprio_dim: int = 18, action_dim: int = 8,
                 hidden_dim: int = 256) -> None:
        super().__init__()
        self.proprio_dim = int(proprio_dim)
        self.action_dim = int(action_dim)
        self.hidden_dim = int(hidden_dim)
        self.visual = nn.Sequential(
            nn.Conv2d(6, 32, kernel_size=5, stride=2, padding=2), nn.SiLU(),
            nn.Conv2d(32, 64, kernel_size=3, stride=2, padding=1), nn.SiLU(),
            nn.Conv2d(64, 128, kernel_size=3, stride=2, padding=1), nn.SiLU(),
            nn.Conv2d(128, 128, kernel_size=3, stride=2, padding=1), nn.SiLU(),
            nn.AdaptiveAvgPool2d((4, 4)), nn.Flatten(),
            nn.Linear(128 * 4 * 4, 256), nn.SiLU(),
        )
        self.sensed = nn.Sequential(nn.Linear(self.proprio_dim + 18, 96), nn.SiLU(),
                                    nn.Linear(96, 96), nn.SiLU())
        self.recurrent = nn.GRUCell(352, self.hidden_dim)
        self.action_head = nn.Sequential(nn.Linear(self.hidden_dim, 192), nn.SiLU(),
                                         nn.Linear(192, self.action_dim))

    @staticmethod
    def _moments(image: torch.Tensor) -> torch.Tensor:
        """Return label-free channel and chromatic soft centroids/masses."""
        batch, _, height, width = image.shape
        yy, xx = torch.meshgrid(
            torch.linspace(0, 1, height, device=image.device, dtype=image.dtype),
            torch.linspace(0, 1, width, device=image.device, dtype=image.dtype), indexing="ij",
        )
        xx, yy = xx.reshape(1, 1, height, width), yy.reshape(1, 1, height, width)
        sets = (image.clamp_min(0), (image - image.mean(dim=1, keepdim=True)).clamp_min(0))
        output = []
        for weights in sets:
            mass = weights.sum(dim=(2, 3)).clamp_min(1e-6)
            output.extend(((weights * xx).sum(dim=(2, 3)) / mass,
                           (weights * yy).sum(dim=(2, 3)) / mass,
                           mass / float(height * width)))
        return torch.cat(output, dim=1).reshape(batch, 18)

    @staticmethod
    def prepare_rgb(rgb: torch.Tensor) -> torch.Tensor:
        if rgb.ndim != 4:
            raise ValueError("rgb_batch_shape_invalid")
        if rgb.shape[-1] in {3, 4}:
            rgb = rgb[..., :3].permute(0, 3, 1, 2)
        elif rgb.shape[1] != 3:
            raise ValueError("rgb_channels_invalid")
        rgb = rgb.float() / 255.0 if rgb.dtype == torch.uint8 else rgb.float()
        return F.interpolate(rgb, size=(64, 64), mode="bilinear", align_corners=False)

    def encode(self, current: torch.Tensor, previous: torch.Tensor,
               proprioception: torch.Tensor) -> torch.Tensor:
        current = self.prepare_rgb(current)
        previous = self.prepare_rgb(previous)
        visual = self.visual(torch.cat((current, previous), dim=1))
        sensed = self.sensed(torch.cat((proprioception.float(), self._moments(current)), dim=1))
        return torch.cat((visual, sensed), dim=1)

    def forward(self, current: torch.Tensor, previous: torch.Tensor,
                proprioception: torch.Tensor, hidden: torch.Tensor | None = None
                ) -> tuple[torch.Tensor, torch.Tensor]:
        encoded = self.encode(current, previous, proprioception)
        if hidden is None:
            hidden = torch.zeros((len(encoded), self.hidden_dim), dtype=encoded.dtype,
                                 device=encoded.device)
        hidden = self.recurrent(encoded, hidden)
        return self.action_head(hidden), hidden

    def forward_sequence(self, rgb: torch.Tensor, proprioception: torch.Tensor,
                         valid: torch.Tensor) -> torch.Tensor:
        """Run padded [B,T,H,W,C] episodes without leaking state across resets."""
        batch, steps = rgb.shape[:2]
        previous = torch.cat((rgb[:, :1], rgb[:, :-1]), dim=1)
        encoded = self.encode(rgb.reshape((-1,) + tuple(rgb.shape[2:])),
                              previous.reshape((-1,) + tuple(previous.shape[2:])),
                              proprioception.reshape(-1, proprioception.shape[-1]))
        encoded = encoded.reshape(batch, steps, -1)
        hidden = torch.zeros((batch, self.hidden_dim), dtype=encoded.dtype, device=encoded.device)
        outputs = []
        for step in range(steps):
            proposal = self.recurrent(encoded[:, step], hidden)
            mask = valid[:, step:step + 1].to(proposal.dtype)
            hidden = proposal * mask + hidden * (1 - mask)
            outputs.append(self.action_head(hidden))
        return torch.stack(outputs, dim=1)


@dataclass
class TemporalPolicyRuntime:
    model: TemporalObjectPolicy
    manifest: Mapping[str, Any]
    device: torch.device
    hidden: torch.Tensor | None = None
    previous_rgb: np.ndarray | None = None
    episode_id: int | None = None

    def propose(self, rgb: np.ndarray, proprioception: np.ndarray, *, episode_id: int,
                step: int) -> dict[str, Any]:
        image = np.asarray(rgb, dtype=np.uint8)[..., :3]
        proprio = np.asarray(proprioception, dtype=np.float32).reshape(-1)
        if (proprio.size != int(self.manifest["proprio_dim"]) or not np.all(np.isfinite(proprio))
                or image.ndim != 3 or image.shape[-1] != 3):
            return {"abstain": True, "reason": "student_observation_contract_failure"}
        if self.episode_id != episode_id or step == 0:
            self.hidden = None
            self.previous_rgb = image
            self.episode_id = episode_id
        low = np.asarray(self.manifest["proprio_low"], dtype=np.float32)
        high = np.asarray(self.manifest["proprio_high"], dtype=np.float32)
        if np.any(proprio < low) or np.any(proprio > high):
            return {"abstain": True, "reason": "proprioception_distribution_ood"}
        current = torch.as_tensor(image[None], device=self.device)
        previous = torch.as_tensor(self.previous_rgb[None], device=self.device)
        sensed = torch.as_tensor(proprio[None], device=self.device)
        with torch.inference_mode():
            normalized, self.hidden = self.model(current, previous, sensed, self.hidden)
        action = normalized[0].cpu().numpy()
        action = action * np.asarray(self.manifest["action_scale"], dtype=np.float32)
        action = action + np.asarray(self.manifest["action_mean"], dtype=np.float32)
        action = np.clip(action, np.asarray(self.manifest["action_low"]),
                         np.asarray(self.manifest["action_high"])).astype(np.float32)
        self.previous_rgb = image
        return {"abstain": False, "values": action, "teacher_used": False,
                "policy_mode": "temporal_object_centric_recurrent",
                "capsule_digest": self.manifest["capsule_digest"]}


def load_runtime(manifest_path: Path, weights_path: Path,
                 *, device: str | torch.device = "cpu") -> TemporalPolicyRuntime:
    manifest = json.loads(manifest_path.read_text())
    unsigned = {key: value for key, value in manifest.items() if key != "capsule_digest"}
    if manifest.get("schema_version") != SCHEMA or manifest.get("capsule_digest") != canonical_digest(unsigned):
        raise ValueError("temporal_capsule_integrity_failure")
    if file_sha256(weights_path) != manifest.get("weights_sha256"):
        raise ValueError("temporal_weights_integrity_failure")
    target = torch.device(device)
    model = TemporalObjectPolicy(proprio_dim=int(manifest["proprio_dim"]),
                                 action_dim=int(manifest["action_dim"]),
                                 hidden_dim=int(manifest["hidden_dim"]))
    state = torch.load(weights_path, map_location=target, weights_only=True)
    model.load_state_dict(state, strict=True)
    model.to(target).eval()
    return TemporalPolicyRuntime(model=model, manifest=manifest, device=target)
