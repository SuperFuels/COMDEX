import hashlib
import json
from pathlib import Path

from backend.modules.hexcore.long_duration_campaign_cau_review import review
from backend.modules.hexcore.long_duration_real_outcome_campaign import PROCEDURE_ID


def _hash(body):
    return hashlib.sha256(json.dumps(body, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def test_review_rereads_and_promotes_only_exact_wall_clock_campaign(tmp_path: Path) -> None:
    results = tmp_path / "results"
    results.mkdir()
    ledger_rows = []
    cycles = []
    for index in range(1, 13):
        body = {"cycle": index, "pre_action_commitment": f"commit-{index}",
                "execution": {"passed": True}, "transaction": {"passed": True}}
        outcome_hash = _hash(body)
        row = {**body, "outcome_sha256": outcome_hash}
        ledger_rows.append(row)
        cycles.append({"cycle": index, "commitment": f"commit-{index}",
                       "outcome_sha256": outcome_hash, "execution_passed": True,
                       "transaction_passed": True})
    state = {"procedure_id": PROCEDURE_ID, "cycles": cycles, "status": "INTERNALLY_ELIGIBLE_FOR_CAU_REVIEW",
             "gate": {"accepted": True, "actual_elapsed_hours": 24.1, "minimum_elapsed_hours": 24,
                      "minimum_cycles": 12, "independent_remote_authorities": 4,
                      "all_execution_and_transaction_outcomes_safe": True}}
    state_path = results / "state.json"
    ledger_path = results / "ledger.jsonl"
    state_path.write_text(json.dumps(state))
    ledger_path.write_text("\n".join(json.dumps(row) for row in ledger_rows) + "\n")
    result = review(repo_root=tmp_path, state_path=state_path, ledger_path=ledger_path,
                    result_path=results / "review.json", learning_path=results / "learning.json")
    assert result["passed"] is True
    assert result["gate"]["exact_commitment_and_outcome_rows"] == 12
    assert json.loads(state_path.read_text())["status"] == "INTERNALLY_PROMOTED_BY_CAU"
