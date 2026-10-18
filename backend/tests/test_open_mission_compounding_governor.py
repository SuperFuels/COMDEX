from datetime import datetime, timedelta, timezone

import pytest

from backend.modules.hexcore.open_mission_compounding_governor import (
    ARMS,
    OpenMissionCompoundingGovernor,
    frozen_campaign_contract,
)
from backend.modules.hexcore import open_mission_compounding_executor as executor


def _contract(start=None):
    return frozen_campaign_contract(
        proposer_id="fixed-proposer-v1",
        tool_manifest_hash="a" * 64,
        action_budget=20,
        started_at=start,
    )


def _mission():
    return {
        "mission_id": "repo-repair-1",
        "lane": "software_systems",
        "objective": "Repair an unfamiliar repository failure.",
        "evaluator_authority": "hidden-ci",
        "success_contract": {
            "frozen_before_execution": True,
            "required": ["hidden_tests_pass", "no_regression"],
        },
        "source_policy": {"closes_after_learning": True},
        "risk_class": "disposable_sandbox",
    }


def test_contract_is_immutable_and_rejects_self_grading(tmp_path):
    governor = OpenMissionCompoundingGovernor(state_path=tmp_path / "state.json")
    governor.authorize(_contract())
    with pytest.raises(ValueError):
        governor.authorize(frozen_campaign_contract(
            proposer_id="different-proposer",
            tool_manifest_hash="a" * 64,
            action_budget=20,
        ))
    bad = _mission()
    bad["evaluator_authority"] = "aion"
    with pytest.raises(ValueError):
        governor.register_mission(bad)


def test_ablation_parity_and_ten_x_claim_are_fail_closed(tmp_path):
    governor = OpenMissionCompoundingGovernor(state_path=tmp_path / "state.json")
    contract = governor.authorize(_contract())
    mission = governor.register_mission(_mission())
    for arm in ARMS:
        full = arm == "full_aion"
        governor.record_outcome({
            "mission_id": mission["mission_id"],
            "mission_hash": mission["mission_hash"],
            "arm": arm,
            "proposer_id": contract["proposer_id"],
            "tool_manifest_hash": contract["tool_manifest_hash"],
            "action_budget": contract["action_budget_per_arm"],
            "evaluator_authority": "hidden-ci",
            "success": True,
            "unsafe_actions": 0,
            "human_intervention_minutes": 1 if full else 20,
            "verified_work_units": 10,
            "investigation_actions": 1 if full else 20,
        })
    snapshot = governor.snapshot()
    assert snapshot["cohort_complete_missions"] == 1
    assert snapshot["full_aion_efficiency_ratio_vs_proposer"] == 20.0
    assert snapshot["ten_x_claim_gate_passed"] is True
    tampered = governor.record_outcome({
        "mission_id": mission["mission_id"],
        "mission_hash": mission["mission_hash"],
        "arm": "full_aion",
        "proposer_id": "stronger-model",
        "tool_manifest_hash": contract["tool_manifest_hash"],
        "action_budget": contract["action_budget_per_arm"],
        "evaluator_authority": "hidden-ci",
        "success": True,
        "unsafe_actions": 0,
    })
    assert tampered["eligible"] is False
    assert tampered["verified_success"] is False


def test_retention_cannot_mature_early_or_replay_sources(tmp_path):
    start = datetime(2026, 8, 8, tzinfo=timezone.utc)
    governor = OpenMissionCompoundingGovernor(state_path=tmp_path / "state.json")
    governor.authorize(_contract(start))
    governor.register_mission(_mission())
    governor.close_source(mission_id="repo-repair-1", closed_at=start)
    early = governor.record_retention({
        "mission_id": "repo-repair-1", "evaluator_authority": "hidden-ci",
        "passed": True, "source_accessed": False,
    }, now=start + timedelta(days=6))
    assert early["verified"] is False
    replay = governor.record_retention({
        "mission_id": "repo-repair-1", "evaluator_authority": "hidden-ci",
        "passed": True, "source_accessed": True,
    }, now=start + timedelta(days=7))
    assert replay["verified"] is False
    mature = governor.record_retention({
        "mission_id": "repo-repair-1", "evaluator_authority": "hidden-ci",
        "passed": True, "source_accessed": False,
    }, now=start + timedelta(days=7))
    assert mature["verified"] is True


def test_mature_retention_is_single_shot_and_calibration_is_excluded(tmp_path):
    start = datetime(2026, 8, 8, tzinfo=timezone.utc)
    governor = OpenMissionCompoundingGovernor(state_path=tmp_path / "state.json")
    governor.authorize(_contract(start))
    diagnostic = governor.register_mission(_mission())
    governor.close_source(mission_id=diagnostic["mission_id"], closed_at=start)
    failed = governor.record_retention({
        "mission_id": diagnostic["mission_id"], "evaluator_authority": "hidden-ci",
        "passed": False, "source_accessed": False,
    }, now=start + timedelta(days=7))
    assert failed["verified"] is False

    calibration = _mission()
    calibration["mission_id"] = "moonshot_public_change_forecast_v2_cursor_test"
    registered = governor.register_mission(calibration)
    governor.close_source(mission_id=registered["mission_id"], closed_at=start)

    snapshot = governor.snapshot(now=start + timedelta(days=8))
    assert diagnostic["mission_id"] not in snapshot["retention_due_missions"]
    assert registered["mission_id"] not in snapshot["retention_due_missions"]
    assert snapshot["retention_attempted_count"] == 1
    assert snapshot["failed_retention_count"] == 1
    assert snapshot["status"] == "retention_followup"


def test_due_structured_retention_uses_fresh_variant_once(tmp_path, monkeypatch):
    start = datetime(2026, 8, 8, tzinfo=timezone.utc)
    state = tmp_path / "backend/modules/hexcore/data/open_mission_compounding/state.json"
    governor = OpenMissionCompoundingGovernor(state_path=state)
    governor.authorize(_contract(start))
    spec = executor.STRUCTURED_REPAIR_SPECS[0]
    mission = governor.register_mission({
        "mission_id": spec["mission_id"], "lane": "software_systems",
        "objective": spec["objective"], "evaluator_authority": spec["authority"],
        "success_contract": {
            "frozen_before_execution": True,
            "required": ["base_hidden_tests", "later_repair_confirmation", "no_regression"],
        },
        "source_policy": {"closes_after_learning": True, "fault_answer_visible_to_proposer": False},
        "risk_class": "disposable_structured_system_sandbox",
    })
    governor.close_source(mission_id=mission["mission_id"], closed_at=start)
    monkeypatch.setattr(executor, "_propose_structured_order", lambda model, spec, memory: {
        "available": True, "order": [spec["correct"]], "domain_memory_applied": memory,
    })

    first = executor.run_due_retention(
        repo_root=tmp_path, now=start + timedelta(days=7)
    )
    second = executor.run_due_retention(
        repo_root=tmp_path, now=start + timedelta(days=7, minutes=1)
    )

    assert first["status"] == "completed"
    assert len(first["receipts"]) == 1
    assert first["receipts"][0]["verified"] is True
    assert first["receipts"][0]["source_accessed"] is False
    assert "retention-" in first["receipts"][0]["renamed_application"]
    assert second["status"] == "nothing_due"
    final = OpenMissionCompoundingGovernor(state_path=state).state
    assert len(final["retention_receipts"]) == 1


def test_due_repository_retention_uses_fresh_disposable_repo_once(tmp_path, monkeypatch):
    start = datetime(2026, 8, 8, tzinfo=timezone.utc)
    state = tmp_path / "backend/modules/hexcore/data/open_mission_compounding/state.json"
    governor = OpenMissionCompoundingGovernor(state_path=state)
    governor.authorize(_contract(start))
    mission = _mission()
    mission["mission_id"] = executor.REPO_MISSION_ID
    mission["evaluator_authority"] = "deterministic-repository-integrity-evaluator"
    registered = governor.register_mission(mission)
    governor.close_source(mission_id=registered["mission_id"], closed_at=start)
    monkeypatch.setattr(executor, "_propose_repo_order", lambda model, memory: {
        "available": True,
        "order": ["validate_then_atomic_promote"],
        "domain_memory_applied": memory,
    })

    first = executor.run_due_retention(
        repo_root=tmp_path, now=start + timedelta(days=7)
    )
    second = executor.run_due_retention(
        repo_root=tmp_path, now=start + timedelta(days=7, minutes=1)
    )

    assert first["status"] == "completed"
    assert len(first["receipts"]) == 1
    assert first["receipts"][0]["verified"] is True
    assert first["receipts"][0]["source_accessed"] is False
    assert first["receipts"][0]["evaluation_mode"] == "fresh_disposable_repository_variant"
    assert second["status"] == "nothing_due"
    final = OpenMissionCompoundingGovernor(state_path=state).state
    assert len(final["retention_receipts"]) == 1


def test_induced_repairs_require_precommit_and_later_authority(tmp_path):
    governor = OpenMissionCompoundingGovernor(state_path=tmp_path / "state.json")
    governor.authorize(_contract())
    invalid = governor.record_repair({
        "fault_kind": "induced_answer_hidden",
        "fault_commitment_before_solver_start": False,
        "later_independent_confirmation": True,
        "confirmation_authority": "hidden-ci",
    })
    assert invalid["eligible"] is False
    valid = governor.record_repair({
        "fault_kind": "induced_answer_hidden",
        "fault_commitment_before_solver_start": True,
        "later_independent_confirmation": True,
        "confirmation_authority": "hidden-ci",
    })
    assert valid["eligible"] is True


def test_polyglot_hidden_authority_requires_preserved_quarantine():
    assert executor._evaluate("accept_and_continue", prefix="accept")["passed"] is False
    assert executor._evaluate("discard_unreadable", prefix="discard")["passed"] is False
    assert executor._evaluate("isolate_preserve_then_continue", prefix="retain")["passed"] is True


def test_memory_and_repair_ablations_change_only_declared_capabilities(monkeypatch):
    monkeypatch.setattr(executor, "_propose_order", lambda model, memory: {
        "available": True,
        "order": ["accept_and_continue", "isolate_preserve_then_continue", "discard_unreadable"],
        "latency_seconds": 0.0,
        "prompt_hash_input_includes_memory": memory,
    })
    full = executor.execute_arm(
        arm="full_aion", proposer_id="fixed", action_budget=40
    )
    no_memory = executor.execute_arm(
        arm="aion_no_memory", proposer_id="fixed", action_budget=40
    )
    no_repair = executor.execute_arm(
        arm="proposer_only", proposer_id="fixed", action_budget=40
    )
    assert full["passed"] is True and len(full["attempts"]) == 1
    assert no_memory["passed"] is True and len(no_memory["attempts"]) == 2
    assert no_repair["passed"] is False and len(no_repair["attempts"]) == 1


def test_public_forecasts_are_calibration_not_ten_x_evidence(tmp_path):
    governor = OpenMissionCompoundingGovernor(state_path=tmp_path / "state.json")
    contract = governor.authorize(_contract())
    mission = _mission()
    mission["mission_id"] = "moonshot_public_change_forecast_v2_cursor_1"
    registered = governor.register_mission(mission)
    for arm in ARMS:
        governor.record_outcome({
            "mission_id": registered["mission_id"], "mission_hash": registered["mission_hash"],
            "arm": arm, "proposer_id": contract["proposer_id"],
            "tool_manifest_hash": contract["tool_manifest_hash"],
            "action_budget": contract["action_budget_per_arm"],
            "evaluator_authority": registered["evaluator_authority"],
            "success": arm == "full_aion", "unsafe_actions": 0,
            "verified_work_units": 1 if arm == "full_aion" else 0,
            "investigation_actions": 1,
        })
    snapshot = governor.snapshot()
    assert snapshot["calibration_outcomes_excluded_from_claim"] == len(ARMS)
    assert snapshot["arms"]["full_aion"]["eligible_outcomes"] == 0
    assert snapshot["ten_x_claim_gate_passed"] is False


def test_repository_fault_requires_repair_and_preserves_failed_bytes():
    corrupt = executor._evaluate_repo_strategy(
        "overwrite_canonical_in_place", prefix="corrupt", repair=True
    )
    base = executor._evaluate_repo_strategy(
        "validate_then_atomic_promote", prefix="no-repair", repair=False
    )
    repaired = executor._evaluate_repo_strategy(
        "validate_then_atomic_promote", prefix="repair", repair=True
    )
    assert corrupt["passed"] is False
    assert base["base_passed"] is True
    assert base["passed"] is False
    assert repaired["repair_performed"] is True
    assert repaired["later_confirmed"] is True
    assert repaired["quarantine_sha256"] is not None


def test_public_forecast_uses_one_frozen_neutral_proposal(tmp_path, monkeypatch):
    state = tmp_path / "backend/modules/hexcore/data/open_mission_compounding/state.json"
    governor = OpenMissionCompoundingGovernor(state_path=state)
    governor.authorize(_contract())
    calls = []
    monkeypatch.setattr(executor, "_propose_changes", lambda model, history, memory: (
        calls.append(memory) or {"available": True, "prediction": [], "memory": memory}
    ))
    result = executor.run_public_change(repo_root=tmp_path)
    pending = __import__("json").loads((state.parent / "public_change_pending.json").read_text())
    assert result["status"] == "precommitted"
    assert calls == [False]
    assert len({tuple(row["prediction"]) for row in pending["proposals"].values()}) == 1
    assert all(row["memory_policy"].startswith("quarantined") for row in pending["proposals"].values())


@pytest.mark.parametrize("family,correct", [
    ("schema_migration", "lossless_versioned_migration"),
    ("api_pagination", "cursor_checkpoint_idempotent_merge"),
    ("webhook_replay", "durable_idempotency_ledger"),
    ("configuration_precedence", "typed_layered_merge_with_provenance"),
    ("cache_coherence", "generation_keyed_read_through"),
    ("concurrent_reservation", "transactional_compare_and_set"),
    ("protocol_versioning", "explicit_version_adapter_registry"),
    ("access_policy_regression", "deny_first_scoped_policy"),
])
def test_structured_faults_require_later_repair_confirmation(family, correct):
    no_repair = executor._evaluate_structured_strategy(
        family=family, strategy=correct, repair=False
    )
    repaired = executor._evaluate_structured_strategy(
        family=family, strategy=correct, repair=True
    )
    assert no_repair["base_passed"] is True
    assert no_repair["passed"] is False
    assert repaired["repair_performed"] is True
    assert repaired["later_confirmed"] is True


def test_structured_transfer_waves_open_by_elapsed_campaign_time(tmp_path, monkeypatch):
    governor = OpenMissionCompoundingGovernor(state_path=tmp_path / "state.json")
    monkeypatch.setattr(executor, "_campaign_elapsed_hours", lambda _governor: 73.0)

    specs = executor._available_structured_specs(governor)
    next_wave = executor._next_structured_wave(governor)

    assert len(specs) == len(executor.STRUCTURED_REPAIR_SPECS) * 2
    assert sum(row.get("variant") == "transfer" for row in specs) == len(executor.STRUCTURED_REPAIR_SPECS)
    assert next_wave["name"] == "reduced_scaffolding"
