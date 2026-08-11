import json

import numpy as np
import pytest

from backend.modules.hexcore.verified_embodied_skill_distillation import authority_from_archive, reconstruct, train


def sample(seed: int, count: int = 80):
    rng = np.random.default_rng(seed)
    rows = []
    for _ in range(count):
        rgb = rng.integers(20, 220, size=(64, 64, 3), dtype=np.uint8)
        proprio = rng.normal(0, .25, size=6).astype(np.float32)
        colour = rgb.mean(axis=(0, 1)) / 255.0
        action = np.asarray([colour[0] - colour[2], proprio[0] * .4 + colour[1] * .2], dtype=np.float32)
        rows.append({"rgb": rgb.tolist(), "proprioception": proprio.tolist(),
                     "teacher_action": action.tolist(), "outcome_verified": True})
    return {"audit": {"independent_physics_success": True, "student_privileged_fields_absent": True,
                       "commit_before_act_verified": True, "teacher_removed_evaluation_required": True},
            "transitions": rows}


def test_verified_distillation_reconstructs_without_teacher_and_beats_cold() -> None:
    receipt = sample(7)
    capsule = train([receipt], action_low=[-1, -1], action_high=[1, 1])
    policy = reconstruct(json.loads(json.dumps(capsule)))
    held = sample(13, 20)["transitions"]
    learned, cold = [], []
    for row in held:
        proposal = policy.propose(np.asarray(row["rgb"], dtype=np.uint8), np.asarray(row["proprioception"]))
        assert proposal["abstain"] is False and proposal["teacher_used"] is False
        target = np.asarray(row["teacher_action"])
        learned.append(float(np.mean((proposal["values"] - target) ** 2)))
        cold.append(float(np.mean(target ** 2)))
    assert np.mean(learned) < np.mean(cold) * .15
    assert capsule["parameter_count"] < 500


def test_unverified_or_privileged_teacher_rows_are_rejected() -> None:
    receipt = sample(3, 3)
    receipt["audit"]["student_privileged_fields_absent"] = False
    with pytest.raises(ValueError, match="trajectory_authority_incomplete"):
        train([receipt], action_low=[-1, -1], action_high=[1, 1])


def test_capsule_tamper_and_distribution_shift_fail_closed() -> None:
    capsule = train([sample(2)], action_low=[-1, -1], action_high=[1, 1])
    altered = json.loads(json.dumps(capsule)); altered["weights"][0][0] += 1
    with pytest.raises(ValueError, match="capsule_integrity_failure"):
        reconstruct(altered)
    policy = reconstruct(capsule)
    rgb = np.full((64, 64, 3), 255, dtype=np.uint8)
    result = policy.propose(rgb, np.full(6, 100, dtype=np.float32))
    assert result["abstain"] is True


def test_only_successful_hash_bound_teacher_archive_enters_training(tmp_path) -> None:
    archive = tmp_path / "teacher.npz"
    rgb = np.zeros((2, 64, 64, 3), dtype=np.uint8)
    proprio = np.zeros((2, 6), dtype=np.float32)
    action = np.asarray([[.1, .2], [.3, .4]], dtype=np.float32)
    np.savez_compressed(archive, rgb=rgb, proprioception=proprio, action=action,
                        reward=np.asarray([0, 1], dtype=np.float32),
                        episode=np.asarray([0, 1]), step=np.asarray([0, 0]))
    import hashlib
    receipt = {"arm_id": "gr00t_teacher",
               "audit": {"completed_without_failure": True, "student_privileged_fields_absent": True,
                         "commit_before_act_verified": True},
               "private_trajectory": {"sha256": hashlib.sha256(archive.read_bytes()).hexdigest()},
               "outcomes": [{"episode": 0, "success": False}, {"episode": 1, "success": True}]}
    authority = authority_from_archive(receipt, archive)
    assert len(authority["transitions"]) == 1
    assert np.allclose(authority["transitions"][0]["teacher_action"], [.3, .4])
    altered = bytearray(archive.read_bytes()); altered[-1] ^= 1; archive.write_bytes(altered)
    with pytest.raises(ValueError, match="trajectory_archive_integrity_failure"):
        authority_from_archive(receipt, archive)
