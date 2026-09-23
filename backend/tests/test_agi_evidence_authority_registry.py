from __future__ import annotations

import json
from pathlib import Path

from backend.modules.hexcore.agi_evidence_authority_registry import (
    PROCEDURE_ID,
    run_agi_evidence_registry,
)


REPO_ROOT = Path(__file__).resolve().parents[2]


def _run(tmp_path: Path) -> dict:
    return run_agi_evidence_registry(
        repo_root=REPO_ROOT,
        state_path=tmp_path / "state.json",
        result_path=tmp_path / "result.json",
        handoff_path=tmp_path / "handoff.json",
    )


def test_registry_commits_and_hashes_all_declared_evidence(tmp_path: Path) -> None:
    result = _run(tmp_path)
    assert result["passed"] is True
    assert result["promotion"]["candidate"]["procedure_id"] == PROCEDURE_ID
    assert result["control_gate"]["artifact_contracts"] == 21
    assert result["control_gate"]["artifact_integrity_rate"] == 1.0
    assert all(row["exists"] for row in result["artifacts"])
    assert all(row["integrity_passed"] for row in result["artifacts"])
    assert all(len(row["sha256"]) == 64 for row in result["artifacts"])


def test_public_outcomes_are_not_misrepresented_as_external_certification(
    tmp_path: Path,
) -> None:
    result = _run(tmp_path)
    bridge = result["external_outcome_bridge"]
    assert bridge["source_families"] == 4
    assert bridge["externally_maintained_source_families_passed"] == 4
    assert bridge["external_administrator_owned"] is False
    assert result["control_gate"]["externally_verified_gates"] == 0
    assert result["control_gate"]["agi_claim_authorized"] is False
    assert result["agi_claim_authorized"] is False


def test_all_ten_agi_gates_have_explicit_status_and_remaining_work(
    tmp_path: Path,
) -> None:
    result = _run(tmp_path)
    gates = {row["gate_id"]: row for row in result["evidence_gates"]}
    assert len(gates) == 10
    assert gates["continual_improvement_without_forgetting"]["status"] == "INTERNAL_BOUNDED_PASS"
    assert gates["tool_and_representation_invention"]["status"] == "INTERNAL_BOUNDED_PASS"
    assert gates["social_commonsense_creative_judgment"]["status"] == "BLOCKED_EXTERNAL_HUMAN_AUTHORITY"
    assert gates["independent_reproducibility"]["status"] == "BLOCKED_EXTERNAL_ADMINISTRATOR"
    assert all(row["satisfied_evidence"] for row in gates.values())
    assert all(row["remaining"] for row in gates.values())


def test_external_handoff_is_complete_but_fail_closed(tmp_path: Path) -> None:
    result = _run(tmp_path)
    handoff = result["external_handoff"]
    assert handoff["status"] == "AWAITING_EXTERNAL_ADMINISTRATOR"
    assert handoff["external_evaluator"] is None
    assert handoff["external_signature"] is None
    assert handoff["developer_self_certification_permitted"] is False
    assert len(handoff["required_portfolio_families"]) == 8
    assert len(handoff["required_matched_systems"]) == 8
    assert len(handoff["required_audit_fields"]) == 10


def test_registry_and_denial_survive_restart_without_relearning(tmp_path: Path) -> None:
    result = _run(tmp_path)
    assert result["restart"] == {
        "registry_retained": True,
        "control_plane_champion_retained": True,
        "agi_claim_still_denied": True,
        "relearning_artifacts": 0,
    }
    persisted = json.loads((tmp_path / "state.json").read_text(encoding="utf-8"))
    assert result["registry_id"] in persisted["agi_evidence_registries"]
    assert persisted["champions"]["agi_evidence_authority_control_plane"] == PROCEDURE_ID
