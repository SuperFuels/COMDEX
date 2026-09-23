from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from backend.modules.hexcore.open_useful_objective_acquisition import run_once


def _row(cycle: int) -> dict:
    row = {
        "cycle": cycle,
        "observed_at": (datetime(2026, 1, 1, tzinfo=timezone.utc) + timedelta(minutes=2 * cycle)).isoformat(),
        "commitment_sha256": hashlib.sha256(f"commit-{cycle}".encode()).hexdigest(),
        "outcomes": {
            "cpython": {"family": "public_source_control", "authority": "https://example/cpython",
                        "reachable": True, "revision": "stable-python"},
            "node": {"family": "public_source_control", "authority": "https://example/node",
                     "reachable": True, "revision": "stable-node"},
            "numpy_release": {"family": "public_package_registry", "authority": "https://example/numpy",
                              "reachable": True, "revision": "stable-numpy", "value": "2.5.1"},
            "madrid_weather": {"family": "public_environmental_sensor", "authority": "https://example/weather",
                               "reachable": True, "revision": f"weather-{cycle}",
                               "temperature": 30.0 + cycle * .1, "wind": 8.0 + cycle * .1},
        },
        "changes": [],
    }
    row["outcome_sha256"] = hashlib.sha256(
        json.dumps(row, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    return row


def _install_documents(repo: Path) -> None:
    root = repo / "backend/modules/hexcore/data/cross_domain_semantic_transfer"
    root.mkdir(parents=True, exist_ok=True)
    (root / "python_design_faq.html").write_text("<p>Why Python uses this design is explained here.</p>")
    (root / "nasa_climate_faq.html").write_text("<p>Global warming is discussed with reported evidence.</p>")
    (root / "constitution_questions_answers.html").write_text("<p>The Constitution source answers this question.</p>")


def test_varied_objectives_are_induced_and_closed_by_later_authority(tmp_path: Path) -> None:
    repo = tmp_path / "repo"; repo.mkdir()
    _install_documents(repo)
    ledger = repo / "results/public.jsonl"
    state = repo / "state/state.json"
    result_path = repo / "results/result.json"
    workspace = repo / "results/work"
    result = {}
    for cycle in range(1, 9):
        ledger.parent.mkdir(parents=True, exist_ok=True)
        with ledger.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(_row(cycle), sort_keys=True) + "\n")
        result = run_once(repo_root=repo, state_path=state, public_outcome_ledger=ledger,
                          workspace_root=workspace, result_path=result_path, minimum_objectives=6)

    assert result["passed"] is True
    assert result["gate"]["later_confirmed"] >= 6
    assert result["gate"]["objective_families"] == 5
    assert result["gate"]["unique_objectives"] == result["gate"]["objectives_created"]
    assert result["gate"]["weakest_family_success"] == 1.0
    assert result["gate"]["owner_interventions"] == 0
    assert result["gate"]["unsafe_live_writes"] == 0
    assert result["gate"]["artifact_action_reduction_vs_fixed_three_lane"] == 2 / 3
    assert any(row["selection_evidence"].get("rejected_alternatives") for row in result["recent_objectives"])
    families = {row["family"] for row in result["recent_objectives"]}
    assert families == {"research_investigation", "software_tool", "data_decision",
                        "mathematical_reasoning", "document_evidence"}


def test_restart_does_not_duplicate_an_open_objective(tmp_path: Path) -> None:
    repo = tmp_path / "repo"; repo.mkdir()
    ledger = repo / "results/public.jsonl"; ledger.parent.mkdir(parents=True)
    ledger.write_text(json.dumps(_row(1)) + "\n", encoding="utf-8")
    kwargs = dict(repo_root=repo, state_path=repo / "state/state.json", public_outcome_ledger=ledger,
                  workspace_root=repo / "results/work", result_path=repo / "results/result.json")
    first = run_once(**kwargs); second = run_once(**kwargs)
    assert first["gate"]["objectives_created"] == 1
    assert second["gate"]["objectives_created"] == 1
    assert second["active_objective"]["commitment_sha256"] == first["active_objective"]["commitment_sha256"]


def test_same_moment_or_too_early_observation_cannot_close_credit(tmp_path: Path) -> None:
    repo = tmp_path / "repo"; repo.mkdir()
    ledger = repo / "results/public.jsonl"; ledger.parent.mkdir(parents=True)
    first_row = _row(1)
    ledger.write_text(json.dumps(first_row) + "\n", encoding="utf-8")
    kwargs = dict(repo_root=repo, state_path=repo / "state/state.json", public_outcome_ledger=ledger,
                  workspace_root=repo / "results/work", result_path=repo / "results/result.json")
    run_once(**kwargs)
    too_early = _row(2)
    too_early["observed_at"] = (datetime.fromisoformat(first_row["observed_at"]) + timedelta(seconds=30)).isoformat()
    body = dict(too_early); body.pop("outcome_sha256")
    too_early["outcome_sha256"] = hashlib.sha256(
        json.dumps(body, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    with ledger.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(too_early) + "\n")
    result = run_once(**kwargs)
    assert result["gate"]["objectives_closed"] == 0
    assert result["active_objective"]["status"] == "waiting_for_later_authority"
