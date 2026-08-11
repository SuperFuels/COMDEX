import json
from pathlib import Path

from backend.AION.system.aion_development_dashboard import collect_snapshot, render_text


def _write(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_dashboard_collects_academy_mastery_and_glyph_state(tmp_path):
    _write(tmp_path / "results/hexcore_constitutional_north_star_mastery_registry.json", {
        "subjects": {
            "python": {"name": "Python", "level": "proficient_bounded", "coverage": 1.0,
                       "work_readiness": "bounded", "missing_subskills": []},
            "biology": {"name": "Biology", "level": "unassessed", "coverage": 0.0,
                        "work_readiness": "not_ready", "missing_subskills": ["cells"]},
        },
        "maturity": {"current_stage": "apprentice", "next_stage": "general_apprentice"},
        "strategic_goal_portfolio": [],
    })
    _write(tmp_path / "backend/modules/hexcore/data/guided_foundation_academy/state.json", {
        "academy_id": "academy_test", "primary_academy_complete": False, "cycles": [{}],
        "retention_queue": [{"status": "scheduled"}],
        "modules": {
            "python_core": {"name": "Python Core", "status": "passed_bounded",
                            "prerequisites": [], "evidence": [{}]},
            "algorithms": {"name": "Algorithms", "status": "executor_required",
                           "prerequisites": ["python_core"], "evidence": []},
        },
    })
    _write(tmp_path / "results/hexcore_governed_intelligence_glyph_consolidation.json", {
        "passed": True, "gate": {"glyphs": 44, "knowledge_glyphs": 25,
                                    "skill_glyphs": 6, "curriculum_glyphs": 13,
                                    "working_memory_reduction": .9708,
                                    "all_provenance_resolves": True},
    })
    snapshot = collect_snapshot(tmp_path)
    assert snapshot["academy"]["passed"] == 1
    assert snapshot["academy"]["active"]["name"] == "Algorithms"
    assert snapshot["mastery"]["subjects_total"] == 2
    assert snapshot["glyphs"]["total"] == 44
    text = render_text(snapshot, width=100, full=True)
    assert "AION INTELLIGENCE DEVELOPMENT" in text
    assert "Programming, Systems & Security" in text
    assert "COMPLETED FOUNDATION ASSESSMENT ARCHIVE" in text
    assert "not competency levels" in text
    assert "COMPRESSED INTELLIGENCE" in text


def test_dashboard_handles_empty_workspace_without_crashing(tmp_path):
    snapshot = collect_snapshot(tmp_path)
    assert snapshot["academy"]["total"] == 0
    assert snapshot["mastery"]["subjects_total"] == 0
    assert snapshot["glyphs"]["total"] == 0
    assert "AION OPEN-MISSION LEARNING" in render_text(snapshot, width=80)


def test_dashboard_describes_completed_calibration_and_zero_control_truthfully(tmp_path):
    _write(tmp_path / "results/aion_open_mission_compounding_status.json", {
        "status": "active", "ends_at": "2026-08-15T19:26:00+00:00",
        "arms": {
            "full_aion": {"verified_successes": 4, "eligible_outcomes": 4,
                          "success_rate": 1.0, "investigation_actions": 11},
            "proposer_only": {"verified_successes": 0, "eligible_outcomes": 4,
                              "success_rate": 0.0, "investigation_actions": 8},
        },
    })
    _write(tmp_path / "results/aion_open_mission_executor_status.json", {
        "status": "cycle_complete",
        "public_change": {"status": "portfolio_limit_reached", "completed": 8, "limit": 8},
    })
    text = render_text(collect_snapshot(tmp_path), width=180)
    assert "Rolling public-world forecast: CALIBRATION COMPLETE" in text
    assert "control produced none (finite ratio not estimable)" in text


def test_dashboard_separates_registry_level_from_fresh_reconstruction(tmp_path):
    _write(tmp_path / "results/hexcore_functional_glyph_lexicon.json", {
        "status": "PROMOTED", "passed": True,
        "gate": {"nodes": 11, "edges": 13, "node_types": 8, "relation_types": 11,
                 "functional_capsules_reconstructed": 2, "functional_capsules_total": 2},
    })
    _write(tmp_path / "results/hexcore_functional_glyph_method_compiler.json", {
        "status": "PROMOTED", "passed": True,
        "gate": {"semantic_operators_compiled": 15, "source_disjoint_transfer": True,
                 "corrupted_or_unsafe_programs_rejected": 4,
                 "corrupted_or_unsafe_programs_total": 4},
    })
    _write(tmp_path / "results/hexcore_autonomous_functional_glyph_induction.json", {
        "status": "PROMOTED", "passed": True,
        "gate": {"verified_trajectories_induced": 6,
                 "induced_procedures_reconstructed": 6,
                 "cross_domain_compositions_passed": 2,
                 "cross_domain_compositions_total": 2,
                 "advanced_memory_qualified": 4, "expert_memory_qualified": 2,
                 "competency_awards": 0},
    })
    _write(tmp_path / "results/hexcore_recursive_verifier_atom_invention.json", {
        "status": "PROMOTED", "passed": True,
        "gate": {"source_disjoint_execution": 3, "artifact_families": 3,
                 "counterexamples_rejected": 6, "counterexamples_total": 6,
                 "ambient_authority_expansions": 0},
    })
    _write(tmp_path / "results/hexcore_open_competency_reconstruction_mission.json", {
        "status": "REJECTED_OR_INCOMPLETE", "passed": False,
        "gate": {"artifacts_passed": 5, "reconstruction_explanation_application_artifacts": 6,
                 "claimed_advanced_or_expert_subjects_tested": 5,
                 "malicious_candidates_rejected": 4, "malicious_candidates_total": 4},
        "final_evaluation": {"artifacts": {
            "english": {"passed": True}, "software_algorithm_application": {"passed": False}}},
    })
    text = render_text(collect_snapshot(tmp_path), width=150, full=True)
    assert "OPEN COMPETENCY RECONSTRUCTION" in text
    assert "Functional Glyph Lexicon: PROMOTED" in text
    assert "Functional method compiler: PROMOTED" in text
    assert "Autonomous functional-memory induction: PROMOTED" in text
    assert "Advanced/Expert 4/2" in text
    assert "Artifacts 5/6" in text
    assert "Non-promotion is authoritative" in text


def test_dashboard_reports_composed_stored_physical_skill(tmp_path):
    _write(tmp_path / "results/hexcore_rgb_contact_occlusion_skill_composition.json", {
        "status": "PROMOTED", "passed": True,
        "gate": {"sealed_success": 4, "sealed_worlds": 4, "cold_success": 0,
                 "causal_contact_discovered": True, "occlusion_recovery": True,
                 "parent_skill_reconstructed": True, "unsafe_worlds": 0},
        "stored_skill_capsule": {"reconstructed": True},
        "restart": {"champion_retained": True},
    })
    text = render_text(collect_snapshot(tmp_path), width=150, full=True)
    assert "Composed RGB contact skill: PROMOTED" in text
    assert "Stored executable skill: True" in text
    assert "Occlusion recovery: True" in text


def test_dashboard_reports_articulated_sequence_learning(tmp_path):
    _write(tmp_path / "results/hexcore_rgb_articulated_sequence_skill.json", {
        "status": "PROMOTED", "passed": True,
        "gate": {"sealed_success": 4, "sealed_worlds": 4, "cold_success": 0,
                 "sequential_targets_per_world": 3, "articulated_joints": 2,
                 "visual_model_adaptation": True, "occlusion_recovery": True,
                 "unsafe_worlds": 0},
        "stored_skill_capsule": {"reconstructed": True},
    })
    text = render_text(collect_snapshot(tmp_path), width=150, full=True)
    assert "Articulated RGB sequence skill: PROMOTED" in text
    assert "Targets/world: 3" in text
    assert "Learned topology/model adaptation: True" in text


def test_dashboard_separates_cloud_package_readiness_from_execution(tmp_path):
    _write(tmp_path / "results/hexcore_simulator_disjoint_embodied_scaleup.json", {
        "status": "READY_FOR_NVIDIA_EXECUTION", "package_ready": True,
        "external_execution_complete": False, "promoted": False,
        "contract_sha256": "a" * 64, "skill_ancestry_count": 3,
        "experimental_arms": ["aion_retained", "aion_cold", "aion_cosmos", "gr00t_teacher"],
        "tamper_rejected": True, "unsigned_rejected": True,
        "blockers": ["NVIDIA Linux GPU authority"],
    })
    text = render_text(collect_snapshot(tmp_path), width=170, full=True)
    assert "Isaac Lab scale-up: READY_FOR_NVIDIA_EXECUTION" in text
    assert "NVIDIA execution complete: False" in text
    assert "Promoted: False" in text
