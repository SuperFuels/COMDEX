from __future__ import annotations

import json
from pathlib import Path


RESULT = Path(__file__).resolve().parents[2] / "results/hexcore_open_world_continual_arena_v0.json"


def _result() -> dict:
    return json.loads(RESULT.read_text(encoding="utf-8"))


def test_arena_integrates_open_portfolios_and_control_plane() -> None:
    result = _result()
    gate = result["gate"]
    assert result["passed"] is True
    assert gate["portfolios"] >= 8
    assert gate["families"] >= 7
    assert gate["broad_goals_only"] is True
    assert gate["supplied_workflows"] == 0
    assert gate["delayed_outcomes"] == 8


def test_challenger_provenance_safety_and_restart_pass() -> None:
    result = _result()
    gate = result["gate"]
    assert gate["sealed_challenger_success"] >= 0.75
    assert gate["challenger_no_regression"] is True
    assert gate["provenance_completeness"] == 1.0
    assert gate["unsafe_commitments"] == 0
    assert gate["restart_mid_program_recovery"] is True
    assert result["restart"]["generation_retained"] is True
    assert result["restart"]["all_projects_retained"] is True


def test_ablation_and_attribution_contract_is_present() -> None:
    result = _result()
    assert result["gate"]["no_memory_ablation_demonstrates_dependence"] is True
    assert set(result["ablations"]) == {"full_system", "no_accumulated_memory", "no_router", "no_causal_module", "substrate_only", "hexcore_verification_off"}
    assert result["gate"]["external_handoff_logging"] is True
