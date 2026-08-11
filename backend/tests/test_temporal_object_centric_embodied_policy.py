import json

import numpy as np
import pytest
import torch

from backend.modules.hexcore.temporal_object_centric_embodied_policy import (
    SCHEMA, TemporalObjectPolicy, canonical_digest, load_runtime,
)


def capsule(tmp_path):
    model = TemporalObjectPolicy(proprio_dim=18, action_dim=8, hidden_dim=32)
    weights = tmp_path / "policy.pt"
    torch.save(model.state_dict(), weights)
    import hashlib
    manifest = {
        "schema_version": SCHEMA, "weights_sha256": hashlib.sha256(weights.read_bytes()).hexdigest(),
        "proprio_dim": 18, "action_dim": 8, "hidden_dim": 32,
        "action_mean": [0] * 8, "action_scale": [1] * 8,
        "action_low": [-2] * 8, "action_high": [2] * 8,
        "proprio_low": [-2] * 18, "proprio_high": [2] * 18,
    }
    manifest["capsule_digest"] = canonical_digest(manifest)
    path = tmp_path / "manifest.json"; path.write_text(json.dumps(manifest))
    return path, weights


def test_temporal_policy_reconstructs_and_resets_belief(tmp_path) -> None:
    manifest, weights = capsule(tmp_path)
    runtime = load_runtime(manifest, weights)
    rgb = np.full((96, 128, 3), 80, dtype=np.uint8)
    first = runtime.propose(rgb, np.zeros(18), episode_id=1, step=0)
    assert first["abstain"] is False and first["teacher_used"] is False
    old_hidden = runtime.hidden.clone()
    runtime.propose(rgb + 1, np.zeros(18), episode_id=1, step=1)
    assert not torch.equal(old_hidden, runtime.hidden)
    runtime.propose(rgb, np.zeros(18), episode_id=2, step=0)
    assert runtime.episode_id == 2


def test_manifest_weights_and_ood_fail_closed(tmp_path) -> None:
    manifest, weights = capsule(tmp_path)
    data = json.loads(manifest.read_text()); data["action_high"][0] = 9
    manifest.write_text(json.dumps(data))
    with pytest.raises(ValueError, match="integrity"):
        load_runtime(manifest, weights)
    manifest, weights = capsule(tmp_path)
    runtime = load_runtime(manifest, weights)
    result = runtime.propose(np.zeros((96, 128, 3), dtype=np.uint8), np.full(18, 30),
                             episode_id=0, step=0)
    assert result == {"abstain": True, "reason": "proprioception_distribution_ood"}


def test_model_sequence_shape_and_visual_moments() -> None:
    model = TemporalObjectPolicy(proprio_dim=18, action_dim=8, hidden_dim=32)
    rgb = torch.randint(0, 255, (2, 4, 96, 128, 3), dtype=torch.uint8)
    output = model.forward_sequence(rgb, torch.zeros(2, 4, 18), torch.ones(2, 4, dtype=torch.bool))
    assert output.shape == (2, 4, 8)
    assert torch.isfinite(output).all()
