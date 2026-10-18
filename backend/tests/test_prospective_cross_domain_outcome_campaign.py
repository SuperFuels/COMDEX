import json
from pathlib import Path

from backend.modules.hexcore.prospective_cross_domain_outcome_campaign import run_cycle


def test_predictions_are_committed_then_scored_across_three_public_families(tmp_path: Path):
    calls = {"count": 0}

    def collector():
        calls["count"] += 1
        cycle = calls["count"]
        return {
            "cpython": {"reachable": True, "revision": "py-2" if cycle >= 4 else "py-1", "family": "public_source_control"},
            "node": {"reachable": True, "revision": "node-1", "family": "public_source_control"},
            "numpy_release": {"reachable": True, "revision": "pkg", "value": "2.3.1", "family": "public_package_registry"},
            "madrid_weather": {"reachable": True, "revision": f"w-{cycle}", "temperature": 30 + cycle / 10, "wind": 8, "family": "public_environmental_sensor"},
        }

    paths = {
        "repo_root": tmp_path,
        "state_path": tmp_path / "state.json",
        "commitment_ledger": tmp_path / "commitments.jsonl",
        "outcome_ledger": tmp_path / "outcomes.jsonl",
        "result_path": tmp_path / "result.json",
        "collector": collector,
        "minimum_cycles": 6,
        "minimum_elapsed_seconds": 0,
    }
    result = None
    for _ in range(6):
        result = run_cycle(**paths)
    assert result is not None and result["passed"] is True
    assert result["gate"]["independent_authority_families"] == 3
    assert result["gate"]["scored_forecasts"] == 20
    assert result["gate"]["forecast_accuracy"] >= .75
    assert result["gate"]["owner_interventions"] == 0
    commitments = [json.loads(line) for line in paths["commitment_ledger"].read_text().splitlines()]
    outcomes = [json.loads(line) for line in paths["outcome_ledger"].read_text().splitlines()]
    assert len(commitments) == len(outcomes) == 6
    assert all(outcome["commitment_sha256"] == commitment["commitment_sha256"]
               for commitment, outcome in zip(commitments, outcomes))


def test_unreachable_public_authority_abstains_from_scoring(tmp_path: Path):
    def collector():
        return {
            "cpython": {"reachable": False, "revision": None, "family": "public_source_control"},
            "node": {"reachable": True, "revision": "n", "family": "public_source_control"},
            "numpy_release": {"reachable": True, "revision": "p", "value": "1", "family": "public_package_registry"},
            "madrid_weather": {"reachable": True, "revision": "w", "temperature": 20, "wind": 2, "family": "public_environmental_sensor"},
        }
    result = run_cycle(repo_root=tmp_path, state_path=tmp_path/"state.json",
                       commitment_ledger=tmp_path/"c.jsonl", outcome_ledger=tmp_path/"o.jsonl",
                       result_path=tmp_path/"r.json", collector=collector, minimum_cycles=6,
                       minimum_elapsed_seconds=0)
    assert result["passed"] is False
    assert result["latest_cycle"]["classification"] == "evidence_acquisition_failure"
    assert result["gate"]["external_events_misrouted_to_self_repair"] == 0
