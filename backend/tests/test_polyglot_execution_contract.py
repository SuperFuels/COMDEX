from __future__ import annotations

import json
from pathlib import Path


RESULT = Path(__file__).resolve().parents[2] / "results/hexcore_polyglot_execution_contract.json"


def test_polyglot_contract_is_promoted_without_claiming_five_repositories() -> None:
    result = json.loads(RESULT.read_text(encoding="utf-8"))
    gate = result["gate"]
    assert result["passed"] is True
    assert gate["accepted"] is True
    assert gate["execution_targets"] == 5
    assert gate["language_names"] == ["javascript", "python", "typescript"]
    assert gate["languages"] == 3
    assert gate["project_families"] == 5
    assert gate["independent_repository_families"] == 4
    assert gate["five_independent_repositories_met"] is False


def test_polyglot_stability_and_counterexamples_pass() -> None:
    result = json.loads(RESULT.read_text(encoding="utf-8"))
    gate = result["gate"]
    assert gate["all_targets_passed"] is True
    assert gate["weakest_target_success"] == 1.0
    assert gate["three_seed_javascript_stability"] is True
    assert gate["three_seed_typescript_stability"] is True
    assert gate["counterexamples"] == gate["counterexamples_rejected"] == 4
    assert result["restart"]["contracts_retained"] is True
    assert result["restart"]["champion_retained"] is True
