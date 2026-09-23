from pathlib import Path

import numpy as np

from integrations.isaac_lab.contact_transition_gate import assess_archive


def test_old_frame_archive_fails_closed():
    path = Path("results/immutable/isaac_precision_franka/tactile_opposition_v8_frames.npz")
    result = assess_archive(path)
    assert result["passed"] is False
    assert result["status"] == "blocked_missing_real_fields"
    assert "fingertip_touch" in result["missing"]


def test_real_fields_without_enough_lifts_do_not_authorize(tmp_path):
    n = 240
    path = tmp_path / "contact.npz"
    np.savez_compressed(
        path,
        proprioception=np.zeros((n, 18), np.float32),
        action=np.zeros((n, 8), np.float32),
        fingertip_touch=np.ones((n, 2), np.float32),
        object_height_post=np.full(n, .055, np.float32),
        episode=np.repeat(np.arange(4), 60),
        step=np.tile(np.arange(60), 4),
        arm=np.full(n, "aion_retained"),
    )
    result = assess_archive(path)
    assert result["passed"] is False
    assert result["status"] == "blocked_insufficient_independent_outcomes"
    assert result["positive"] == 0
