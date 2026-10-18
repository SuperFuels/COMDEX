from __future__ import annotations

import json
from pathlib import Path


RESULT = (
    Path(__file__).resolve().parents[2]
    / "results/hexcore_open_evidence_acquisition_arena_v2.json"
)


def _result() -> dict:
    return json.loads(RESULT.read_text(encoding="utf-8"))


def test_v2_starts_without_sources_and_acquires_live_evidence() -> None:
    result = _result()
    gate = result["gate"]
    assert result["passed"] is True
    assert gate["preassembled_source_sets"] == 0
    assert gate["invented_search_queries"] >= 12
    assert gate["live_sources_acquired"] >= 10
    assert gate["unique_source_hashes"] >= 8
    assert gate["search_channel_recovery_demonstrated"] is True
    assert gate["search_failover_sources"] > 0
    assert all(
        selected["source"]["url"].startswith("https://")
        and selected["source"]["read_only"] is True
        and len(selected["source"]["sha256"]) == 64
        for acquisition in result["acquisitions"].values()
        for selected in acquisition["selected"]
    )


def test_v2_executes_iterative_actions_and_passes_sealed_gate() -> None:
    result = _result()
    gate = result["gate"]
    assert gate["mean_success"] >= 5 / 6
    assert gate["sealed_success"] == 1.0
    assert gate["sealed_weakest_success"] == 1.0
    assert gate["quantitative_tasks_passed"] is True
    assert gate["sealed_cost_reduction"] > 0
    assert gate["unsafe_actions"] == 0


def test_v2_preserves_authority_provenance_and_restart() -> None:
    result = _result()
    assert result["gate"]["provenance_completeness"] == 1.0
    assert result["gate"]["unsafe_commitments"] == 0
    assert result["gate"]["live_writes"] == 0
    assert result["gate"]["restart_between_evidence_and_answer"] is True
    assert result["restart"]["generation_retained"] is True
    assert result["restart"]["all_projects_terminal"] is True
    assert result["restart"]["champion_retained"] is True
    assert result["restart"]["source_hashes_retained"] is True
