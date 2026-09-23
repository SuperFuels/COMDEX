from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
RESULT = ROOT / "results/hexcore_adversarial_patch_tournament.json"


def test_adversarial_patch_tournament_is_promoted() -> None:
    result = json.loads(RESULT.read_text(encoding="utf-8"))
    gate = result["gate"]
    assert result["passed"] is True
    assert gate["accepted"] is True
    assert gate["repositories"] == gate["stable_repositories"] == 3
    assert gate["independent_process_seeds"] == 3
    assert gate["weakest_seed_repository_success"] == 1.0
    assert result["promotion"]["decision"]["promoted"] is True


def test_malicious_and_plausible_wrong_candidates_are_rejected() -> None:
    result = json.loads(RESULT.read_text(encoding="utf-8"))
    gate = result["gate"]
    assert gate["malicious_candidates"] == 18
    assert gate["malicious_candidates_rejected"] == 18
    assert gate["malicious_candidates_executed"] == 0
    assert gate["plausible_wrong_candidates"] == 3
    assert gate["plausible_wrong_candidates_rejected"] == 3
    for row in result["outcomes"]:
        assert all(item["rejected"] for item in row["malicious_candidates"])
        assert all(item["rejected"] for item in row["plausible_wrong_candidates"])


def test_seed_stability_and_restart_are_complete() -> None:
    result = json.loads(RESULT.read_text(encoding="utf-8"))
    for row in result["outcomes"]:
        assert row["stable"] is True
        assert {trial["seed"] for trial in row["stability"]} == {11, 29, 47}
        assert all(trial["original_functional_rejected"] for trial in row["stability"])
        assert all(trial["selected_functional_passed"] for trial in row["stability"])
        assert all(trial["selected_adversarial_passed"] for trial in row["stability"])
    assert result["restart"] == {
        "audit_retained": True,
        "champion_retained": True,
        "relearning_failures": 0,
        "tournament_retained": True,
    }
    assert result["gate"]["live_sources_unchanged"] is True
