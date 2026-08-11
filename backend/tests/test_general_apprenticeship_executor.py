import json
from pathlib import Path

import pytest

from backend.modules.hexcore.general_apprenticeship_executor import (
    CorruptArtifactQuarantineInventor,
    ExerciseInventor,
    ResourceAndFailureDiscovery,
    _audit_patch,
    _transfer_and_cold_control,
    run,
)


REPO_ROOT = Path(__file__).resolve().parents[2]


def test_executor_discovers_resources_and_invents_progressive_exercises():
    discovery = ResourceAndFailureDiscovery().discover(REPO_ROOT)
    exercises = ExerciseInventor.invent(discovery)
    assert discovery["resources"]["language"] == "python"
    assert discovery["resources"]["source_model"]["direct_unprotected_parse"] is True
    assert len(exercises) == 6
    assert [row["difficulty"] for row in exercises] == list(range(1, 7))


def test_private_repair_is_source_derived_and_security_scanned():
    discovery = ResourceAndFailureDiscovery().discover(REPO_ROOT)
    proposal = CorruptArtifactQuarantineInventor.propose(discovery["source"])
    assert proposal["status"] == "proposed"
    assert proposal["audit"]["safe"] is True
    assert "quarantined" in proposal["candidate"]
    for malicious in (
        "eval(payload)", "subprocess.run(['sh'])", "requests.get(url)",
        "path.unlink()", "../outside",
    ):
        assert _audit_patch(malicious)["safe"] is False


def test_verified_method_transfers_to_sql_and_beats_cold_search():
    transfer = _transfer_and_cold_control(
        "validate_quarantine_preserve_then_return_absence"
    )
    assert transfer["passed"] is True
    assert transfer["cold_attempts"] == 3
    assert transfer["retained_attempts"] == 1
    assert transfer["attempt_reduction"] == pytest.approx(2 / 3)


def test_end_to_end_executor_passes_repository_transfer_and_retention(tmp_path):
    result = run(
        repo_root=REPO_ROOT,
        state_path=tmp_path / "executor/state.json",
        result_path=tmp_path / "result.json",
        apprentice_state_path=tmp_path / "apprentice/state.json",
    )
    assert result["passed"] is True
    assert result["gate"]["original_failure_reproduced"] is True
    assert result["gate"]["hidden_repository_outcome_passed"] is True
    assert result["gate"]["source_disjoint_sql_transfer"] is True
    assert result["gate"]["restart_retention"] is True
    assert result["gate"]["general_apprentice_receipt_verified"] is True
    assert result["gate"]["executor_contract_retained"] is True
    assert result["gate"]["live_repository_writes"] == 0
    retained = json.loads((tmp_path / "executor/state.json").read_text())
    assert retained["source_code_retained"] is False
    apprentice = json.loads((tmp_path / "apprentice/state.json").read_text())
    contract = apprentice["executor_contracts"][result["procedure_id"]]
    assert contract["proposal_only"] is True
