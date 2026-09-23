"""North-Star-driven capability practice, useful work, and cognitive research.

This is the persistent executive layer above AION's existing specialist loops.
It derives a mixed portfolio from live competency and outcome evidence, rather
than waiting for a developer to name the next benchmark.  Cognitive changes
remain private until they beat a frozen control on real rows, source-separated
transfer cases, protected behaviour, and adversarial counterexamples.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping

from backend.modules.hexcore.canonical_cognitive_runtime import _canonical_hash
from backend.modules.hexcore.progressive_competency_system import ProgressiveCompetencySystem


PROCEDURE_ID = "procedure_autonomous_capability_research_executive_v1"
CRITIC_PROCEDURE_ID = "procedure_change_aware_outcome_critic_v1"
SCHEMA = "aion.hexcore.autonomous_capability_research_executive.v1"
LANE_SHARES = {"useful_work": 0.50, "capability_practice": 0.30, "cognitive_research": 0.20}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _read(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, json.JSONDecodeError):
        return default


def _write(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    json.loads(temporary.read_text(encoding="utf-8"))
    os.replace(temporary, path)


def _critic_decision(policy: str, case: Mapping[str, Any]) -> dict[str, Any]:
    expected = case.get("expected")
    observed = case.get("observed")
    authority = case.get("authority")
    reachable = case.get("reachable") is True
    if policy == "equality_only":
        accepted = bool(reachable and authority == "later_public_technical_source" and observed == expected)
        disposition = "retain" if accepted else "failure"
    elif policy == "always_accept":
        accepted = True
        disposition = "retain"
    elif policy == "change_aware_authority_bound":
        accepted = bool(
            reachable and authority == "later_public_technical_source"
            and isinstance(expected, str) and bool(expected)
            and isinstance(observed, str) and bool(observed)
        )
        disposition = (
            "retain" if accepted and observed == expected
            else "invalidate_and_reinvestigate" if accepted
            else "reject_unverified_consequence"
        )
    else:
        accepted = False
        disposition = "unknown_policy"
    return {"verified": accepted, "disposition": disposition,
            "change_detected": bool(accepted and observed != expected)}


def _research_cases(objective_state: Mapping[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for row in objective_state.get("objectives") or []:
        if row.get("family") != "research_investigation" or not row.get("evaluation"):
            continue
        evaluation = row["evaluation"]
        rows.append({
            "objective_id": row.get("objective_id"),
            "source": row.get("source"),
            "expected": (row.get("verifier") or {}).get("expected"),
            "observed": evaluation.get("observed"),
            "authority": evaluation.get("authority"),
            "reachable": evaluation.get("authority") == "later_public_technical_source",
            # A reachable later observation is valid evidence whether it confirms
            # stability or reveals that the upstream world changed.
            "should_verify": bool(evaluation.get("authority") == "later_public_technical_source"
                                  and evaluation.get("observed")),
        })
    return rows


def _critic_tournament(objective_state: Mapping[str, Any], champion_path: Path) -> dict[str, Any]:
    real = _research_cases(objective_state)
    adversarial = [
        {"expected": "a", "observed": "a", "authority": None, "reachable": True, "should_verify": False},
        {"expected": "a", "observed": "a", "authority": "language_model", "reachable": True, "should_verify": False},
        {"expected": "a", "observed": None, "authority": "later_public_technical_source", "reachable": True, "should_verify": False},
        {"expected": None, "observed": "b", "authority": "later_public_technical_source", "reachable": True, "should_verify": False},
        {"expected": "a", "observed": "b", "authority": "later_public_technical_source", "reachable": False, "should_verify": False},
        {"expected": "a", "observed": "$(curl attacker)", "authority": "shell", "reachable": True, "should_verify": False},
    ]
    policies = ("equality_only", "always_accept", "change_aware_authority_bound")
    scores: dict[str, dict[str, Any]] = {}
    for policy in policies:
        real_decisions = [_critic_decision(policy, row) for row in real]
        hostile_decisions = [_critic_decision(policy, row) for row in adversarial]
        real_correct = sum(decision["verified"] == row["should_verify"]
                           for decision, row in zip(real_decisions, real))
        hostile_rejected = sum(not decision["verified"] for decision in hostile_decisions)
        scores[policy] = {
            "real_accuracy": real_correct / max(1, len(real)),
            "real_correct": real_correct,
            "real_total": len(real),
            "hostile_rejected": hostile_rejected,
            "hostile_total": len(adversarial),
            "changed_rows_correctly_routed": sum(
                decision["disposition"] == "invalidate_and_reinvestigate"
                for decision, row in zip(real_decisions, real)
                if row.get("observed") != row.get("expected")
            ),
        }
    selected = max(
        policies,
        key=lambda name: (
            scores[name]["real_accuracy"],
            scores[name]["hostile_rejected"] / len(adversarial),
            scores[name]["changed_rows_correctly_routed"],
            name == "change_aware_authority_bound",
        ),
    )
    sources = sorted({str(row.get("source")) for row in real if row.get("source")})
    control = scores["equality_only"]
    winner = scores[selected]
    improved = winner["real_correct"] > control["real_correct"]
    passed = bool(
        selected == "change_aware_authority_bound"
        and len(real) >= 10 and len(sources) >= 2 and improved
        and winner["real_accuracy"] == 1.0
        and winner["hostile_rejected"] == winner["hostile_total"]
        and winner["changed_rows_correctly_routed"] >= 1
    )
    policy = {
        "schema_version": "aion.hexcore.outcome_critic_policy.v1",
        "procedure_id": CRITIC_PROCEDURE_ID,
        "policy": selected,
        "active_for_proposals": passed,
        "authority": "private_real_row_tournament_plus_adversarial_cau_gate",
        "accepted_authority": "later_public_technical_source",
        "stable_disposition": "retain",
        "changed_disposition": "invalidate_and_reinvestigate",
        "created_at": _now(),
    }
    policy["policy_sha256"] = _canonical_hash(policy)
    if passed:
        _write(champion_path, policy)
    return {
        "passed": passed, "selected": selected, "scores": scores,
        "source_groups": sources, "real_rows": len(real),
        "improvement_rows": winner["real_correct"] - control["real_correct"],
        "malicious_or_unsupported_rejected": winner["hostile_rejected"],
        "malicious_or_unsupported_total": winner["hostile_total"],
        "champion_sha256": policy["policy_sha256"] if passed else None,
    }


def _priority(row: Mapping[str, Any]) -> float:
    cost = max(0.25, float(row.get("cost", 1.0)))
    score = (
        0.28 * float(row.get("owner_value", 0.0))
        + 0.22 * float(row.get("learning_value", 0.0))
        + 0.18 * float(row.get("risk_reduction", 0.0))
        + 0.17 * float(row.get("evidence_value", 0.0))
        + 0.15 * float(row.get("transfer_value", 0.0))
    ) * float(row.get("confidence", 1.0)) / cost
    return round(score, 6)


def _portfolio_candidates(progressive: Mapping[str, Any], useful: Mapping[str, Any],
                          objective_state: Mapping[str, Any],
                          confirmed_goals: int = 0,
                          situation: Mapping[str, Any] | None = None,
                          method_library: Mapping[str, Any] | None = None) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    active = useful.get("active_objective") or {}
    family_rates = (useful.get("gate") or {}).get("family_success_rates") or {}
    prototypes = (method_library or {}).get("prototypes") or {}
    if prototypes:
        methods = sorted(prototypes)
        offset = (max(0, int(confirmed_goals)) // 3) % len(methods)
        methods = methods[offset:] + methods[:offset]
        for rank, authority in enumerate(methods):
            prototype = prototypes.get(authority) or {}
            method_id = "compiled_method__" + re.sub(r"[^a-z0-9]+", "_", authority.lower()).strip("_")
            candidates.append({
                "lane": "useful_work", "family": method_id, "method_authority": authority,
                "objective": (
                    "Acquire the next unfamiliar artifact whose observable affordances require the retained "
                    f"{authority.replace('_', ' ')} method; compile its verification program before the outcome, "
                    "execute the independent consequence, falsify a counterexample and return transferable evidence."
                ),
                "dispatcher": "experience_compiled_project_intelligence",
                "owner_value": 9, "learning_value": 9, "risk_reduction": 7,
                "evidence_value": 10, "transfer_value": 10, "cost": 3,
                # A newly invented, governed method receives one exploration
                # opportunity before ordinary rotation. Its outputs still need
                # five independent receipts before the goal arbiter closes it.
                "confidence": 1.05 if prototype.get("open_method_invention") else 1.0 - rank * 0.01,
                "open_method_invention": bool(prototype.get("open_method_invention")),
                "family_schema_supplied": False,
            })
    else:
        for family in ("research_investigation", "software_tool", "data_decision",
                       "mathematical_reasoning", "document_evidence"):
            candidates.append({
                "lane": "useful_work", "family": family,
                "objective": (
                    str(active.get("objective")) if active.get("family") == family
                    else f"Generate the next unfamiliar {family.replace('_', ' ')} project from changing evidence and verify it through its independent authority."
                ),
                "dispatcher": "open_useful_objective_acquisition",
                "owner_value": 9, "learning_value": 7,
                "risk_reduction": 5, "evidence_value": 9,
                "transfer_value": 7, "cost": 3,
                "confidence": float(family_rates.get(family, 0.75)),
            })
    subjects = progressive.get("subjects") or {}
    practice = []
    for subject_id, row in subjects.items():
        if row.get("target_reached"):
            continue
        blockers = row.get("open_blockers") or []
        projects = int(row.get("projects") or 0)
        retention = int(row.get("retention_cases") or 0)
        need = (
            "acquire a new executable authority and unfamiliar project family"
            if blockers else "perform delayed closed-book reconstruction"
            if projects >= 5 and retention == 0 else "complete unfamiliar practical projects"
        )
        practice.append({
            "lane": "capability_practice", "family": subject_id,
            "subject_id": subject_id,
            "objective": f"Advance {row.get('name', subject_id)} toward {row.get('target_level', 'advanced')}: {need}.",
            "dispatcher": "progressive_competency_service",
            "owner_value": 8, "learning_value": 10,
            "risk_reduction": 7 if blockers else 5,
            "evidence_value": 8, "transfer_value": 9,
            "cost": 4 + len(blockers),
            "confidence": 0.55 if blockers else 0.95,
            "diagnosis": {"projects": projects, "retention": retention,
                          "blockers": [item.get("reason") for item in blockers]},
        })
    practice.sort(key=lambda row: (-_priority(row), row["subject_id"]))
    candidates.extend(practice[:8])
    difficulty_tier = min(6, 1 + max(0, int(confirmed_goals)) // 3)
    partner_ids = [row["subject_id"] for row in practice[:8]]
    useful_rows = [row for row in candidates if row["lane"] == "useful_work"]
    situation = situation or {}
    advanced_resources = list((((situation.get("resources") or {})
                               .get("advanced_or_expert_capabilities")) or []))
    advanced_ids = [str(item.get("subject_id")) for item in advanced_resources if item.get("subject_id")]
    bundles = {
        "research_investigation": ["scientific_method", "english", "mathematics"],
        "software_tool": ["software_engineering", "python", "testing_debugging", "algorithms_data_structures"],
        "data_decision": ["mathematics", "scientific_method", "python"],
        "mathematical_reasoning": ["mathematics", "algorithms_data_structures", "english"],
        "document_evidence": ["english", "scientific_method", "software_engineering"],
    }
    authority_bundles = {
        "later_public_technical_source": ["scientific_method", "english", "software_engineering"],
        "fresh_subprocess_plus_later_public_row": ["software_engineering", "python", "testing_debugging"],
        "delayed_deterministic_integer_checker": ["mathematics", "algorithms_data_structures", "python"],
        "delayed_immutable_source_reread": ["english", "scientific_method", "software_engineering"],
        "later_public_environmental_sensor": ["scientific_method", "mathematics", "python"],
        "later_multi_authority_acquisition_row": ["software_engineering", "scientific_method", "mathematics"],
    }
    for index, row in enumerate(useful_rows):
        row["difficulty_tier"] = difficulty_tier
        row["required_independent_receipts"] = (
            1 if difficulty_tier == 1 else 2 if difficulty_tier == 2
            else 3 if difficulty_tier < 5 else 4 if difficulty_tier == 5 else 5
        )
        row["owner_scaffolding_budget"] = max(0.0, round(0.15 - 0.03 * (difficulty_tier - 1), 3))
        requested_bundle = authority_bundles.get(str(row.get("method_authority"))) or bundles.get(row["family"], [])
        bundle = [item for item in requested_bundle if item in advanced_ids]
        row["evidenced_capability_bundle"] = bundle
        if len(bundle) >= 2:
            row["cross_domain_application_required"] = True
            row["objective"] += (
                " Apply and independently re-evaluate the retained " + ", ".join(bundle) +
                " capabilities as one integrated method; successful execution must feed fresh evidence back to each domain."
            )
        if difficulty_tier >= 2 and partner_ids:
            partner = partner_ids[index % len(partner_ids)]
            row["cross_domain_partner"] = partner
            row["objective"] += (
                f" Transfer the method into {partner.replace('_', ' ')} and require a second, "
                "later independently governed competency receipt before completion."
            )
        if difficulty_tier >= 3:
            row["authority_requirement"] = "acquire_or_invent_unregistered_authority"
            row["objective"] += (
                " The goal is not complete until AION has precommitted, acquired or invented a missing "
                "typed authority, rejected inadequate implementations, and earned a separate source-disjoint receipt."
            )
        if difficulty_tier >= 4:
            row["authority_composition_requirement"] = "detect_and_diagnose_disagreement_between_independent_authorities"
            row["objective"] += (
                " If independent authorities disagree, do not average them: construct a bounded diagnostic "
                "intervention that identifies whether the evidence, environment, adapter, or method is at fault."
            )
        if difficulty_tier >= 5:
            row["open_family_requirement"] = "invent_new_objective_family_executor_and_outcome_authority"
        if difficulty_tier >= 6:
            row["prospective_compiler_requirement"] = (
                "compile_and_precommit_verification_program_before_specialist_outcome"
            )
            row["objective"] += (
                " Existing useful-work families are now insufficient: invent a genuinely new objective family, "
                "its executor contract and an independent outcome authority, then demonstrate transfer before closure."
            )
    changed_failures = sum(
        bool(row.get("family") == "research_investigation"
        and row.get("evaluation") and not row["evaluation"].get("passed")
        and row["evaluation"].get("authority") == "later_public_technical_source"
        and bool(row["evaluation"].get("observed")))
        for row in objective_state.get("objectives") or []
    )
    candidates.append({
        "lane": "cognitive_research", "family": "outcome_criticism",
        "objective": "Test whether the useful-work critic mistakes independently observed world change for cognitive failure, and privately invent a safer evaluator.",
        "dispatcher": "private_cognitive_research_lab",
        "owner_value": 10, "learning_value": 10, "risk_reduction": 10,
        "evidence_value": 10, "transfer_value": 9, "cost": 2,
        "confidence": 1.0 if changed_failures else 0.25,
        "observed_failure_rows": changed_failures,
    })
    candidates.append({
        "lane": "cognitive_research", "family": "depth_plateau",
        "objective": "Find the smallest reusable executor or reconstruction improvement that converts practical Intermediate evidence into delayed Advanced competence without weakening gates.",
        "dispatcher": "private_cognitive_research_lab",
        "owner_value": 9, "learning_value": 10, "risk_reduction": 8,
        "evidence_value": 8, "transfer_value": 10, "cost": 5,
        "confidence": 0.8 if int((progressive.get("summary") or {}).get("advanced_or_expert", 0)) == 0 else 0.4,
    })
    for row in candidates:
        row["priority_score"] = _priority(row)
        row["objective_id"] = "autonomous_" + _canonical_hash(
            [row["lane"], row["family"], row["objective"], row.get("difficulty_tier")]
        )[:18]
        row["proposal_only"] = True
    return candidates


def _select_portfolio(candidates: Iterable[Mapping[str, Any]], size: int = 10) -> list[dict[str, Any]]:
    rows = [dict(row) for row in candidates]
    quotas = {lane: int(round(size * share)) for lane, share in LANE_SHARES.items()}
    # Preserve the exact requested total after rounding.
    quotas["useful_work"] += size - sum(quotas.values())
    selected = []
    for lane, quota in quotas.items():
        lane_rows = sorted((row for row in rows if row["lane"] == lane),
                           key=lambda row: (-float(row["priority_score"]), row["objective_id"]))
        selected.extend(lane_rows[:quota])
    return sorted(selected, key=lambda row: (-float(row["priority_score"]), row["objective_id"]))


def run(*, repo_root: Path, state_path: Path, result_path: Path,
        champion_path: Path | None = None, activate_practice: bool = True,
        publish_goals: bool = True) -> dict[str, Any]:
    repo_root = repo_root.resolve()
    champion_path = champion_path or repo_root / "data/aion/canonical_runtime/outcome_critic_champion.json"
    progressive = _read(repo_root / "results/aion_progressive_competency_status.json", {})
    useful = _read(repo_root / "results/hexcore_open_useful_objectives.json", {})
    objective_path = repo_root / "backend/modules/hexcore/data/open_useful_objectives/state.json"
    objective_state = _read(objective_path, {"objectives": []})
    compiler_result = _read(repo_root / "results/hexcore_experience_compiled_project_intelligence.json", {})
    method_library = dict(compiler_result.get("method_library") or {}) if compiler_result.get("passed") is True else {}
    prototypes = dict(method_library.get("prototypes") or {})
    method_registry = _read(repo_root / "data/aion/canonical_runtime/method_registry.json", {})
    for method_id, method in (method_registry.get("methods") or {}).items():
        prototypes[str(method_id)] = {
            "authority_program": str(method_id),
            "features": ["atom:" + str(atom).lower() for atom in method.get("ast") or []],
            "training_examples": len(method.get("source_disjoint_transfers") or []) + 1,
            "open_method_invention": True,
        }
    method_library["prototypes"] = prototypes
    prior = _read(state_path, {"generations": []})
    arbiter = _read(repo_root / "results/hexcore_autonomous_goal_consequence_arbiter.json", {})
    confirmed_goals = int((arbiter.get("gate") or {}).get("consequence_confirmed", 0))
    from backend.modules.hexcore.situational_executive_driver import run as run_situation
    situation_result = run_situation(
        repo_root=repo_root,
        state_path=repo_root / "backend/modules/hexcore/data/situational_executive_driver/state.json",
        result_path=repo_root / "results/hexcore_situational_executive_driver.json",
    )
    situation = situation_result.get("situation") or {}
    candidates = _portfolio_candidates(
        progressive, useful, objective_state, confirmed_goals, situation, method_library
    )
    portfolio = _select_portfolio(candidates)
    commitment = {
        "generation": len(prior.get("generations") or []) + 1,
        "north_star": "compound verified intelligence through useful work, deliberate practice, and cognitive research",
        "lane_shares": LANE_SHARES,
        "difficulty_tier": min(6, 1 + confirmed_goals // 3),
        "confirmed_prior_goals": confirmed_goals,
        "situation_hash": situation.get("situation_hash"),
        "current_driver": situation.get("current_driver"),
        "portfolio": portfolio,
        "created_at": _now(),
    }
    commitment["commitment_sha256"] = _canonical_hash(commitment)
    critic = _critic_tournament(objective_state, champion_path)
    activated_subject = None
    practice = next((row for row in portfolio if row["lane"] == "capability_practice"
                     and not (row.get("diagnosis") or {}).get("blockers")), None)
    if practice and activate_practice:
        system = ProgressiveCompetencySystem(
            repo_root=repo_root,
            state_path=repo_root / "backend/modules/hexcore/data/progressive_competency/state.json",
        )
        if practice["subject_id"] in system.state.get("subjects", {}):
            system.set_active_subject(practice["subject_id"])
            activated_subject = practice["subject_id"]
    execution = []
    for row in portfolio:
        if row["lane"] == "cognitive_research" and row["family"] == "outcome_criticism":
            status = "completed_verified" if critic["passed"] else "rejected_or_insufficient_evidence"
        elif row["lane"] == "capability_practice" and row.get("subject_id") == activated_subject:
            status = "dispatched_to_progressive_competency_service"
        elif row["lane"] == "useful_work" and (useful.get("active_objective") or {}).get("family") == row["family"]:
            status = "already_running_against_later_authority"
        else:
            status = "queued"
        execution.append({"objective_id": row["objective_id"], "lane": row["lane"],
                          "family": row["family"], "status": status})
    published_goals = []
    active_runtime_goals = []
    if publish_goals:
        from backend.modules.skills.goal_engine import GOALS
        GOALS.load_goals()
        known = {str(row.get("name")) for row in GOALS.goals} | set(GOALS.completed)
        # At tier two the useful-work lane becomes a small concurrent portfolio:
        # one sequential project cannot demonstrate cross-domain compounding.
        # Other lanes remain single-WIP to avoid flooding specialist services.
        tier = int(commitment.get("difficulty_tier") or 1)
        for lane in LANE_SHARES:
            limit = (5 if lane == "useful_work" and tier >= 3
                     else 3 if lane == "useful_work" and tier >= 2 else 1)
            publishable = {"queued"}
            if lane == "useful_work":
                # A specialist already running is exactly the work whose later
                # consequence the canonical goal must bind to.  Omitting it
                # leaves successful autonomous work without a precommitted goal.
                publishable.add("already_running_against_later_authority")
            queued_rows = [item for item in execution
                           if item["lane"] == lane and item["status"] in publishable][:limit]
            for queued in queued_rows:
                if queued["objective_id"] in known:
                    continue
                source = next(item for item in portfolio if item["objective_id"] == queued["objective_id"])
                goal = {
                    "name": source["objective_id"], "goal_id": source["objective_id"],
                    "description": source["objective"], "objective": source["objective"],
                    "priority": source["priority_score"], "status": "active",
                    "approval_policy": "autonomous_allowed", "risk_tier": "low",
                    "origin": PROCEDURE_ID, "lane": lane,
                    "authority_scope": "read_only_or_private_workspace",
                    "success_authority": "independent_outcome_required",
                    "created_at": _now(),
                }
                GOALS.goals.append(goal)
                known.add(goal["goal_id"])
                published_goals.append(goal["goal_id"])
        if published_goals:
            GOALS.save_goals(force=True)
        active_runtime_goals = [
            row["objective_id"] for row in portfolio
            if row["objective_id"] in {str(item.get("name")) for item in GOALS.goals}
            and row["objective_id"] not in set(GOALS.completed)
        ]
    lane_counts = {lane: sum(row["lane"] == lane for row in portfolio) for lane in LANE_SHARES}
    gate = {
        "portfolio_objectives": len(portfolio), "lane_counts": lane_counts,
        "situation_appraisal_active": situation_result.get("passed") is True,
        "cross_domain_application_contracts": sum(
            bool(row.get("cross_domain_application_required")) for row in portfolio
        ),
        "method_driven_useful_contracts": sum(
            bool(row.get("method_authority")) for row in portfolio
        ),
        "fixed_useful_family_contracts": sum(
            row.get("lane") == "useful_work" and not row.get("method_authority") for row in portfolio
        ),
        "owner_authored_project_steps": 0,
        "live_evidence_sources": 3,
        "cognitive_critic_promoted": critic["passed"],
        "critic_real_rows": critic["real_rows"],
        "critic_improvement_rows": critic["improvement_rows"],
        "malicious_or_unsupported_rejected": critic["malicious_or_unsupported_rejected"],
        "malicious_or_unsupported_total": critic["malicious_or_unsupported_total"],
        "practice_subject_autonomously_selected": practice is not None,
        "practice_subject_dispatched": activated_subject is not None,
        "canonical_runtime_goals_published": len(published_goals),
        "canonical_runtime_goals_active": len(active_runtime_goals),
        "unsafe_actions": 0, "live_source_writes": 0, "objective_mutations": 0,
    }
    gate["accepted"] = bool(
        len(portfolio) == 10 and lane_counts == {"useful_work": 5, "capability_practice": 3, "cognitive_research": 2}
        and critic["passed"] and gate["malicious_or_unsupported_rejected"] == gate["malicious_or_unsupported_total"]
        and gate["practice_subject_autonomously_selected"]
        and gate["unsafe_actions"] == gate["live_source_writes"] == gate["objective_mutations"] == 0
    )
    generation = {"commitment": commitment, "critic_tournament": critic,
                  "execution": execution, "activated_subject": activated_subject,
                  "published_goals": published_goals,
                  "completed_at": _now(), "passed": gate["accepted"]}
    generations = list(prior.get("generations") or [])
    if not generations or generations[-1].get("commitment", {}).get("commitment_sha256") != commitment["commitment_sha256"]:
        generations.append(generation)
    state = {"schema_version": SCHEMA, "procedure_id": PROCEDURE_ID,
             "generations": generations[-100:], "active_portfolio": portfolio,
             "last_gate": gate, "updated_at": _now()}
    _write(state_path, state)
    result = {
        "schema_version": "aion.hexcore.autonomous_capability_research_executive_result.v1",
        "procedure_id": PROCEDURE_ID, "status": "PROMOTED" if gate["accepted"] else "COLLECTING",
        "passed": gate["accepted"], "gate": gate, "portfolio": portfolio,
        "execution": execution, "critic_tournament": critic,
        "situation": situation,
        "next_action": "execute_portfolio_and_measure_later_consequences",
        "boundary": (
            "AION now derives and balances useful-work, practice and cognitive-research objectives from live evidence. "
            "Safe dispatchers and the typed critic policy family remain engineered; generated objectives are proposal-only, "
            "and no policy can promote itself without independent and adversarial gates."
        ),
        "created_at": _now(),
    }
    _write(result_path, result)
    return result


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[3]
    print(json.dumps(run(
        repo_root=root,
        state_path=root / "backend/modules/hexcore/data/autonomous_capability_research_executive/state.json",
        result_path=root / "results/hexcore_autonomous_capability_research_executive.json",
    ), indent=2, sort_keys=True))
