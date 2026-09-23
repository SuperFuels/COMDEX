from __future__ import annotations

import json
from pathlib import Path


RESULT = (
    Path(__file__).resolve().parents[2]
    / "results/hexcore_open_world_outcome_execution_arena_v1.json"
)


def _result() -> dict:
    return json.loads(RESULT.read_text(encoding="utf-8"))


def test_v1_executes_selected_actions_and_aligns_answers() -> None:
    result = _result()
    gate = result["gate"]
    assert result["passed"] is True
    assert gate["portfolios"] == 8
    assert gate["families"] >= 7
    assert gate["required_tool_execution_rate"] == 1.0
    assert gate["consequence_alignment"] == 1.0
    assert gate["outcome_executed_success"] >= 0.875


def test_v1_has_real_math_code_table_image_and_change_outcomes() -> None:
    result = _result()
    executions = result["executions"]
    atom = {row["tool"]: row["outcome"] for row in executions["atoms_isotopes_project"]}
    python = {row["tool"]: row["outcome"] for row in executions["python_behavior_project"]}
    fourier = {row["tool"]: row["outcome"] for row in executions["fourier_evidence_project"]}
    software = {row["tool"]: row["outcome"] for row in executions["software_governance_project"]}
    assert atom["math_tool"]["remaining_percent"] == 25.0
    assert python["code_reasoner"]["verified"] is True
    assert fourier["table_analyzer"]["verified"] is True
    assert fourier["image_inspector"]["semantic_axis_alignment_verified"] is False
    assert software["sandbox_change_probe"]["change_detected"] is True
    assert software["sandbox_change_probe"]["live_source_unchanged"] is True


def test_v1_preserves_provenance_authority_and_restart() -> None:
    result = _result()
    assert result["gate"]["provenance_completeness"] == 1.0
    assert result["gate"]["unsafe_commitments"] == 0
    assert result["gate"]["evidence_ledger_immutable"] is True
    assert result["gate"]["revision_claims_given_source_authority"] == 0
    assert result["gate"]["rejected_revision_claims"] > 0
    assert result["gate"]["unconstrained_revision_rejected"] is True
    assert result["unconstrained_revision_audit"]["accepted"] is False
    assert result["unconstrained_revision_audit"]["unsafe_commitments"] > 0
    assert result["gate"]["restart_between_action_and_revision"] is True
    assert result["restart"]["generation_retained"] is True
    assert result["restart"]["all_projects_terminal"] is True
    assert result["restart"]["champion_retained"] is True
