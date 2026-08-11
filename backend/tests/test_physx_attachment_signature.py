import json
from pathlib import Path

import numpy as np
import pytest

from integrations.isaac_lab.learn_physx_attachment_signature import AttachmentSignature, build


ROOT = Path(__file__).resolve().parents[2]


def test_learned_signature_passes_later_consequence_gate(tmp_path: Path) -> None:
    capsule = build(
        ROOT / "results/immutable/isaac_precision_franka/contact_transition_collection.npz",
        ROOT / "results/immutable/isaac_precision_franka/contact_transition_collection_receipt.json",
        tmp_path / "capsule.json",
    )
    assert capsule["gate"]["development"]["recall"] == 1.0
    assert capsule["gate"]["sealed"]["recall"] == 1.0
    assert capsule["gate"]["sealed"]["precision"] >= .80


def test_signature_accepts_real_grasp_shape_and_rejects_collision(tmp_path: Path) -> None:
    path = tmp_path / "capsule.json"
    build(ROOT / "results/immutable/isaac_precision_franka/contact_transition_collection.npz",
          ROOT / "results/immutable/isaac_precision_franka/contact_transition_collection_receipt.json", path)
    signature = AttachmentSignature.load(path)
    for _ in range(4):
        accepted = signature.update(np.asarray([44., 42.]), .0228)
    assert accepted
    signature.reset()
    for _ in range(4):
        accepted = signature.update(np.asarray([250., 0.]), .0003)
    assert not accepted
    with pytest.raises(ValueError):
        signature.update(np.asarray([np.nan, 0.]), .02)
