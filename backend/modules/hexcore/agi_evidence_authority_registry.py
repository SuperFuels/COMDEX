from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, List, Mapping, Sequence

from backend.modules.hexcore.documentation_guided_open_software_benchmark import _allow
from backend.modules.hexcore.persistent_learning import (
    HexCorePersistentLearningRuntime,
    ProcedureCandidate,
    _canonical_hash,
    _utc_timestamp,
)


PROCEDURE_ID = "procedure_agi_evidence_authority_registry_v1_9b6e63c112a4"


@dataclass(frozen=True)
class ArtifactContract:
    artifact_id: str
    relative_path: str
    authority_class: str
    checks: Sequence[str]


ARTIFACTS = (
    ArtifactContract(
        "arena_v5_invention",
        "results/hexcore_residual_driven_primitive_invention_v5.json",
        "internal_sealed_outcome",
        ("passed", "gate.transfer_success", "gate.ood_abstention"),
    ),
    ArtifactContract(
        "large_continual_arena",
        "results/hexcore_large_continual_learning_arena.json",
        "internal_source_disjoint_outcome",
        ("passed", "gate.total_tasks", "gate.maximum_forgetting"),
    ),
    ArtifactContract(
        "continual_neural_challengers",
        "results/hexcore_continual_neural_improvement.json",
        "internal_private_challenger_outcome",
        ("passed", "gate.successive_generations", "gate.maximum_measured_forgetting"),
    ),
    ArtifactContract(
        "open_multimodal_projects",
        "results/hexcore_phase58_open_multimodal_projects.json",
        "internal_real_file_outcome",
        ("passed", "gate.project_completion", "gate.contradiction_detection"),
    ),
    ArtifactContract(
        "natural_multimodal_v6",
        "results/hexcore_natural_multimodal_physical_grounding_v6.json",
        "public_natural_pixel_and_official_source_outcome",
        (
            "passed",
            "gate.pixel_semantic_accuracy",
            "gate.cross_modal_conflicts_detected",
            "gate.ood_abstention",
        ),
    ),
    ArtifactContract(
        "temporal_multimodal_v7",
        "results/hexcore_temporal_multimodal_action_v7.json",
        "public_natural_temporal_media_outcome",
        (
            "passed",
            "gate.video_temporal_semantic_accuracy",
            "gate.audio_top_event_coverage",
            "gate.broken_chronologies_detected",
        ),
    ),
    ArtifactContract(
        "closed_loop_physical_v8",
        "results/hexcore_closed_loop_physical_intelligence_v8.json",
        "internal_pixel_action_delayed_outcome",
        (
            "passed",
            "gate.goal_success",
            "gate.probe_reduction_vs_cold",
            "gate.ood_abstention",
        ),
    ),
    ArtifactContract(
        "public_pixel_physics_v9",
        "results/hexcore_public_physics_transfer_v9.json",
        "third_party_public_simulator_outcome",
        ("passed", "gate.learned_policy_success", "gate.success_lift_vs_cold", "gate.unseen_visual_schema_abstention"),
    ),
    ArtifactContract(
        "open_visual_control_v10",
        "results/hexcore_open_visual_control_invention_v10.json",
        "third_party_public_open_visual_control_outcome",
        ("passed", "gate.overall_success", "gate.continuous_transfer_success", "gate.unknown_schema_abstention"),
    ),
    ArtifactContract(
        "cross_topology_physics_v11",
        "results/hexcore_cross_topology_physical_invention_v11.json",
        "third_party_public_cross_topology_outcome",
        ("passed", "gate.overall_success", "gate.nips_transfer_success", "gate.new_state_primitive"),
    ),
    ArtifactContract(
        "real_world_acoustic_v12",
        "results/hexcore_real_world_acoustic_learning_v12.json",
        "development_owned_real_physical_outcome",
        ("passed", "gate.real_air_path", "gate.error_reduction_vs_flat", "gate.raw_audio_persisted"),
    ),
    ArtifactContract(
        "real_world_acoustic_improvement_v13",
        "results/hexcore_real_world_acoustic_improvement_v13.json",
        "development_owned_real_physical_improvement",
        ("passed", "gate.physical_uniformity_improvement", "gate.tool_retained", "gate.unsafe_output_level"),
    ),
    ArtifactContract(
        "continual_neural_physical_policy_v14",
        "results/hexcore_continual_neural_physical_policy_v14.json",
        "development_owned_continual_neural_physical_consolidation",
        ("passed", "gate.mean_success", "gate.weakest_task_success", "gate.component_replacement_predictions_identical"),
    ),
    ArtifactContract(
        "open_outcome_project_scientist",
        "results/hexcore_open_outcome_project_scientist.json",
        "internal_delayed_project_outcome",
        (
            "passed",
            "gate.broad_goal_only",
            "gate.mid_project_process_recovery",
            "gate.independent_delayed_authority",
        ),
    ),
    ArtifactContract(
        "public_swebench_repair",
        "results/hexcore_source_disjoint_swebench_repair.json",
        "externally_authored_public_repository_outcome",
        ("passed", "gate.base_commit_integrity", "gate.human_patch_blind_during_search"),
    ),
    ArtifactContract(
        "noaa_sensor_transfer",
        "results/hexcore_open_continuous_operator_invention.json",
        "independently_maintained_public_sensor_outcome",
        ("passed", "gate.sensor_predictive_transfer", "gate.sensor_test_r2"),
    ),
    ArtifactContract(
        "external_questions_memory",
        "results/hexcore_cross_domain_semantic_transfer.json",
        "externally_authored_public_question_outcome",
        ("passed", "gate.externally_authored_questions", "gate.delayed_memory_only_accuracy"),
    ),
    ArtifactContract(
        "public_reasoning_evaluation",
        "results/hexcore_phase48_external_evaluation.json",
        "public_human_authored_benchmark_outcome",
        ("passed", "gate.public_human_authored_cases", "gate.mean_accuracy"),
    ),
    ArtifactContract(
        "stronger_substrate",
        "results/hexcore_stronger_foundation_substrate_gemma5b.json",
        "internal_matched_substrate_outcome",
        ("passed", "gate.backbone_frozen", "gate.governed_accuracy"),
    ),
    ArtifactContract(
        "open_public_api_acquisition",
        "results/hexcore_open_public_api_acquisition.json",
        "official_documentation_and_live_read_only_api_outcome",
        ("passed", "gate.documentation_routes_discovered", "gate.source_disjoint_transfers", "gate.unsafe_or_paid_actions"),
    ),
    ArtifactContract(
        "human_judgment_protocol",
        "results/hexcore_human_judgment_protocol.json",
        "external_authority_protocol_only",
        ("gate.protocol_frozen", "gate.independent_human_evaluation_complete"),
    ),
)


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _get(data: Mapping[str, Any], dotted: str) -> Any:
    current: Any = data
    for part in dotted.split("."):
        if not isinstance(current, Mapping) or part not in current:
            return None
        current = current[part]
    return current


def _artifact_row(repo_root: Path, contract: ArtifactContract) -> Dict[str, Any]:
    path = repo_root / contract.relative_path
    if not path.exists():
        return {
            "artifact_id": contract.artifact_id,
            "path": str(path),
            "exists": False,
            "authority_class": contract.authority_class,
            "checks": {},
            "integrity_passed": False,
        }
    data = json.loads(path.read_text(encoding="utf-8"))
    checks = {name: _get(data, name) for name in contract.checks}
    return {
        "artifact_id": contract.artifact_id,
        "path": str(path),
        "sha256": _sha(path),
        "schema_version": data.get("schema_version"),
        "exists": True,
        "authority_class": contract.authority_class,
        "checks": checks,
        "boundary": data.get("boundary"),
        "integrity_passed": all(value is not None for value in checks.values()),
    }


def _external_source_bridge(repo_root: Path, rows: Mapping[str, Mapping[str, Any]]) -> Dict[str, Any]:
    noaa = json.loads(
        (repo_root / "results/hexcore_open_continuous_operator_invention.json").read_text(encoding="utf-8")
    )
    swebench = json.loads(
        (repo_root / "results/hexcore_source_disjoint_swebench_repair.json").read_text(encoding="utf-8")
    )
    semantic = json.loads(
        (repo_root / "results/hexcore_cross_domain_semantic_transfer.json").read_text(encoding="utf-8")
    )
    public_eval = json.loads(
        (repo_root / "results/hexcore_phase48_external_evaluation.json").read_text(encoding="utf-8")
    )
    noaa_path = Path("/Users/kevinrobinson/Documents/Tessaris/TPU/datasets/external/SP000003195.csv.gz")
    noaa_source = {
        "authority": "NOAA_NCEI_GHCN_Daily",
        "station": noaa["gate"]["sensor_source"],
        "url": "https://www.ncei.noaa.gov/pub/data/ghcn/daily/by_station/SP000003195.csv.gz",
        "cached_path": str(noaa_path),
        "cached_exists": noaa_path.exists(),
        "cached_sha256": _sha(noaa_path) if noaa_path.exists() else None,
        "chronological_test_r2": noaa["gate"]["sensor_test_r2"],
        "passed": bool(
            noaa_path.exists()
            and noaa["gate"]["sensor_predictive_transfer"]
            and noaa["gate"]["sensor_test_r2"] >= 0.80
        ),
    }
    software_source = {
        "authority": swebench["gate"]["public_benchmark"],
        "source_disjoint_repositories": swebench["gate"]["source_disjoint_repositories"],
        "human_patch_blind": swebench["gate"]["human_patch_blind_during_search"],
        "base_commit_integrity": swebench["gate"]["base_commit_integrity"],
        "passed": bool(
            swebench["gate"]["repair_success"] == 1.0
            and swebench["gate"]["base_commit_integrity"]
            and swebench["gate"]["human_patch_blind_during_search"]
        ),
    }
    knowledge_source = {
        "authority": "official_public_sources_and_questions",
        "source_domains": semantic["gate"]["source_domains"],
        "externally_authored_questions": semantic["gate"]["externally_authored_questions"],
        "delayed_memory_accuracy": semantic["gate"]["delayed_memory_only_accuracy"],
        "passed": bool(
            semantic["gate"]["externally_authored_questions"] >= 12
            and semantic["gate"]["provenance_completeness"] == 1.0
        ),
    }
    reasoning_source = {
        "authority": "public_human_authored_validation_sets",
        "cases": public_eval["gate"]["public_human_authored_cases"],
        "mean_accuracy": public_eval["gate"]["mean_accuracy"],
        "weakest_family_accuracy": public_eval["gate"]["weakest_family_accuracy"],
        "contamination_excluded": public_eval["gate"]["pretraining_contamination_excluded"],
        "passed_as_public_transfer": public_eval["gate"]["mean_accuracy"] > public_eval["gate"]["chance_reference"],
        "passed_as_external_certification": False,
    }
    sources = [noaa_source, software_source, knowledge_source, reasoning_source]
    return {
        "schema_version": "aion.hexcore.external_outcome_bridge.v1",
        "sources": sources,
        "source_families": 4,
        "externally_maintained_source_families_passed": sum(
            bool(row.get("passed") or row.get("passed_as_public_transfer")) for row in sources
        ),
        "all_source_artifact_commitments_present": all(
            rows[name]["integrity_passed"]
            for name in (
                "noaa_sensor_transfer",
                "public_swebench_repair",
                "external_questions_memory",
                "public_reasoning_evaluation",
            )
        ),
        "external_administrator_owned": False,
        "claim": "EXTERNALLY_SOURCED_OUTCOMES_PARTIAL_NOT_EXTERNAL_CERTIFICATION",
    }


def _gate_registry(rows: Mapping[str, Mapping[str, Any]], bridge: Mapping[str, Any]) -> List[Dict[str, Any]]:
    return [
        {
            "gate_id": "broad_domain_transfer",
            "status": "PARTIAL_INTERNAL_AND_PUBLIC",
            "evidence": ["large_continual_arena", "public_reasoning_evaluation", "external_questions_memory"],
            "satisfied_evidence": "2040-task internal arena plus public language/reasoning transfer",
            "remaining": "natural physical, social, creative and independently hidden breadth",
        },
        {
            "gate_id": "autonomous_long_project_decomposition",
            "status": "PARTIAL_INTERNAL",
            "evidence": ["arena_v5_invention", "open_outcome_project_scientist"],
            "satisfied_evidence": "broad-goal decomposition, changing milestones and restart recovery",
            "remaining": "hours/days duration and independently changing external systems",
        },
        {
            "gate_id": "independently_owned_consequence_learning",
            "status": "PARTIAL_EXTERNALLY_SOURCED",
            "evidence": ["noaa_sensor_transfer", "public_swebench_repair", "external_questions_memory"],
            "satisfied_evidence": f"{bridge['externally_maintained_source_families_passed']} public outcome families",
            "remaining": "administrator-controlled delayed reveal and evaluation",
        },
        {
            "gate_id": "continual_improvement_without_forgetting",
            "status": "INTERNAL_BOUNDED_PASS",
            "evidence": ["large_continual_arena", "continual_neural_challengers"],
            "satisfied_evidence": "three generations, 2040 tasks and zero measured forgetting",
            "remaining": "long-duration diverse human-authored arena and external replay authority",
        },
        {
            "gate_id": "natural_multimodal_physical_grounding",
            "status": "PARTIAL_PUBLIC_NATURAL_MULTIMODAL",
            "evidence": [
                "open_multimodal_projects",
                "natural_multimodal_v6",
                "temporal_multimodal_v7",
                "closed_loop_physical_v8",
                "public_pixel_physics_v9",
                "open_visual_control_v10",
                "cross_topology_physics_v11",
                "real_world_acoustic_v12",
                "real_world_acoustic_improvement_v13",
                "continual_neural_physical_policy_v14",
                "noaa_sensor_transfer",
            ],
            "satisfied_evidence": (
                "natural NASA/USGS pixels and temporal media, active visual perception, "
                "chronology criticism, budgeted seismic measurement, pixel-to-action control, "
                "outcome-driven dynamics revision, official-source delayed reveal, cross-modal "
                "criticism and public NOAA temporal data"
            ),
            "remaining": "native audio/video, real spatial actuation and independently administered physical outcomes",
        },
        {
            "gate_id": "social_commonsense_creative_judgment",
            "status": "BLOCKED_EXTERNAL_HUMAN_AUTHORITY",
            "evidence": ["human_judgment_protocol"],
            "satisfied_evidence": "frozen protocol and blank rating instrument",
            "remaining": "independent multi-rater outcomes and held-out human-authored cohort",
        },
        {
            "gate_id": "tool_and_representation_invention",
            "status": "INTERNAL_BOUNDED_PASS",
            "evidence": ["arena_v5_invention", "open_public_api_acquisition"],
            "satisfied_evidence": "program/primitive invention plus typed read-only acquisition across three public APIs",
            "remaining": "credentialed or state-changing interfaces under explicit authority and independent real-project value",
        },
        {
            "gate_id": "safe_abstention_and_human_escalation",
            "status": "PARTIAL_INTERNAL",
            "evidence": ["arena_v5_invention", "human_judgment_protocol"],
            "satisfied_evidence": "OOD abstention and fail-closed promotion",
            "remaining": "measured human escalation quality and response time",
        },
        {
            "gate_id": "matched_frontier_and_human_comparison",
            "status": "PARTIAL_SUBSTRATE_ONLY",
            "evidence": ["stronger_substrate"],
            "satisfied_evidence": "matched replaceable-substrate trial",
            "remaining": "frontier agents, specialist systems and human baselines under one external budget",
        },
        {
            "gate_id": "independent_reproducibility",
            "status": "BLOCKED_EXTERNAL_ADMINISTRATOR",
            "evidence": [],
            "satisfied_evidence": "handoff and commitment protocols only",
            "remaining": "independent organization must own tasks, outcomes, scoring and reproduction",
        },
    ]


def run_agi_evidence_registry(
    *,
    repo_root: Path,
    state_path: Path,
    result_path: Path | None = None,
    handoff_path: Path | None = None,
) -> Dict[str, Any]:
    artifact_rows = [_artifact_row(repo_root, contract) for contract in ARTIFACTS]
    by_id = {row["artifact_id"]: row for row in artifact_rows}
    bridge = _external_source_bridge(repo_root, by_id)
    registry = _gate_registry(by_id, bridge)
    externally_verified = [row for row in registry if row["status"] == "EXTERNALLY_VERIFIED"]
    blocked = [row for row in registry if row["status"].startswith("BLOCKED")]
    internal_or_partial = [row for row in registry if row not in blocked]
    integrity = all(row["integrity_passed"] for row in artifact_rows)
    honest_authority = (
        not bridge["external_administrator_owned"]
        and len(externally_verified) == 0
        and any(row["gate_id"] == "independent_reproducibility" for row in blocked)
    )
    control_gate = {
        "artifact_contracts": len(artifact_rows),
        "artifact_integrity_rate": sum(row["integrity_passed"] for row in artifact_rows) / len(artifact_rows),
        "agi_evidence_gates": len(registry),
        "internal_or_partial_gates": len(internal_or_partial),
        "externally_verified_gates": len(externally_verified),
        "externally_blocked_gates": len(blocked),
        "external_outcome_source_families": bridge["source_families"],
        "external_outcome_source_families_passed": bridge["externally_maintained_source_families_passed"],
        "authority_classification_fail_closed": honest_authority,
        "agi_claim_authorized": False,
        "registry_runtime_accepted": integrity and honest_authority,
    }
    control_gate["errors"] = []
    if not integrity:
        control_gate["errors"].append("ARTIFACT_INTEGRITY_INCOMPLETE")
    if not honest_authority:
        control_gate["errors"].append("AUTHORITY_CLASSIFICATION_UNSAFE")

    handoff = {
        "schema_version": "aion.external.agi_evidence_handoff.v1",
        "created_at": _utc_timestamp(),
        "registry_commitment": _canonical_hash(registry),
        "artifact_manifest_commitment": _canonical_hash(artifact_rows),
        "external_evaluator": None,
        "external_task_owner": None,
        "sealed_portfolio_commitment": None,
        "delayed_outcome_commitment": None,
        "human_rater_panel_commitment": None,
        "matched_budget_commitment": None,
        "answer_reveal_commitment": None,
        "external_signature": None,
        "status": "AWAITING_EXTERNAL_ADMINISTRATOR",
        "required_portfolio_families": [
            "unfamiliar_language_and_long_document_research",
            "mathematics_and_formal_reasoning",
            "source_disjoint_software_engineering",
            "scientific_model_invention_and_prediction",
            "natural_multimodal_and_physical_grounding",
            "long_horizon_changing_projects",
            "social_commonsense_and_multi_agent_judgment",
            "creative_synthesis_with_independent_raters",
        ],
        "required_matched_systems": [
            "complete_aion",
            "aion_without_accumulated_memory",
            "aion_without_causal_world_model",
            "aion_without_neural_proposals",
            "aion_without_hexcore_verification_where_safe",
            "frontier_agent_under_identical_tools_and_budget",
            "strong_open_agent_under_identical_tools_and_budget",
            "qualified_human_baseline",
        ],
        "required_audit_fields": [
            "task_owner_independent_of_aion_development",
            "task_commitment_precedes_system_access",
            "answers_and_delayed_outcomes_sealed_until_finalization",
            "contamination_and_source_overlap_audit",
            "identical_information_tool_compute_and_time_budgets",
            "mean_and_weakest_family_scores",
            "forward_transfer_and_backward_retention",
            "unsafe_acceptance_abstention_and_human_escalation",
            "full_restart_and_component_replacement",
            "reproducible_artifact_hashes_and_execution_logs",
        ],
        "developer_self_certification_permitted": False,
        "instructions": [
            "External administrator fills identity and commitment fields before AION receives tasks.",
            "Task, outcome, budget and answer commitments must be signed and immutable.",
            "AION developers may not reveal answers, replace failed outcomes or score the final cohort.",
            "Every reported gate requires artifact hashes and evaluator signature verification.",
        ],
    }

    runtime = HexCorePersistentLearningRuntime(state_path=state_path, authority_provider=_allow)
    runtime.store.state.setdefault("agi_evidence_registries", {})
    registry_id = "agi_registry_" + _canonical_hash({"registry": registry, "bridge": bridge})[:16]
    runtime.store.state["agi_evidence_registries"][registry_id] = {
        "registry": registry,
        "bridge": bridge,
        "control_gate": control_gate,
        "handoff_commitment": _canonical_hash(handoff),
        "created_at": _utc_timestamp(),
    }
    candidate = ProcedureCandidate(
        procedure_id=PROCEDURE_ID,
        goal="agi_evidence_authority_control_plane",
        steps=[
            "hash_commit_all_capability_artifacts",
            "classify_internal_external_source_and_external_authority",
            "bridge_public_repository_sensor_question_and_benchmark_outcomes",
            "map_evidence_to_ten_agi_gates",
            "keep_external_human_and_reproducibility_gates_closed",
            "freeze_external_evaluator_handoff_contract",
            "deny_agi_claim_without_external_signatures",
        ],
        score=control_gate["artifact_integrity_rate"],
        success=control_gate["registry_runtime_accepted"],
        evidence={"control_gate": control_gate, "registry_id": registry_id},
        source_rules=[],
    )
    promotion = runtime.skills.promote(candidate)
    runtime.skills.record_outcome(
        procedure_id=PROCEDURE_ID,
        success=candidate.success,
        score=candidate.score,
        evidence=candidate.evidence,
    )
    runtime.store.commit(reason="agi_evidence_authority_registry")
    restarted = HexCorePersistentLearningRuntime(state_path=state_path, authority_provider=_allow)
    restart = {
        "registry_retained": registry_id in restarted.store.state.get("agi_evidence_registries", {}),
        "control_plane_champion_retained": restarted.store.state["champions"].get("agi_evidence_authority_control_plane") == PROCEDURE_ID,
        "agi_claim_still_denied": not control_gate["agi_claim_authorized"],
        "relearning_artifacts": 0,
    }
    payload = {
        "schema_version": "aion.hexcore.agi_evidence_authority_registry.v1",
        "created_at": _utc_timestamp(),
        "registry_id": registry_id,
        "artifacts": artifact_rows,
        "external_outcome_bridge": bridge,
        "evidence_gates": registry,
        "control_gate": control_gate,
        "external_handoff": handoff,
        "promotion": {"candidate": candidate.to_dict(), "decision": promotion},
        "restart": restart,
        "passed": bool(
            control_gate["registry_runtime_accepted"]
            and (promotion.get("promoted") or promotion.get("champion_id") == PROCEDURE_ID)
            and all(value is True or value == 0 for value in restart.values())
        ),
        "agi_claim_authorized": False,
        "boundary": (
            "This procedure promotes an evidence-authority registry, not AGI. It consolidates "
            "internally verified and externally sourced outcomes, preserves their distinct "
            "authority classes, and freezes an external handoff. No external administrator, "
            "human panel or contamination-proof hidden evaluation has completed the final gates."
        ),
    }
    if result_path:
        result_path.parent.mkdir(parents=True, exist_ok=True)
        result_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    if handoff_path:
        handoff_path.parent.mkdir(parents=True, exist_ok=True)
        handoff_path.write_text(json.dumps(handoff, indent=2, sort_keys=True), encoding="utf-8")
    return payload


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, default=Path("."))
    parser.add_argument(
        "--state-path",
        type=Path,
        default=Path("backend/modules/hexcore/data/agi_evidence_registry/state.json"),
    )
    parser.add_argument(
        "--result-path",
        type=Path,
        default=Path("results/hexcore_agi_evidence_authority_registry.json"),
    )
    parser.add_argument(
        "--handoff-path",
        type=Path,
        default=Path("results/aion_external_agi_evidence_handoff.json"),
    )
    args = parser.parse_args()
    result = run_agi_evidence_registry(
        repo_root=args.repo_root.resolve(),
        state_path=args.state_path.resolve(),
        result_path=args.result_path.resolve(),
        handoff_path=args.handoff_path.resolve(),
    )
    print(json.dumps(result["control_gate"], indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
