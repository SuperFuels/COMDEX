import json

import pytest

from backend.api.boardroom_provider_router import _validate_board_response


def test_boardroom_accepts_only_complete_flat_structured_minutes():
    payload = {
        "position": "Focus on validating the first customer journey.",
        "recommendations": ["Validate lead to payment."],
        "risks": ["Management accounts are not yet verified."],
        "missing_inputs": ["Real job outcomes."],
        "plan_changes": ["Marketing: request original project evidence."],
        "confidence": 0.78,
    }
    assert _validate_board_response(json.dumps(payload)) == payload


@pytest.mark.parametrize(
    "content",
    [
        '{"position":"truncated",',
        json.dumps({
            "position": "Nested recommendations are not the agreed contract.",
            "recommendations": {"CMO": ["Do something"]},
            "risks": [],
            "missing_inputs": [],
            "plan_changes": [],
            "confidence": 0.5,
        }),
        json.dumps({
            "position": "Confidence missing.",
            "recommendations": [],
            "risks": [],
            "missing_inputs": [],
            "plan_changes": [],
        }),
    ],
)
def test_boardroom_rejects_truncated_or_wrong_shape_minutes(content):
    with pytest.raises(RuntimeError, match="invalid_structured_response"):
        _validate_board_response(content)
