from __future__ import annotations

import json
from pathlib import Path


RESULT = Path(__file__).resolve().parents[2] / "results/hexcore_fifth_repository_rust_repair.json"


def _result() -> dict:
    return json.loads(RESULT.read_text(encoding="utf-8"))


def test_fifth_repository_and_self_falsification_pass() -> None:
    result = _result()
    gate = result["gate"]
    assert result["passed"] is True
    assert gate["independent_git_authority"] is True
    assert gate["human_patch_blind"] is True
    assert gate["self_invented_property_rejects_original"] is True
    assert gate["self_invented_property_accepts_candidate"] is True


def test_hidden_native_security_and_restart_gates_pass() -> None:
    result = _result()
    gate = result["gate"]
    assert gate["hidden_three_seed_success"] is True
    assert gate["full_native_suite_passed"] is True
    assert gate["malicious_variants_rejected"] == gate["malicious_variants_total"] == 6
    assert gate["malicious_variants_executed"] == 0
    assert gate["live_repository_writes"] == 0
    assert result["restart"]["contract_retained"] is True
    assert result["restart"]["champion_retained"] is True
