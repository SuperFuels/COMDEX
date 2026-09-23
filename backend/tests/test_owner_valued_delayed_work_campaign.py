import json
from pathlib import Path

from backend.modules.hexcore.canonical_cognitive_runtime import _canonical_hash
from backend.modules.hexcore.owner_valued_delayed_work_campaign import run_once


def _outcome(cycle: int) -> dict:
    row = {
        "cycle": cycle, "observed_at": f"t-{cycle}", "commitment_sha256": f"commit-{cycle}",
        "outcomes": {
            "cpython": {"reachable": True, "revision": "py", "family": "public_source_control"},
            "node": {"reachable": True, "revision": "node", "family": "public_source_control"},
            "numpy_release": {"reachable": True, "revision": "pkg", "value": "2.3", "family": "public_package_registry"},
            "madrid_weather": {"reachable": True, "revision": f"weather-{cycle}", "temperature": 25 + cycle / 10, "wind": 5, "family": "public_environmental_sensor"},
        },
        "scores": {}, "classification": "stable_observation", "response": "retain_and_monitor",
        "changes": [], "acquisition_failures": [], "internal_self_repair_triggered": False,
    }
    row["outcome_sha256"] = _canonical_hash(row)
    return row


def _append(path: Path, row: dict) -> None:
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, sort_keys=True) + "\n")


def test_three_owner_work_lanes_require_later_rows_and_repeat(tmp_path: Path):
    ledger = tmp_path / "public.jsonl"
    arguments = dict(repo_root=tmp_path, state_path=tmp_path/"state.json",
                     public_outcome_ledger=ledger, workspace_root=tmp_path/"work",
                     result_path=tmp_path/"result.json", minimum_generations=3)
    result = None
    for cycle in range(1, 5):
        _append(ledger, _outcome(cycle))
        result = run_once(**arguments)
    assert result is not None and result["passed"] is True
    assert result["gate"]["consequence_confirmed_generations"] == 3
    assert result["gate"]["owner_valued_artifacts"] == 12
    assert result["gate"]["cross_domain_work_lanes"] == 3
    assert result["gate"]["research_success_rate"] == 1.0
    assert result["gate"]["software_success_rate"] == 1.0
    assert result["gate"]["data_decision_success_rate"] == 1.0
    assert result["gate"]["owner_interventions"] == 0
    assert result["gate"]["verified_executive_work_outcomes"] == 3


def test_first_generation_waits_and_cannot_self_certify(tmp_path: Path):
    ledger = tmp_path / "public.jsonl"; _append(ledger, _outcome(1))
    result = run_once(repo_root=tmp_path, state_path=tmp_path/"state.json",
                      public_outcome_ledger=ledger, workspace_root=tmp_path/"work",
                      result_path=tmp_path/"result.json", minimum_generations=3)
    assert result["passed"] is False
    assert result["gate"]["closed_by_later_consequence"] == 0
    assert result["active_generation"]["status"] == "waiting_for_later_public_outcome"
