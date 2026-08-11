from __future__ import annotations

import numpy as np
import pytest

from backend.modules.hexcore.hand_embodiment_apprenticeship import (
    DEVELOPMENT,
    HandEmbodimentLearner,
    TactileHandAuthority,
)
from integrations.isaac_lab.aion_tactile_hand_contract import bounded_fingertip_touch


def test_hand_self_model_discovers_all_digits_and_touches_visual_target() -> None:
    authority = TactileHandAuthority(DEVELOPMENT, target_digit=2)
    try:
        result, schema = HandEmbodimentLearner().execute(authority)
    finally:
        authority.close()
    assert result["success"] is True
    assert result["correct_digit_selected"] is True
    assert schema["self_model_complete"] is True
    assert {row["physical_digit"] for row in schema["models"]} == set(range(5))
    assert result["teacher_actions_used"] == 0


def test_hand_authority_rejects_malformed_actions() -> None:
    for action in (np.asarray([0.0]), np.asarray([0, 0, 0, 0, 2.0]),
                   np.asarray([0, 0, np.nan, 0, 0])):
        with pytest.raises(ValueError):
            TactileHandAuthority.validate(action)


def test_isaac_tactile_contract_is_ordered_bounded_and_fail_closed() -> None:
    result = bounded_fingertip_touch(
        {"thumb": [3.0, 4.0, 0.0], "index": [0.0, 0.0, 2.0]},
        ["thumb", "index"],
    )
    assert result["fingertip_touch"].tolist() == [5.0, 2.0]
    assert result["privileged_contact_geometry"] is False
    with pytest.raises(RuntimeError):
        bounded_fingertip_touch({"thumb": [1, 0, 0], "palm": [0, 0, 0]}, ["thumb"])
    with pytest.raises(RuntimeError):
        bounded_fingertip_touch({"thumb": [1000, 0, 0]}, ["thumb"])
