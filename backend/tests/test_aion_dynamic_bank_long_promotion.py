import json

import pytest

from backend.scripts.promote_aion_dynamic_bank_long_generation import (
    _canonical_sha256,
    _load_verified,
    _repeatability,
)


def test_repeatability_compares_the_two_matching_conditions() -> None:
    report = {"prompt_families": ["a"], "runs": [
        {"family": "a", "condition": "dynamic_bank", "sequence": 1,
         "token_ids": [1, 2]},
        {"family": "a", "condition": "dynamic_bank", "sequence": 2,
         "token_ids": [1, 2]},
    ]}
    assert _repeatability(report, "dynamic_bank")["fraction"] == 1.0


def test_load_verified_rejects_changed_evidence(tmp_path) -> None:
    value = {"measurement": 1}
    value["report_sha256"] = _canonical_sha256(value)
    path = tmp_path / "evidence.json"
    path.write_text(json.dumps(value))
    assert _load_verified(path)["measurement"] == 1
    value["measurement"] = 2
    path.write_text(json.dumps(value))
    with pytest.raises(ValueError, match="canonical report hash failed"):
        _load_verified(path)
