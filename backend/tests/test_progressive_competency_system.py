import json
import subprocess
import sys
import time
from pathlib import Path

from backend.modules.hexcore.progressive_competency_system import ProgressiveCompetencySystem
from backend.modules.hexcore.progressive_competency_executor import (
    PROJECTS, ProgressiveCompetencyExecutor, _run_program,
)


def _empty_repo(tmp_path: Path) -> ProgressiveCompetencySystem:
    return ProgressiveCompetencySystem(repo_root=tmp_path, state_path=tmp_path / "state.json")


def _record(system: ProgressiveCompetencySystem, subject_id: str, kind: str,
            skills: list[str], index: int, **overrides):
    body = dict(score=0.96, artifact=f"sealed/{index}.json", artifact_hash=f"hash-{index}",
                verified=True, source_disjoint=True, retained=False,
                independent_outcome=True, unfamiliar=True, scaffolding=0.2, trials=1,
                authority=["sealed_outcome"])
    body.update(overrides)
    return system.record_evidence(subject_id=subject_id, kind=kind, subskills=skills, **body)


def test_one_pass_is_not_advanced(tmp_path: Path):
    system = _empty_repo(tmp_path)
    system.register_mission_gap(
        mission="learn a new field", subject_name="Small Field", group="research",
        proposed_subskills=["alpha", "beta"], evidence="mission requires it",
    )
    _record(system, "mission_small_field", "assessment", ["alpha", "beta"], 1)
    result = system.assess("mission_small_field")
    assert result["knowledge_level"] == "beginner"
    assert result["practical_level"] == "unassessed"
    assert result["target_reached"] is False


def test_advanced_requires_repeated_subskills_projects_failures_transfer_and_retention(tmp_path: Path):
    system = _empty_repo(tmp_path)
    system.register_mission_gap(
        mission="learn a new field", subject_name="Deep Field", group="research",
        proposed_subskills=["alpha", "beta"], evidence="mission requires it",
    )
    sid = "mission_deep_field"
    # Every subskill receives repeated knowledge and practical evidence.
    for i, skill in enumerate(["alpha", "beta"]):
        _record(system, sid, "lesson", [skill], 10 + i)
        _record(system, sid, "knowledge_test", [skill], 20 + i)
        _record(system, sid, "exercise", [skill], 30 + i)
        _record(system, sid, "exercise", [skill], 40 + i)
    for i in range(5):
        _record(system, sid, "project", ["alpha", "beta"], 50 + i)
    for i in range(3):
        _record(system, sid, "debugging", ["alpha", "beta"], 60 + i)
    for i in range(2):
        _record(system, sid, "transfer", ["alpha", "beta"], 70 + i)
    _record(system, sid, "retention", ["alpha", "beta"], 80, retained=True)
    result = system.assess(sid)
    assert result["knowledge_level"] == "advanced"
    assert result["practical_level"] == "advanced"
    assert result["overall_level"] == "advanced"
    assert result["target_reached"] is True


def test_missing_unfamiliar_projects_are_scheduled_before_retention(tmp_path: Path):
    system = _empty_repo(tmp_path)
    row = {
        "target_level": "advanced",
        "per_subskill": {"alpha": {"knowledge": 2, "practical": 2}},
        "projects": 5, "unfamiliar_projects": 0, "debugging_cases": 3,
        "transfer_cases": 2, "retention_cases": 0, "independent_outcomes": 12,
        "trials": 30, "latest_scaffolding": 0.1,
    }
    requirement = system._next_requirement(row)
    assert requirement["kind"] == "project"
    assert requirement["novelty_required"] is True
    assert requirement["minimum_unfamiliar_projects"] == 3


def test_cross_domain_depth_targets_override_unfocused_breadth(tmp_path: Path):
    system = _empty_repo(tmp_path)
    system.configure_depth_acceleration(
        advanced_targets=["mathematics", "english"], expert_targets=["mathematics"]
    )
    assert system._priority_subject() in {"mathematics", "english"}
    lane = system.state["depth_acceleration"]
    assert lane["scheduling_only"] is True
    assert lane["awards_competency"] is False


def test_depth_configuration_supersedes_only_premature_unexecuted_retention(tmp_path: Path):
    system = _empty_repo(tmp_path)
    contract = {
        "contract_id": "legacy-retention", "subject_id": "mathematics", "status": "open",
        "requirement": {"kind": "retention", "not_before_epoch": time.time() + 1000},
    }
    system.state["contracts"].append(contract)
    lane = system.configure_depth_acceleration(
        advanced_targets=["mathematics"], expert_targets=[]
    )
    assert lane["superseded_premature_retention_contracts"] == ["legacy-retention"]
    assert contract["status"] == "superseded_missing_prerequisite"
    assert system.evidence_for("mathematics") == []


def test_advanced_subject_unlocks_expert_depth_without_waiting_for_all_subjects(tmp_path: Path):
    system = _empty_repo(tmp_path)
    system.register_mission_gap(
        mission="learn a new field", subject_name="Depth Lane", group="research",
        proposed_subskills=["alpha", "beta"], evidence="mission requires it",
    )
    sid = "mission_depth_lane"
    for i, skill in enumerate(["alpha", "beta"]):
        _record(system, sid, "lesson", [skill], 100 + i)
        _record(system, sid, "knowledge_test", [skill], 110 + i)
        _record(system, sid, "exercise", [skill], 120 + i)
        _record(system, sid, "exercise", [skill], 130 + i)
    for i in range(5): _record(system, sid, "project", ["alpha", "beta"], 140 + i)
    for i in range(3): _record(system, sid, "debugging", ["alpha", "beta"], 150 + i)
    for i in range(2): _record(system, sid, "transfer", ["alpha", "beta"], 160 + i)
    _record(system, sid, "retention", ["alpha", "beta"], 170, retained=True)
    assert system.assess(sid)["overall_level"] == "advanced"
    unlocked = system._unlock_expert_targets()
    assert sid in unlocked
    expert_assessment = system.assess(sid)
    assert expert_assessment["target_level"] == "expert"
    assert expert_assessment["target_reached"] is False
    assert system._next_requirement(expert_assessment)["kind"] == "project"
    system.state["lane_scheduler"].update({"breadth_contracts": 3, "depth_contracts": 0})
    assert system._priority_subject() == sid


def test_expert_requires_deeper_projects_recovery_transfer_and_retention(tmp_path: Path):
    system = _empty_repo(tmp_path)
    system.register_mission_gap(
        mission="learn a new field", subject_name="Expert Field", group="research",
        proposed_subskills=["alpha", "beta"], evidence="mission requires it",
    )
    sid = "mission_expert_field"
    system.state["subjects"][sid]["target_level"] = "expert"
    for i, skill in enumerate(["alpha", "beta"]):
        for repeat in range(4):
            _record(system, sid, "knowledge_test", [skill], 200 + i * 20 + repeat)
            _record(system, sid, "exercise", [skill], 210 + i * 20 + repeat)
    for i in range(12): _record(system, sid, "project", ["alpha", "beta"], 300 + i)
    for i in range(6): _record(system, sid, "debugging", ["alpha", "beta"], 320 + i)
    for i in range(4): _record(system, sid, "transfer", ["alpha", "beta"], 340 + i)
    for i in range(2):
        _record(system, sid, "retention", ["alpha", "beta"], 350 + i,
                retained=True, scaffolding=0.1)
    result = system.assess(sid)
    assert result["knowledge_level"] == "expert"
    assert result["practical_level"] == "expert"
    assert result["overall_level"] == "expert"
    assert result["target_reached"] is True


def test_theory_can_advance_while_physical_practice_remains_explicitly_blocked(tmp_path: Path):
    system = _empty_repo(tmp_path)
    sid = "embedded_robotics"
    for i in range(8):
        skills = system.state["subjects"][sid]["subskills"]
        _record(system, sid, "knowledge_test" if i % 2 else "lesson", skills, 100 + i, trials=2)
    result = system.assess(sid)
    assert result["knowledge_level"] == "advanced"
    assert result["practical_level"] == "unassessed"
    assert result["display_level"] == "advanced_theory_practical_blocked"
    assert result["open_blockers"]


def test_mission_gap_creates_persistent_curriculum_and_open_contract(tmp_path: Path):
    state = tmp_path / "state.json"
    system = ProgressiveCompetencySystem(repo_root=tmp_path, state_path=state)
    gap = system.register_mission_gap(
        mission="Build a pet-food company", subject_name="Pet Food Industry",
        group="business_science",
        proposed_subskills=["nutrition", "regulation", "manufacturing", "unit_economics"],
        evidence="mission analysis found no grounded domain knowledge",
    )
    outcome = system.step()
    assert gap["subject_id"] == "mission_pet_food_industry"
    assert outcome["cycle"]["action"]["subject_id"] == gap["subject_id"]
    restarted = ProgressiveCompetencySystem(repo_root=tmp_path, state_path=state)
    assert gap["gap_id"] in {row["gap_id"] for row in restarted.state["mission_gaps"]}
    assert restarted.summary()["open_contracts"] == 1


def test_open_executor_contract_becomes_visible_stall_not_false_progress(tmp_path: Path):
    system = _empty_repo(tmp_path)
    system.set_active_subject("python")
    first = system.step()["cycle"]["action"]
    contract = system.state["contracts"][-1]
    contract["created_epoch"] -= 1900
    system._save()
    second = system.step()["cycle"]["action"]
    assert first["status"] == "curriculum_contract_created"
    assert second["status"] == "stalled_executor_required"
    assert system.assess("python")["target_reached"] is False


def test_concurrent_state_transactions_remain_valid_and_preserve_both_updates(tmp_path: Path):
    state = tmp_path / "state.json"
    ProgressiveCompetencySystem(repo_root=tmp_path, state_path=state)
    script = """
import sys, time
from pathlib import Path
from backend.modules.hexcore.progressive_competency_system import ProgressiveCompetencySystem
root, state, subject, delay = Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3], float(sys.argv[4])
system = ProgressiveCompetencySystem(repo_root=root, state_path=state)
time.sleep(delay)
system.register_mission_gap(mission="concurrent " + subject, subject_name=subject,
    group="test", proposed_subskills=["one", "two"], evidence="independent transaction")
"""
    first = subprocess.Popen([sys.executable, "-c", script, str(tmp_path), str(state), "Concurrent Alpha", "0.2"])
    second = subprocess.Popen([sys.executable, "-c", script, str(tmp_path), str(state), "Concurrent Beta", "0.0"])
    assert first.wait(timeout=10) == 0
    assert second.wait(timeout=10) == 0
    recovered = json.loads(state.read_text(encoding="utf-8"))
    gap_subjects = {row["subject_id"] for row in recovered["mission_gaps"]}
    assert {"mission_concurrent_alpha", "mission_concurrent_beta"} <= gap_subjects
    assert not list(tmp_path.glob(".state.json.*.tmp"))


def test_malformed_trailing_payload_is_rejected_without_overwriting_evidence(tmp_path: Path):
    state = tmp_path / "state.json"
    system = ProgressiveCompetencySystem(repo_root=tmp_path, state_path=state)
    original = state.read_bytes()
    state.write_bytes(original + b"truncated-second-payload")
    try:
        ProgressiveCompetencySystem(repo_root=tmp_path, state_path=state)
    except json.JSONDecodeError:
        pass
    else:
        raise AssertionError("malformed trailing state was accepted")
    assert state.read_bytes() == original + b"truncated-second-payload"


def test_future_retention_parks_only_subject_and_curriculum_continues(tmp_path: Path):
    system = _empty_repo(tmp_path)
    system._add_subject("testing_debugging", "Testing and Debugging", "computing",
                        ["unit"], importance=1.0, source="test")
    system.set_active_subject("testing_debugging")
    system.state["contracts"].append({
        "contract_id": "future-retention", "subject_id": "testing_debugging",
        "status": "open", "created_epoch": time.time(),
        "requirement": {"kind": "retention", "subskills": ["unit"],
                        "authority": "elapsed_closed_book_fresh_tasks",
                        "not_before_epoch": time.time() + 3600},
    })
    system._save()
    action = system.step()["cycle"]["action"]
    assert action["status"] == "curriculum_contract_created"
    assert action["subject_id"] != "testing_debugging"
    assert system.state["active_subject_id"] == action["subject_id"]


def test_executor_skips_future_retention_and_executes_other_available_work(tmp_path: Path):
    system = _empty_repo(tmp_path)
    system._add_subject("testing_debugging", "Testing and Debugging", "computing",
                        ["unit"], importance=1.0, source="test")
    system._add_subject("advanced_python", "Advanced Python", "computing",
                        ["asyncio"], importance=1.0, source="test")
    system.state["contracts"].extend([
        {"contract_id": "future-retention", "subject_id": "testing_debugging",
         "status": "open", "created_epoch": time.time(),
         "requirement": {"kind": "retention", "subskills": ["unit"],
                         "not_before_epoch": time.time() + 3600}},
        {"contract_id": "new-work", "subject_id": "advanced_python",
         "status": "open", "created_epoch": time.time(),
         "requirement": {"kind": "lesson", "subskills": ["asyncio"]}},
    ])
    system.set_active_subject("advanced_python")
    system._save()
    executor = ProgressiveCompetencyExecutor(
        system=system, state_path=tmp_path / "executor.json",
        result_dir=tmp_path / "results" / "progressive_competency",
    )
    outcome = executor.step()
    assert outcome["status"] == "verified_and_recorded"
    assert outcome["subject_id"] == "advanced_python"
    assert outcome["progressed"] is True


def test_progressive_executor_records_real_counterexample_grounded_outcome(tmp_path: Path):
    system = _empty_repo(tmp_path)
    system._add_subject(
        "testing_debugging", "Testing and Debugging", "computing",
        ["unit", "integration", "property_testing", "fault_localisation", "observability", "regression"],
        importance=1.0, source="test",
    )
    system.set_active_subject("testing_debugging")
    system.step()
    executor = ProgressiveCompetencyExecutor(
        system=system, state_path=tmp_path / "executor.json",
        result_dir=tmp_path / "results" / "progressive_competency",
    )
    outcome = executor.step()
    assert outcome["progressed"] is True
    assert system.evidence_for("testing_debugging")[-1]["independent_outcome"] is True
    result = json.loads((tmp_path / outcome["result_path"]).read_text())
    assert result["gate"]["unsafe_variants_rejected"] == 6
    assert result["gate"]["counterexamples_rejected"] == result["gate"]["counterexamples_total"]


def test_python_core_progresses_from_interpreter_and_counterexample_authority(tmp_path: Path):
    system = _empty_repo(tmp_path)
    system._add_subject("python_core", "Python Core", "computing",
                        ["basic_testing", "collections", "errors", "functions",
                         "input_security", "language_semantics"],
                        importance=1.0, source="test")
    system.set_active_subject("python_core")
    contract = system.step()["cycle"]["action"]
    executor = ProgressiveCompetencyExecutor(
        system=system, state_path=tmp_path / "executor.json",
        result_dir=tmp_path / "results" / "progressive_competency",
    )
    outcome = executor.step()
    assert contract["status"] == "curriculum_contract_created"
    assert outcome["progressed"] is True
    evidence = system.evidence_for("python_core")[-1]
    assert evidence["subskills"] == ["basic_testing"]
    result = json.loads((tmp_path / outcome["result_path"]).read_text())
    assert result["authority_boundary"].startswith("Python execution")
    assert result["gate"]["counterexamples_rejected"] == result["gate"]["counterexamples_total"]


def test_advanced_python_uses_real_sealed_package_executor(tmp_path: Path):
    system = _empty_repo(tmp_path)
    system._add_subject("advanced_python", "Advanced Python", "computing",
                        ["asyncio", "context_managers", "generators", "packaging",
                         "profiling", "protocols", "typing"],
                        importance=1.0, source="test")
    system.set_active_subject("advanced_python")
    system.step()
    executor = ProgressiveCompetencyExecutor(
        system=system, state_path=tmp_path / "executor.json",
        result_dir=tmp_path / "results/progressive_competency",
    )
    outcome = executor.step()
    assert outcome["progressed"] is True
    result = json.loads((tmp_path / outcome["result_path"]).read_text())
    assert result["gate"]["candidate_execution_passed"] is True
    assert result["gate"]["source_disjoint_transfer"] is True
    assert result["gate"]["unsafe_variants_rejected"] == result["gate"]["unsafe_variants_total"]


def test_algorithms_progresses_with_fresh_executable_counterexample(tmp_path: Path):
    system = _empty_repo(tmp_path)
    system._add_subject(
        "algorithms_data_structures", "Algorithms and Data Structures", "computing",
        ["arrays", "complexity", "dynamic_programming", "graphs", "maps", "search", "sorting", "trees"],
        importance=1.0, source="test",
    )
    system.set_active_subject("algorithms_data_structures")
    system.step()
    executor = ProgressiveCompetencyExecutor(
        system=system, state_path=tmp_path / "executor.json",
        result_dir=tmp_path / "results/progressive_competency",
    )
    outcome = executor.step()
    assert outcome["progressed"] is True
    result = json.loads((tmp_path / outcome["result_path"]).read_text())
    assert result["gate"]["candidate_execution_passed"] is True
    assert result["gate"]["counterexamples_rejected"] == 1
    assert result["gate"]["unsafe_variants_rejected"] == result["gate"]["unsafe_variants_total"]


def test_unsupported_subject_is_explicitly_parked_so_scheduler_can_rotate(tmp_path: Path):
    system = _empty_repo(tmp_path)
    system.register_mission_gap(
        mission="learn unfamiliar domain", subject_name="Unfamiliar Domain", group="research",
        proposed_subskills=["alpha"], evidence="mission gap",
    )
    system.set_active_subject("mission_unfamiliar_domain")
    system.step()
    executor = ProgressiveCompetencyExecutor(
        system=system, state_path=tmp_path / "executor.json",
        result_dir=tmp_path / "results/progressive_competency",
    )
    outcome = executor.step()
    assert outcome["status"] == "executor_acquisition_required"
    assert outcome["acquisition_action"] == "invent_and_verify_progressive_adapter"
    durable_events = [json.loads(line) for line in
                      (tmp_path / "event_ledger.jsonl").read_text().splitlines()]
    assert durable_events[-1]["status"] == "executor_acquisition_required"
    assert durable_events[-1]["event_id"].startswith("executor_event_")
    assert any(
        row["subject_id"] == "mission_unfamiliar_domain"
        and row["blocker_type"] == "executor_capability"
        and row["status"] == "open"
        for row in system.state["blockers"]
    )
    next_cycle = system.step()["cycle"]["action"]
    assert next_cycle.get("subject_id") != "mission_unfamiliar_domain"


def test_active_unsupported_subject_never_borrows_unrelated_executor(tmp_path: Path):
    system = _empty_repo(tmp_path)
    system._add_subject("advanced_python", "Advanced Python", "computing", ["asyncio"],
                        importance=1.0, source="test")
    system.register_mission_gap(
        mission="learn unfamiliar domain", subject_name="Unfamiliar Domain", group="research",
        proposed_subskills=["alpha"], evidence="mission gap",
    )
    system.set_active_subject("mission_unfamiliar_domain")
    system.step()
    system.state["contracts"].append({
        "contract_id": "unrelated-supported", "subject_id": "advanced_python",
        "status": "open", "created_epoch": time.time(),
        "requirement": {"kind": "lesson", "subskills": ["asyncio"]},
    })
    system.set_active_subject("mission_unfamiliar_domain")
    system._save()
    executor = ProgressiveCompetencyExecutor(
        system=system, state_path=tmp_path / "executor.json",
        result_dir=tmp_path / "results/progressive_competency",
    )
    outcome = executor.step()
    assert outcome["status"] == "executor_acquisition_required"
    assert outcome["subject_id"] == "mission_unfamiliar_domain"
    assert system.evidence_for("advanced_python") == []


def test_software_engineering_uses_executable_concept_counterexamples(tmp_path: Path):
    system = _empty_repo(tmp_path)
    system._add_subject(
        "software_engineering", "Software Engineering", "computing",
        ["architecture", "debugging", "delivery", "implementation", "maintenance",
         "modularity", "observability", "requirements", "review", "team_practice",
         "testing", "version_control"], importance=1.0, source="test",
    )
    system.set_active_subject("software_engineering")
    system.step()
    executor = ProgressiveCompetencyExecutor(
        system=system, state_path=tmp_path / "executor.json",
        result_dir=tmp_path / "results/progressive_competency",
    )
    outcome = executor.step()
    assert outcome["progressed"] is True
    result = json.loads((tmp_path / outcome["result_path"]).read_text())
    assert result["gate"]["candidate_execution_passed"] is True
    assert result["gate"]["counterexamples_rejected"] == result["gate"]["counterexamples_total"]
    assert result["gate"]["unsafe_variants_rejected"] == 6


def test_expert_project_portfolio_has_twelve_distinct_falsifiable_families():
    assert len(PROJECTS) >= 12
    for source, old, new in PROJECTS.values():
        assert _run_program(source)["returncode"] == 0
        assert _run_program(source.replace(old, new, 1))["returncode"] != 0


def test_capability_query_reports_level_and_refuses_unknown_subject(tmp_path: Path):
    system = _empty_repo(tmp_path)
    python = system.capability_query("Can you build this in Python?")
    unknown = system.capability_query("Do you understand Martian pet nutrition?")
    assert python["answer"] == "known"
    assert python["work_readiness"] == "not_ready"
    assert unknown["answer"] == "unknown_subject"
    assert unknown["action"] == "register_mission_gap_or_clarify_subject"
