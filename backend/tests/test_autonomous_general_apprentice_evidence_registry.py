from __future__ import annotations

import json
from pathlib import Path

from backend.modules.hexcore.autonomous_general_apprentice_evidence_registry import build_registry


def _write(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_registry_fails_closed_and_does_not_count_executor_installation(tmp_path: Path) -> None:
    _write(tmp_path / "results/aion_progressive_competency_status.json", {
        "summary": {"executor_coverage": 44},
        "subjects": {"python": {"overall_level": "intermediate"}, "math": {"overall_level": "advanced"}},
    })
    _write(tmp_path / "results/hexcore_open_useful_objectives.json", {
        "gate": {"later_confirmed": 6, "objective_families": 3},
        "recent_objectives": [{"status": "consequence_confirmed", "owner_interventions": 0} for _ in range(6)],
    })
    _write(tmp_path / "results/hexcore_cross_domain_consequence_repair.json", {
        "gate": {"consequence_confirmed_repairs": 2, "distinct_internal_domains": 2}})
    result = build_registry(tmp_path, tmp_path / "results/aga.json")
    assert result["authorized"] is False
    assert result["scope_profiles"]["full_aga"]["total"] == 11
    assert result["scope_profiles"]["technical_aga"]["total"] == 10
    assert result["scope_profiles"]["technical_aga"]["excluded_gates"] == ["social_creative_grounding"]
    assert result["gates"]["advanced_domains"]["observed"] == 1
    assert result["gates"]["declining_intervention"]["passed"] is True
    assert result["summary"]["executor_installations_count_as_mastery"] is False
    assert result["gates"]["social_creative_grounding"]["status"] == "blocked"


def test_registry_history_is_hash_chained(tmp_path: Path) -> None:
    result_path = tmp_path / "results/aga.json"; history = tmp_path / "results/aga.jsonl"
    first = build_registry(tmp_path, result_path, history)
    second = build_registry(tmp_path, result_path, history)
    rows = [json.loads(line) for line in history.read_text().splitlines()]
    assert rows[0]["prior_commitment"] == ""
    assert rows[1]["prior_commitment"] == first["evidence_commitment"]
    assert second["authorized"] is False


def test_frozen_technical_baseline_survives_new_uptime_window(tmp_path: Path) -> None:
    result_path = tmp_path / "results/aga.json"
    history = tmp_path / "results/aga.jsonl"
    history.parent.mkdir(parents=True)
    history.write_text(json.dumps({
        "recorded_at": "2026-08-08T06:49:07+00:00",
        "evidence_commitment": "sealed-technical-v1",
        "prior_commitment": "prior",
        "authorized": False,
        "passed_gates": 10,
    }) + "\n", encoding="utf-8")
    _write(tmp_path / "results/aion_progressive_competency_status.json", {
        "subjects": {
            "a": {"overall_level": "expert", "group": "one"},
            "b": {"overall_level": "expert", "group": "two"},
            **{f"advanced-{i}": {"overall_level": "advanced", "group": str(i)} for i in range(4)},
        },
    })
    _write(tmp_path / "results/hexcore_open_useful_objectives.json", {
        "gate": {"later_confirmed": 20, "objective_families": 5},
        "recent_objectives": [
            {"status": "consequence_confirmed", "owner_interventions": 0} for _ in range(6)
        ],
    })
    _write(tmp_path / "results/hexcore_cross_domain_consequence_repair.json", {
        "gate": {"consequence_confirmed_repairs": 3, "distinct_internal_domains": 3},
    })
    _write(tmp_path / "results/hexcore_cross_domain_method_transfer.json", {
        "gate": {"verified_transfers": 3},
    })
    _write(tmp_path / "results/hexcore_later_confirmed_cognitive_code_improvement.json", {
        "gate": {"later_confirmed_improvements": 1},
    })
    result = build_registry(tmp_path, result_path, history)
    assert result["gates"]["week_retention"]["status"] == "passed_frozen_baseline"
    assert result["scope_profiles"]["technical_aga"]["authorized"] is True
    assert result["scope_profiles"]["full_aga"]["authorized"] is False
