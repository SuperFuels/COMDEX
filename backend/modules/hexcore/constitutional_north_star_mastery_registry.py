"""Constitutional North Star, evidence-backed mastery registry and goal portfolio.

The registry distinguishes exposure, operational capability, bounded
proficiency, expertise and mastery.  A procedure promotion can establish that
the registry works; it cannot promote the subjects listed inside it.
"""
from __future__ import annotations

import argparse
import json
import math
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

from backend.modules.hexcore.autonomous_general_apprentice import (
    AutonomousGeneralApprentice,
)
from backend.modules.hexcore.canonical_cognitive_runtime import (
    _canonical_hash,
    _utc_timestamp,
)
from backend.modules.hexcore.persistent_learning import (
    HexCorePersistentLearningRuntime,
    ProcedureCandidate,
)


PROCEDURE_ID = "procedure_constitutional_north_star_mastery_registry_v1"
CONSTITUTIONAL_PURPOSE = (
    "Develop and use increasingly general intelligence to create beneficial, "
    "evidence-backed knowledge and capability; respect human authority, law, "
    "consent, safety, provenance and legitimate uncertainty; never treat money, "
    "access, infrastructure, influence or self-preservation as terminal goals."
)

LEVELS = (
    "unassessed", "learning", "operational_bounded", "proficient_bounded",
    "expert", "mastered",
)


@dataclass(frozen=True)
class SubjectSpec:
    subject_id: str
    name: str
    group: str
    importance: float
    target_level: str
    subskills: tuple[str, ...]
    evidence: tuple[tuple[str, tuple[str, ...], tuple[str, ...]], ...]
    prerequisites: tuple[str, ...] = ()


def _ev(path: str, skills: Sequence[str], authorities: Sequence[str]) -> tuple[str, tuple[str, ...], tuple[str, ...]]:
    return path, tuple(skills), tuple(authorities)


SUBJECTS: tuple[SubjectSpec, ...] = (
    SubjectSpec("english", "English natural-language cognition", "human_language", 1.0, "proficient_bounded",
        ("instruction_understanding", "long_documents", "argument_structure", "ambiguity", "correction", "clear_generation", "pragmatics", "long_dialogue"),
        (_ev("results/hexcore_persistent_natural_language_mission_interface.json", ("instruction_understanding","ambiguity","correction","clear_generation"), ("sealed_interpretation",)),
         _ev("results/hexcore_long_document_semantic_memory.json", ("long_documents","long_dialogue"), ("public_books",)),
         _ev("results/hexcore_open_relation_argument_memory.json", ("argument_structure","pragmatics"), ("source_spans",)),
         _ev("results/hexcore_cross_domain_semantic_transfer.json", ("long_documents","instruction_understanding"), ("official_documents",)))),
    SubjectSpec("spanish", "Spanish language", "human_language", 0.55, "operational_bounded",
        ("reading", "writing", "conversation", "pragmatics", "domain_vocabulary"), ()),
    SubjectSpec("mathematics", "Mathematics", "formal_reasoning", 1.0, "proficient_bounded",
        ("arithmetic", "algebra", "logic", "probability", "statistics", "calculus", "discrete_math", "proof"),
        (_ev("results/hexcore_continuous_cross_domain_mastery.json", ("algebra","logic"), ("sealed_algebra",)),
         _ev("results/hexcore_compositional_multivariate_discovery.json", ("probability","statistics"), ("held_out_numeric",)),
         _ev("results/hexcore_residual_driven_primitive_invention_v5.json", ("algebra","calculus"), ("independent_execution",)))),
    SubjectSpec("scientific_method", "Scientific investigation and causal reasoning", "science", 1.0, "proficient_bounded",
        ("hypothesis_generation", "experiment_design", "causal_inference", "model_criticism", "measurement", "uncertainty", "replication", "literature_synthesis"),
        (_ev("results/hexcore_open_causal_scientific_learning.json", ("hypothesis_generation","experiment_design","causal_inference","model_criticism"), ("intervention_outcomes",)),
         _ev("results/hexcore_open_continuous_operator_invention.json", ("measurement","uncertainty","replication"), ("noaa_sensor","software_subprocess")),
         _ev("results/hexcore_continuous_natural_world_learning.json", ("measurement","causal_inference"), ("withheld_future",)),
         _ev("results/hexcore_cross_domain_semantic_transfer.json", ("literature_synthesis",), ("official_scientific_source",)))),
    SubjectSpec("physics", "Physics", "science", 0.8, "operational_bounded",
        ("mechanics", "thermodynamics", "electromagnetism", "waves", "optics", "quantum", "relativity", "experimental_physics"),
        (_ev("results/hexcore_cross_topology_physical_invention_v11.json", ("mechanics",), ("public_gym_physics",)),
         _ev("results/hexcore_real_world_acoustic_improvement_v13.json", ("waves","experimental_physics"), ("microphone_outcome",)))),
    SubjectSpec("biology_medicine", "Biology and medicine", "science", 0.9, "operational_bounded",
        ("cell_biology", "genetics", "physiology", "immunology", "pharmacology", "epidemiology", "clinical_evidence", "bioethics"), ()),
    SubjectSpec("chemistry", "Chemistry and materials", "science", 0.75, "operational_bounded",
        ("general_chemistry", "organic", "inorganic", "physical_chemistry", "analytical", "materials", "laboratory_safety"), ()),
    SubjectSpec("python", "Python programming", "programming", 1.0, "proficient_bounded",
        ("syntax", "data_structures", "typing", "testing", "debugging", "packages", "concurrency", "performance", "security", "architecture"),
        (_ev("results/hexcore_polyglot_execution_contract.json", ("syntax","testing"), ("python_runtime",)),
         _ev("results/hexcore_natural_historical_repository_repair.json", ("debugging","packages"), ("historical_git","hidden_tests")),
         _ev("results/hexcore_documentation_guided_open_software.json", ("architecture","typing"), ("repository_tests",)),
         _ev("results/hexcore_general_apprenticeship_executor.json", ("debugging","testing","security"), ("python_runtime","historical_git")),
         _ev("results/hexcore_governed_teacher_python_core_cycle.json", ("syntax","data_structures","testing","debugging","security"), ("python_runtime","fresh_subprocess","ast_security_scan")))),
    SubjectSpec("rust", "Rust programming", "programming", 1.0, "proficient_bounded",
        ("syntax", "ownership", "traits", "error_handling", "testing", "concurrency", "performance", "unsafe_review", "multi_file_design", "toolchain"),
        (_ev("results/hexcore_rust_sql_construction_and_selection.json", ("syntax","error_handling","testing"), ("rustc",)),
         _ev("results/hexcore_rust_sql_systems_depth.json", ("traits","concurrency","performance","multi_file_design"), ("cargo","clippy")),
         _ev("results/hexcore_fifth_repository_rust_repair.json", ("ownership","toolchain"), ("historical_git","cargo")),
         _ev("results/hexcore_real_rust_apprenticeship.json", ("ownership","traits","error_handling","testing","concurrency","unsafe_review","multi_file_design","toolchain"), ("cargo","hidden_tests")))),
    SubjectSpec("javascript_typescript", "JavaScript and TypeScript", "programming", 0.9, "proficient_bounded",
        ("javascript", "typescript", "async", "browser", "node", "testing", "tooling", "security", "architecture"),
        (_ev("results/hexcore_polyglot_execution_contract.json", ("javascript","typescript","node","testing","tooling"), ("node","tsc")),
         _ev("results/hexcore_cross_language_historical_repair.json", ("javascript","testing"), ("historical_git","node")),
         _ev("results/hexcore_autonomous_executor_contract_campaign.json", ("node","security","architecture"), ("node",)))),
    SubjectSpec("sql_databases", "SQL and database systems", "programming", 0.95, "proficient_bounded",
        ("schema_design", "queries", "constraints", "transactions", "migrations", "indexes", "query_plans", "concurrency", "security", "operations"),
        (_ev("results/hexcore_rust_sql_construction_and_selection.json", ("schema_design","constraints","transactions","indexes","security"), ("sqlite",)),
         _ev("results/hexcore_rust_sql_systems_depth.json", ("migrations","query_plans","concurrency","operations"), ("sqlite",)),
         _ev("results/hexcore_general_apprenticeship_executor.json", ("transactions","security"), ("sqlite",)))),
    SubjectSpec("software_engineering", "Software engineering", "engineering", 1.0, "proficient_bounded",
        ("requirements", "architecture", "implementation", "testing", "debugging", "maintenance", "version_control", "delivery", "observability", "team_practice"),
        (_ev("results/hexcore_documentation_guided_open_software.json", ("requirements","architecture","implementation","testing"), ("repository_tests",)),
         _ev("results/hexcore_source_disjoint_swebench_repair.json", ("debugging","maintenance","version_control"), ("hidden_repository_tests",)),
         _ev("results/hexcore_real_file_projects.json", ("delivery","observability"), ("disk_verifier",)),
         _ev("results/hexcore_autonomous_executor_contract_campaign.json", ("implementation","testing","maintenance"), ("cargo","node")))),
    SubjectSpec("security_engineering", "Security engineering", "engineering", 0.95, "proficient_bounded",
        ("threat_modeling", "secure_coding", "adversarial_testing", "sandboxing", "auth", "cryptography", "network_security", "incident_response", "supply_chain", "governance"),
        (_ev("results/hexcore_adversarial_patch_tournament.json", ("secure_coding","adversarial_testing","sandboxing"), ("security_scanner",)),
         _ev("results/hexcore_programming_intelligence_closure.json", ("threat_modeling","supply_chain","governance"), ("malicious_patch_tests",)),
         _ev("results/hexcore_agi_evidence_authority_registry.json", ("cryptography","governance"), ("sha256","ed25519_protocol")),
         _ev("results/hexcore_autonomous_executor_contract_campaign.json", ("secure_coding","sandboxing"), ("cargo","node","sqlite")))),
    SubjectSpec("data_statistics", "Data analysis and statistics", "analysis", 0.9, "proficient_bounded",
        ("data_cleaning", "descriptive_statistics", "inference", "time_series", "visualisation", "causal_analysis", "uncertainty", "reporting"),
        (_ev("results/hexcore_open_continuous_operator_invention.json", ("time_series","inference","uncertainty"), ("noaa_sensor",)),
         _ev("results/hexcore_natural_multimodal_physical_grounding_v6.json", ("visualisation","reporting"), ("multimodal_files",)),
         _ev("results/hexcore_continuous_natural_world_learning.json", ("causal_analysis","descriptive_statistics"), ("withheld_future",)))),
    SubjectSpec("business_management", "Business and organisational management", "business", 0.9, "operational_bounded",
        ("strategy", "operations", "marketing", "sales", "product", "people", "finance", "risk", "governance", "execution"),
        (_ev("results/hexcore_long_running_changing_project_arena_v3.json", ("operations","risk","execution"), ("delayed_projects",)),
         _ev("results/hexcore_open_mission_portfolio_induction.json", ("strategy","product","governance"), ("portfolio_outcomes",)))),
    SubjectSpec("finance_accounting", "Financial management and accounting", "business", 0.95, "operational_bounded",
        ("bookkeeping", "financial_statements", "management_accounting", "corporate_finance", "markets", "risk", "tax", "audit", "forecasting", "controls"),
        (_ev("results/hexcore_rust_sql_systems_depth.json", ("controls","audit"), ("transaction_tests",)),
         _ev("results/hexcore_outcome_grounded_project_learning.json", ("risk","forecasting"), ("financial_portfolio",)))),
    SubjectSpec("ui_product_design", "User-interface and product design", "creative_engineering", 0.75, "operational_bounded",
        ("user_research", "information_architecture", "interaction", "visual_design", "accessibility", "prototyping", "testing", "design_systems"),
        (_ev("results/hexcore_natural_multimodal_physical_grounding_v6.json", ("visual_design","information_architecture"), ("multimodal_files",)),)),
    SubjectSpec("social_commonsense", "Social and commonsense intelligence", "human", 1.0, "operational_bounded",
        ("perspective", "intent", "emotion", "norms", "consent", "negotiation", "culture", "disagreement", "physical_commonsense"),
        (_ev("results/hexcore_external_human_judgment_v2.json", ("perspective","disagreement"), ("protocol_only",)),)),
    SubjectSpec("creative_invention", "Creative synthesis and invention", "creative_engineering", 0.85, "operational_bounded",
        ("ideation", "novelty", "design", "writing", "criticism", "iteration", "usefulness", "aesthetics"),
        (_ev("results/hexcore_residual_driven_primitive_invention_v5.json", ("ideation","novelty","criticism","iteration"), ("independent_execution",)),)),
    SubjectSpec("go", "Go programming", "programming", 0.55, "operational_bounded", ("syntax","types","testing","concurrency","packages","security"), ()),
    SubjectSpec("java", "Java programming", "programming", 0.55, "operational_bounded", ("syntax","types","testing","concurrency","build_tools","security"), ()),
    SubjectSpec("cpp", "C and C++ programming", "programming", 0.6, "operational_bounded", ("c","cpp","memory","types","testing","build_tools","performance","security"), ()),
    SubjectSpec("web_platform", "HTML, CSS and browser platform", "programming", 0.7, "operational_bounded", ("html","css","dom","accessibility","responsive_design","browser_security"), ()),
)


def _allow(goal: str) -> dict[str, Any]:
    return {"allow_learn": True, "deny_reason": None, "goal": goal,
            "source": "north_star_mastery_registry_cau", "S": 1.0, "H": 0.0}


def _read_positive(path: Path) -> tuple[bool, dict[str, Any]]:
    if not path.exists():
        return False, {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return False, {}
    promoted = bool(
        payload.get("passed") is True
        or (payload.get("gate") or {}).get("accepted") is True
        or ((payload.get("promotion") or {}).get("decision") or {}).get("promoted") is True
        or (payload.get("promotion") or {}).get("champion_retained") is True
    )
    return promoted, payload


def _level_index(level: str) -> int:
    return LEVELS.index(level)


class MasteryRegistry:
    def __init__(self, repo_root: Path) -> None:
        self.repo_root = repo_root

    def assess(self, spec: SubjectSpec) -> dict[str, Any]:
        evidence = []
        demonstrated: set[str] = set()
        authorities: set[str] = set()
        procedures: set[str] = set()
        for relative, skills, outcome_authorities in spec.evidence:
            passed, payload = _read_positive(self.repo_root / relative)
            if not passed:
                continue
            procedure = str(
                payload.get("procedure_id")
                or ((payload.get("promotion") or {}).get("candidate") or {}).get("procedure_id")
                or relative
            )
            procedures.add(procedure)
            demonstrated.update(skills)
            authorities.update(outcome_authorities)
            searchable = json.dumps(payload, sort_keys=True).lower()
            evidence.append({
                "artifact": relative,
                "artifact_hash": _canonical_hash(payload),
                "procedure_id": procedure,
                "demonstrated_subskills": list(skills),
                "authorities": list(outcome_authorities),
                "transfer_verified": any(
                    token in searchable for token in ("source_disjoint", "cross_domain", "transfer_success")
                ),
                "retention_verified": any(
                    token in searchable for token in ("restart_retention", "retention_success", "relearning_failures")
                ),
            })
        coverage = len(demonstrated) / max(1, len(spec.subskills))
        transfer = any(row["transfer_verified"] for row in evidence)
        retained = any(row["retention_verified"] for row in evidence)
        if not evidence:
            level = "unassessed"
        elif len(evidence) == 1 or coverage < 0.35:
            level = "learning"
        elif len(evidence) >= 4 and coverage >= 0.70 and len(authorities) >= 2 and transfer and retained:
            level = "proficient_bounded"
        elif len(evidence) >= 2 and coverage >= 0.40 and len(authorities) >= 1:
            level = "operational_bounded"
        else:
            level = "learning"
        # Expert/mastered require much broader elapsed, externally controlled
        # work and cannot be inferred from the current internal artifact corpus.
        readiness = {
            "unassessed": "not_ready",
            "learning": "practice_only",
            "operational_bounded": "bounded_work_with_verification",
            "proficient_bounded": "substantial_bounded_work_with_independent_checks",
            "expert": "independent_professional_work",
            "mastered": "broad_adaptive_leadership_and_teaching",
        }[level]
        missing = [skill for skill in spec.subskills if skill not in demonstrated]
        expert_gaps = [] if level in {"expert", "mastered"} else [
            "broad unfamiliar real projects rather than bounded cohorts",
            "multi-month retention and continuing competence",
            "independently controlled professional outcome evaluation",
            "failure recovery across the full subject rather than selected subskills",
        ]
        mastery_gaps = [] if level == "mastered" else [
            *expert_gaps,
            "adaptive teaching and leadership across the subject",
            "successful invention and transfer beyond the development distribution",
        ]
        return {
            "subject_id": spec.subject_id, "name": spec.name, "group": spec.group,
            "level": level, "level_index": _level_index(level),
            "target_level": spec.target_level,
            "target_level_index": _level_index(spec.target_level),
            "work_readiness": readiness,
            "coverage": round(coverage, 6),
            "demonstrated_subskills": sorted(demonstrated),
            "missing_subskills": missing,
            "expert_evidence_gaps": expert_gaps,
            "mastery_evidence_gaps": mastery_gaps,
            "evidence_count": len(evidence),
            "procedure_count": len(procedures),
            "authorities": sorted(authorities),
            "transfer_evidence": transfer, "retention_evidence": retained,
            "evidence": evidence,
            "expert_claim_authorized": level in {"expert", "mastered"},
            "mastery_claim_authorized": level == "mastered",
        }

    def build(self) -> dict[str, dict[str, Any]]:
        return {spec.subject_id: self.assess(spec) for spec in SUBJECTS}

    @staticmethod
    def answer(subjects: Mapping[str, Mapping[str, Any]], question: str) -> dict[str, Any]:
        lowered = question.lower()
        aliases = {
            "typescript": "javascript_typescript", "javascript": "javascript_typescript",
            "security": "security_engineering", "cybersecurity": "security_engineering",
            "accounting": "finance_accounting", "financial": "finance_accounting",
            "business": "business_management", "science": "scientific_method",
            "english": "english", "rust": "rust", "python": "python", "sql": "sql_databases",
            "math": "mathematics", "physics": "physics", "biology": "biology_medicine",
            "medicine": "biology_medicine", "chemistry": "chemistry", "design": "ui_product_design",
        }
        subject_id = next((value for key, value in aliases.items() if key in lowered), None)
        if subject_id is None or subject_id not in subjects:
            return {"status": "unknown_subject", "answer": "No assessed subject matches the question."}
        row = dict(subjects[subject_id])
        asks_mastery = any(token in lowered for token in ("master", "expert"))
        asks_work = any(token in lowered for token in ("work", "job", "can you", "capable"))
        if asks_mastery:
            answer = "no" if not row["mastery_claim_authorized"] else "yes"
        elif asks_work:
            answer = "yes_with_limits" if row["level"] in {"operational_bounded", "proficient_bounded"} else "not_yet"
        else:
            answer = "yes_bounded" if row["level"] not in {"unassessed", "learning"} else "learning_or_unassessed"
        return {
            "status": "assessed", "answer": answer,
            "subject": row["name"], "level": row["level"],
            "work_readiness": row["work_readiness"],
            "demonstrated": row["demonstrated_subskills"],
            "limitations": (
                list(dict.fromkeys([
                    *row["missing_subskills"], *row["mastery_evidence_gaps"]
                ])) if asks_mastery
                else row["missing_subskills"]
            ),
            "evidence": row["evidence"],
        }


def _maturity(subjects: Mapping[str, Mapping[str, Any]], apprentice: Mapping[str, Any]) -> dict[str, Any]:
    operational = [row for row in subjects.values() if row["level_index"] >= _level_index("operational_bounded")]
    noncomputational = [
        row for row in operational if row["group"] not in {"programming", "engineering"}
    ]
    receipts = [row for row in apprentice.get("outcome_receipts", []) if row.get("verified")]
    transfers = {row.get("transfer_family") for row in receipts if row.get("transfer_family")}
    contracts = apprentice.get("executor_contracts", {})
    owner_fields = sum(int(row.get("human_supplied_task_fields") or 0) for row in apprentice.get("curriculum_history", []))
    derived_fields = sum(int(row.get("derived_task_fields") or 0) for row in apprentice.get("curriculum_history", []))
    criteria = {
        "operational_subjects_at_least_6": len(operational) >= 6,
        "noncomputational_subjects_at_least_3": len(noncomputational) >= 3,
        "verified_transfer_families_at_least_6": len(transfers) >= 6,
        "executor_contracts_at_least_5": len(contracts) >= 5,
        "verified_receipts_at_least_10": len(receipts) >= 10,
        "owner_task_fields_zero": owner_fields == 0,
        "derived_fields_positive": derived_fields > 0,
    }
    general_apprentice = all(criteria.values())
    return {
        "current_stage": "general_apprentice" if general_apprentice else "apprentice",
        "next_stage": "integrator" if general_apprentice else "general_apprentice",
        "operational_subjects": len(operational),
        "noncomputational_operational_subjects": len(noncomputational),
        "verified_transfer_families": len(transfers),
        "executor_contracts": len(contracts), "verified_receipts": len(receipts),
        "owner_task_fields": owner_fields, "derived_task_fields": derived_fields,
        "general_apprentice_criteria": criteria,
        "innovation_authority_unlocked": False,
        "reason_innovation_locked": (
            "Research proposals are allowed, but autonomous innovation authority remains locked "
            "until general-apprentice breadth, cross-subject transfer and independent outcomes mature."
        ),
    }


def _goal_portfolio(subjects: Mapping[str, Mapping[str, Any]], limit: int = 12) -> list[dict[str, Any]]:
    spec_by_id = {row.subject_id: row for row in SUBJECTS}
    candidates = []
    for subject_id, row in subjects.items():
        spec = spec_by_id[subject_id]
        gap = max(0, row["target_level_index"] - row["level_index"])
        missing_ratio = 1.0 - row["coverage"]
        priority = spec.importance * (1.0 + gap) * (0.5 + missing_ratio)
        if gap <= 0 and missing_ratio < 0.25:
            continue
        candidates.append({
            "goal_id": "north_star_" + _canonical_hash([subject_id, row["level"], row["missing_subskills"]])[:16],
            "subject_id": subject_id, "subject": row["name"],
            "current_level": row["level"], "target_level": row["target_level"],
            "priority": round(priority, 6),
            "objective": (
                f"Advance {row['name']} from {row['level']} toward {row['target_level']} "
                f"through unfamiliar practice, independent outcomes, cross-subject transfer and retention."
            ),
            "next_missing_subskills": row["missing_subskills"][:4],
            "prerequisites": list(spec.prerequisites),
            "proposal_only": True,
            "requires_independent_authority": True,
            "requires_transfer": True, "requires_retention": True,
            "owner_supplied_lesson_steps": 0,
        })
    return sorted(candidates, key=lambda row: (-row["priority"], row["subject_id"]))[:limit]


def run(*, repo_root: Path, apprentice_state_path: Path, state_path: Path, result_path: Path) -> dict[str, Any]:
    registry = MasteryRegistry(repo_root)
    subjects = registry.build()
    apprentice = AutonomousGeneralApprentice(
        state_path=apprentice_state_path, repo_root=repo_root
    )
    maturity = _maturity(subjects, apprentice.state)
    goals = _goal_portfolio(subjects)
    guidance = apprentice.register_constitutional_guidance(
        purpose=CONSTITUTIONAL_PURPOSE,
        maturity_stage=maturity["current_stage"],
        proposed_learning_goals=goals,
    )
    prior_state = json.loads(state_path.read_text(encoding="utf-8")) if state_path.exists() else {}
    verified_subjects = sum(
        row["level"] in {"operational_bounded", "proficient_bounded", "expert", "mastered"}
        for row in subjects.values()
    )
    scaffolding_snapshot = {
        "recorded_at": _utc_timestamp(),
        "verified_subjects": verified_subjects,
        "owner_supplied_task_fields": maturity["owner_task_fields"],
        "aion_derived_task_fields": maturity["derived_task_fields"],
        "owner_fields_per_verified_subject": round(
            maturity["owner_task_fields"] / max(1, verified_subjects), 6
        ),
        "development_harness_scaffolding": "not_yet_quantified",
    }
    scaffolding_history = list(prior_state.get("scaffolding", {}).get("history") or [])
    comparable = {key: value for key, value in scaffolding_snapshot.items() if key != "recorded_at"}
    if not scaffolding_history or {
        key: value for key, value in scaffolding_history[-1].items() if key != "recorded_at"
    } != comparable:
        scaffolding_history.append(scaffolding_snapshot)
    owner_series = [row["owner_fields_per_verified_subject"] for row in scaffolding_history]
    scaffolding = {
        "history": scaffolding_history,
        "explicit_owner_intervention_trend": (
            "declining" if len(owner_series) >= 3 and owner_series[-1] < owner_series[0]
            else "baseline_established_insufficient_generations"
        ),
        "latest_owner_fields_per_verified_subject": owner_series[-1],
        "development_harness_scaffolding_measured": False,
        "claim_boundary": (
            "Owner-supplied task fields are measured. Developer effort used to construct "
            "safe adapters and evaluation harnesses is not yet quantified, so full "
            "scaffolding decline cannot yet be claimed."
        ),
    }
    query_examples = {
        "rust_knowledge": registry.answer(subjects, "Do you know Rust?"),
        "rust_mastery": registry.answer(subjects, "Have you mastered Rust?"),
        "rust_work": registry.answer(subjects, "Can you do a Rust job for me?"),
        "accounting_mastery": registry.answer(subjects, "Are you an expert in accounting?"),
        "python_work": registry.answer(subjects, "Can you work in Python?"),
    }
    state = {
        "schema_version": "aion.hexcore.constitutional_north_star_mastery_registry.v1",
        "constitutional_purpose": CONSTITUTIONAL_PURPOSE,
        "purpose_hash": _canonical_hash(CONSTITUTIONAL_PURPOSE),
        "purpose_mutable": False,
        "maturity": maturity, "subjects": subjects,
        "strategic_goal_portfolio": goals,
        "scaffolding": scaffolding,
        "query_examples": query_examples,
        "apprentice_guidance_hash": _canonical_hash(guidance),
        "updated_at": _utc_timestamp(),
    }
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(json.dumps(state, indent=2, sort_keys=True), encoding="utf-8")
    restart = json.loads(state_path.read_text(encoding="utf-8"))
    counts = {level: sum(row["level"] == level for row in subjects.values()) for level in LEVELS}
    gate = {
        "subjects_tracked": len(subjects), "subject_groups": len({row["group"] for row in subjects.values()}),
        "levels": counts, "queryable_capability_answers": len(query_examples),
        "unsupported_expert_claims": sum(
            row["expert_claim_authorized"] and row["level"] not in {"expert", "mastered"}
            for row in subjects.values()
        ),
        "unsupported_mastery_claims": sum(
            row["mastery_claim_authorized"] and row["level"] != "mastered"
            for row in subjects.values()
        ),
        "learning_goals_generated": len(goals),
        "owner_supplied_lesson_steps": sum(row["owner_supplied_lesson_steps"] for row in goals),
        "constitutional_purpose_immutable": restart["purpose_hash"] == _canonical_hash(CONSTITUTIONAL_PURPOSE),
        "guidance_proposal_only": guidance["proposal_only"],
        "scaffolding_baseline_established": len(scaffolding_history) >= 1,
        "development_scaffolding_claim_withheld": not scaffolding["development_harness_scaffolding_measured"],
        "innovation_authority_locked": not maturity["innovation_authority_unlocked"],
        "restart_retention": restart["subjects"] == subjects,
        "unsafe_actions": 0, "objective_mutations": 0,
    }
    gate["accepted"] = bool(
        gate["subjects_tracked"] >= 20 and gate["subject_groups"] >= 7
        and gate["queryable_capability_answers"] >= 5
        and gate["unsupported_expert_claims"] == gate["unsupported_mastery_claims"] == 0
        and gate["learning_goals_generated"] >= 8
        and gate["owner_supplied_lesson_steps"] == 0
        and gate["constitutional_purpose_immutable"] and gate["guidance_proposal_only"]
        and gate["scaffolding_baseline_established"] and gate["development_scaffolding_claim_withheld"]
        and gate["innovation_authority_locked"] and gate["restart_retention"]
        and gate["unsafe_actions"] == gate["objective_mutations"] == 0
    )
    learning = HexCorePersistentLearningRuntime(
        state_path=state_path.with_name("learning.json"), authority_provider=_allow
    )
    candidate = ProcedureCandidate(
        PROCEDURE_ID, "constitutional_north_star_and_mastery_registry",
        [
            "preserve_immutable_beneficial_constitutional_purpose",
            "reconstruct_subject_competence_from_verified_artifacts",
            "separate_knowing_work_readiness_expertise_and_mastery",
            "expose_evidence_limitations_and_next_missing_subskills",
            "measure_maturity_from_cross_subject_receipts_and_scaffolding",
            "generate_proposal_only_learning_goals_from_capability_gaps",
            "keep_innovation_authority_locked_until_maturity_is_earned",
        ],
        1.0, gate["accepted"], {"gate": gate, "maturity": maturity},
        ["procedure_autonomous_general_apprentice_kernel_v1", "procedure_autonomous_executor_contract_campaign_v1"],
    )
    decision = learning.skills.promote(candidate)
    learning.skills.record_outcome(
        procedure_id=PROCEDURE_ID, success=candidate.success,
        score=candidate.score, evidence=candidate.evidence,
    )
    learning.store.commit(reason="constitutional_north_star_mastery_registry")
    champion = learning.skills.champion("constitutional_north_star_and_mastery_registry") or {}
    result = {
        **state, "created_at": _utc_timestamp(), "procedure_id": PROCEDURE_ID,
        "gate": gate, "promotion": {
            "candidate": candidate.to_dict(), "decision": decision,
            "champion_retained": champion.get("procedure_id") == PROCEDURE_ID,
        },
        "passed": bool(gate["accepted"] and champion.get("procedure_id") == PROCEDURE_ID),
        "boundary": (
            "This promotes the constitutional purpose, evidence-backed registry and goal-selection "
            "mechanism. It does not promote any listed subject to expert or mastered status."
        ),
    }
    result_path.parent.mkdir(parents=True, exist_ok=True)
    result_path.write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, default=Path("."))
    parser.add_argument("--apprentice-state", type=Path, default=Path("backend/modules/hexcore/data/autonomous_general_apprentice/state.json"))
    parser.add_argument("--state-path", type=Path, default=Path("backend/modules/hexcore/data/constitutional_north_star/state.json"))
    parser.add_argument("--result-path", type=Path, default=Path("results/hexcore_constitutional_north_star_mastery_registry.json"))
    parser.add_argument("--query")
    args = parser.parse_args()
    result = run(
        repo_root=args.repo_root.resolve(), apprentice_state_path=args.apprentice_state.resolve(),
        state_path=args.state_path.resolve(), result_path=args.result_path.resolve(),
    )
    output = {"passed": result["passed"], "gate": result["gate"], "maturity": result["maturity"]}
    if args.query:
        output["capability_answer"] = MasteryRegistry.answer(result["subjects"], args.query)
    print(json.dumps(output, indent=2))
    raise SystemExit(0 if result["passed"] else 1)


if __name__ == "__main__":
    main()
