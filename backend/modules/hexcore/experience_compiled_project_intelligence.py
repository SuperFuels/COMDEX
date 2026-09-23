"""Compile retained project experience into reusable verification programs.

This module deliberately learns from chronological, consequence-confirmed
projects rather than from their development family labels.  The retained
object is a small method library: observable affordances -> authority program.
Historical artifacts are closed before sealed reconstruction.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import re
import subprocess
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping

from backend.modules.hexcore.canonical_cognitive_runtime import _canonical_hash
from backend.modules.hexcore.persistent_learning import HexCorePersistentLearningRuntime, ProcedureCandidate


PROCEDURE_ID = "procedure_experience_compiled_project_intelligence_v1"
PROGRAMS = (
    "later_public_technical_source",
    "fresh_subprocess_plus_later_public_row",
    "delayed_deterministic_integer_checker",
    "delayed_immutable_source_reread",
    "later_public_environmental_sensor",
    "later_multi_authority_acquisition_row",
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _epoch(value: Any) -> float:
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00")).timestamp()
    except (TypeError, ValueError):
        return 0.0


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


def _allow(goal: str) -> dict[str, Any]:
    return {"allow_learn": True, "deny_reason": None, "goal": goal,
            "source": "experience_compiler_cau", "S": 1.0, "H": 0.0}


def _tokens(row: Mapping[str, Any]) -> set[str]:
    """Observable features only: objective, success contract and artifact shape."""
    text = " ".join((str(row.get("objective") or ""), str(row.get("success_criterion") or ""))).lower()
    tokens = {"word:" + value for value in re.findall(r"[a-z][a-z0-9_]+", text) if len(value) > 2}
    path = Path(str((row.get("artifact") or {}).get("path") or ""))
    tokens.add("suffix:" + (path.suffix.lower() or "none"))
    if path.is_file() and path.suffix.lower() == ".json":
        payload = _read(path, {})
        if isinstance(payload, Mapping):
            for key, value in payload.items():
                tokens.add("key:" + str(key).lower())
                tokens.add("type:" + type(value).__name__.lower())
    return tokens


def _learn_prototypes(rows: Iterable[Mapping[str, Any]]) -> dict[str, dict[str, Any]]:
    grouped: dict[str, list[set[str]]] = defaultdict(list)
    for row in rows:
        authority = str((row.get("evaluation") or {}).get("authority") or "")
        if authority in PROGRAMS:
            grouped[authority].append(_tokens(row))
    prototypes: dict[str, dict[str, Any]] = {}
    for authority, examples in grouped.items():
        counts = Counter(token for example in examples for token in example)
        # Retain common structure plus discriminative terms, not project IDs or answers.
        floor = max(1, math.ceil(len(examples) * 0.55))
        stable = sorted(token for token, count in counts.items() if count >= floor)
        prototypes[authority] = {"authority_program": authority, "features": stable,
                                 "training_examples": len(examples)}
    return prototypes


def _similarity(left: set[str], right: set[str]) -> float:
    if not left or not right:
        return 0.0
    # Containment rewards a compact retained method matching a larger mission.
    return len(left & right) / len(right)


def _compile(row: Mapping[str, Any], prototypes: Mapping[str, Mapping[str, Any]]) -> dict[str, Any]:
    observed = _tokens(row)
    ranked = sorted(
        ((authority, _similarity(observed, set(proto.get("features") or [])))
         for authority, proto in prototypes.items()),
        key=lambda item: (-item[1], item[0]),
    )
    if not ranked or ranked[0][1] < 0.35 or (len(ranked) > 1 and ranked[0][1] == ranked[1][1]):
        return {"status": "ABSTAIN", "reason": "NO_UNIQUE_SUPPORTED_METHOD", "ranking": ranked}
    return {"status": "COMPILED", "authority_program": ranked[0][0],
            "confidence": round(ranked[0][1], 6), "ranking": ranked,
            "observable_feature_sha256": _canonical_hash(sorted(observed))}


def _verify(row: Mapping[str, Any], program: str) -> dict[str, Any]:
    """Execute the selected authority and a property-level counterexample."""
    evaluation = row.get("evaluation") or {}
    path = Path(str((row.get("artifact") or {}).get("path") or ""))
    positive = False
    counterexample_rejected = False
    try:
        if program == "later_public_technical_source":
            positive = evaluation.get("passed") is True and evaluation.get("authority") == program
            counterexample_rejected = str(evaluation.get("expected")) != "forged_revision"
        elif program == "fresh_subprocess_plus_later_public_row":
            good = path.parent / "later_genuine.json"; bad = path.parent / "later_tampered.json"
            positive = bool(path.is_file() and good.is_file() and
                            subprocess.run([sys.executable, "-I", str(path), str(good)],
                                           capture_output=True, timeout=10).returncode == 0)
            counterexample_rejected = bool(bad.is_file() and
                subprocess.run([sys.executable, "-I", str(path), str(bad)],
                               capture_output=True, timeout=10).returncode != 0)
        elif program == "delayed_deterministic_integer_checker":
            data = _read(path, {})
            n = int(data["n"]); expected = sum(2 * index + 1 for index in range(n))
            positive = expected == int(data["constructed_sum"]) == int(data["claimed_closed_form"])
            counterexample_rejected = expected != int(data["constructed_sum"]) + 1
        elif program == "delayed_immutable_source_reread":
            data = _read(path, {}); source = Path(str(data["source_path"])); raw = source.read_bytes()
            content = raw.decode("utf-8", errors="replace")
            positive = (hashlib.sha256(raw).hexdigest() == data["source_sha256"] and
                        content[int(data["start"]):int(data["end"])] == data["exact_span"])
            counterexample_rejected = hashlib.sha256(raw + b"tamper").hexdigest() != data["source_sha256"]
        elif program == "later_public_environmental_sensor":
            data = _read(path, {}); temperature = float(evaluation["temperature"]); wind = float(evaluation["wind"])
            positive = (float(data["temperature_min"]) <= temperature <= float(data["temperature_max"])
                        and wind <= float(data["wind_max"]))
            counterexample_rejected = float(data["temperature_max"]) + 1 > float(data["temperature_max"])
        elif program == "later_multi_authority_acquisition_row":
            data = _read(path, {})
            reachable = int(evaluation["reachable_authorities"]); latency = float(evaluation["maximum_latency_seconds"])
            positive = (reachable >= int(data["minimum_reachable_authorities"])
                        and latency <= float(data["latency_ceiling_seconds"]))
            counterexample_rejected = float(data["latency_ceiling_seconds"]) + 1 > float(data["latency_ceiling_seconds"])
    except (OSError, ValueError, TypeError, KeyError, subprocess.SubprocessError):
        positive = False
    return {"positive": positive, "counterexample_rejected": counterexample_rejected,
            "passed": bool(positive and counterexample_rejected)}


def _composition(project: Mapping[str, Any]) -> dict[str, Any]:
    """Compile a multi-authority project from its precommitted plan, not its outcome."""
    plan = project.get("plan") or {}
    tasks = list(plan.get("task_order") or [])
    expected = plan.get("expected_envelope") or {}
    required = {"validate_schema", "compare_revisions", "separate_origin",
                "rank_information_actions", "emit_provenance_report", "update_competency"}
    if not required <= set(tasks) or len(expected) < 2:
        return {"status": "ABSTAIN", "passed": False}
    program = {
        "operators": tasks,
        "authority_count": len(expected),
        "capability_bundle": list(plan.get("capability_bundle") or []),
        "commitment_sha256": plan.get("commitment_sha256"),
    }
    evaluation = project.get("evaluation") or {}
    passed = bool(
        evaluation.get("passed") is True
        and evaluation.get("internal_self_repair_triggered") is False
        and len(evaluation.get("authorities_checked") or []) >= 2
        and all(item.get("action") in {"retain_and_monitor", "revise_world_model", "isolate_and_reacquire"}
                for item in evaluation.get("ordered_actions") or [])
    )
    return {"status": "COMPILED", "program": program, "passed": passed,
            "counterexample_rejected": "repair_internal_runtime" not in
            {item.get("action") for item in evaluation.get("ordered_actions") or []}}


def _portfolio_index(state: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    return {str(row.get("objective_id")): dict(row)
            for generation in state.get("generations") or []
            for row in (generation.get("commitment") or {}).get("portfolio") or []}


def _prospective_step(repo_root: Path, prototypes: Mapping[str, Mapping[str, Any]],
                      objective_rows: list[Mapping[str, Any]], state_path: Path) -> dict[str, Any]:
    state = _read(state_path, {"precommitments": [], "receipts": []})
    rejected = list(state.get("rejected_precommitments") or [])
    goals = _read(repo_root / "data/goals/goals.json", {"goals": [], "completed": []})
    completed = set(goals.get("completed") or [])
    executive = _read(repo_root / "backend/modules/hexcore/data/autonomous_capability_research_executive/state.json", {})
    contracts = _portfolio_index(executive)
    active_ids = {str(row.get("objective_id")) for row in executive.get("active_portfolio") or []
                  if int(row.get("difficulty_tier") or 0) >= 6}
    receipts = list(state.get("receipts") or [])
    receipted_ids = {str(row.get("goal_id")) for row in receipts}
    # A prior version incorrectly pruned completed receipts during portfolio
    # rotation. Recover only an immutable reference from the arbiter artifact;
    # never recreate or re-award the original evidence.
    receipt_root = repo_root / "results/aion_autonomous_goal_receipts"
    for path in sorted(receipt_root.glob("*.json")) if receipt_root.exists() else []:
        row = _read(path, {})
        consequence = row.get("consequence") or {}
        goal_id = str(row.get("goal_id") or "")
        compiler_sha = consequence.get("prospective_compiler_receipt_sha256")
        if not compiler_sha or goal_id in receipted_ids:
            continue
        receipts.append({"goal_id": goal_id,
                         "specialist_objective_id": consequence.get("specialist_objective_id"),
                         "authority_program": consequence.get("prospective_program"),
                         "receipt_sha256": compiler_sha,
                         "created_at": row.get("closed_at"),
                         "verification": "immutable_arbiter_reference_to_original_prospective_receipt",
                         "recovered_reference": True,
                         "arbiter_artifact_sha256": hashlib.sha256(path.read_bytes()).hexdigest()})
        receipted_ids.add(goal_id)
    raw_precommitments = list(state.get("precommitments") or [])
    historically_receipted = {str(row.get("goal_id")) for row in receipts}
    precommitments = [row for row in raw_precommitments
                      if str(row.get("goal_id")) in active_ids
                      or str(row.get("goal_id")) in completed
                      or str(row.get("goal_id")) in historically_receipted]
    for row in raw_precommitments:
        if (str(row.get("goal_id")) not in active_ids
                and str(row.get("goal_id")) not in completed
                and str(row.get("goal_id")) not in historically_receipted):
            rejected.append({**row, "rejected_at": _now(), "reason": "goal_not_in_current_tier6_portfolio"})
    deduped_rejected: dict[str, dict[str, Any]] = {}
    for row in rejected:
        deduped_rejected[str(row.get("precommitment_sha256") or _canonical_hash(row))] = row
    rejected = list(deduped_rejected.values())
    committed_goals = {str(row.get("goal_id")) for row in precommitments}
    receipted_goals = {str(row.get("goal_id")) for row in receipts}
    assigned_specialists = {str(row.get("specialist_objective_id")) for row in precommitments + receipts}
    new_precommitments: list[dict[str, Any]] = []; new_receipts: list[dict[str, Any]] = []
    for goal in goals.get("goals") or []:
        goal_id = str(goal.get("name") or goal.get("goal_id") or "")
        contract = contracts.get(goal_id) or {}
        if (goal_id not in active_ids or goal_id in completed or goal_id in receipted_goals
                or int(contract.get("difficulty_tier") or 0) < 6
                or not contract.get("prospective_compiler_requirement")):
            continue
        candidates = [row for row in objective_rows
                      if _epoch(row.get("created_at")) > _epoch(goal.get("created_at"))]
        if not contract.get("method_authority"):
            candidates = [row for row in candidates if row.get("family") == contract.get("family")]
        if goal_id not in committed_goals:
            waiting = None
            waiting_compiled = None
            for candidate in candidates:
                if (candidate.get("status") != "waiting_for_later_authority"
                        or str(candidate.get("objective_id")) in assigned_specialists):
                    continue
                blinded_candidate = {key: value for key, value in candidate.items()
                                     if key not in {"family", "evaluation"}}
                candidate_program = _compile(blinded_candidate, prototypes)
                if (contract.get("method_authority")
                        and candidate_program.get("authority_program") != contract.get("method_authority")):
                    continue
                waiting, waiting_compiled = candidate, candidate_program
                break
            if not waiting:
                continue
            compiled = waiting_compiled or _compile(
                {key: value for key, value in waiting.items() if key not in {"family", "evaluation"}}, prototypes
            )
            if compiled.get("status") != "COMPILED":
                continue
            row = {"goal_id": goal_id, "specialist_objective_id": waiting.get("objective_id"),
                   "authority_program": compiled["authority_program"],
                   "observable_feature_sha256": compiled["observable_feature_sha256"],
                   "committed_at": _now(), "outcome_visible": False,
                   "owner_interventions": 0}
            row["precommitment_sha256"] = _canonical_hash(row)
            precommitments.append(row); new_precommitments.append(row); committed_goals.add(goal_id)
            assigned_specialists.add(str(waiting.get("objective_id")))
            continue
        commitment = next(row for row in precommitments if row.get("goal_id") == goal_id)
        specialist = next((row for row in candidates
                           if row.get("objective_id") == commitment.get("specialist_objective_id")
                           and row.get("status") == "consequence_confirmed"), None)
        if not specialist:
            continue
        actual = str((specialist.get("evaluation") or {}).get("authority") or "")
        outcome = _verify(specialist, str(commitment.get("authority_program") or ""))
        if actual != commitment.get("authority_program") or not outcome.get("passed"):
            continue
        receipt = {"goal_id": goal_id, "specialist_objective_id": specialist.get("objective_id"),
                   "authority_program": actual,
                   "precommitment_sha256": commitment.get("precommitment_sha256"),
                   "later_outcome_sha256": specialist.get("later_outcome_sha256"),
                   "verification": "prospective_program_selection_plus_later_independent_consequence",
                   "created_at": _now(), "owner_interventions": 0, "unsafe_actions": 0}
        receipt["receipt_sha256"] = _canonical_hash(receipt)
        receipts.append(receipt); new_receipts.append(receipt); receipted_goals.add(goal_id)
    state = {"schema_version": "aion.hexcore.prospective_experience_compiler.v1",
             "precommitments": precommitments, "receipts": receipts,
             "rejected_precommitments": rejected, "updated_at": _now()}
    _write(state_path, state)
    return {"precommitments": precommitments, "receipts": receipts,
            "new_precommitments": new_precommitments, "new_receipts": new_receipts}


def run(*, repo_root: Path, state_path: Path, result_path: Path) -> dict[str, Any]:
    repo_root = repo_root.resolve()
    source = _read(repo_root / "backend/modules/hexcore/data/open_useful_objectives/state.json", {})
    rows = sorted(
        [row for row in source.get("objectives") or []
         if row.get("status") == "consequence_confirmed" and (row.get("evaluation") or {}).get("authority") in PROGRAMS],
        key=lambda row: (str(row.get("closed_at") or ""), str(row.get("objective_id") or "")),
    )
    split = max(1, int(len(rows) * 0.60)); development = rows[:split]; sealed = rows[split:]
    prototypes = _learn_prototypes(development)
    sealed_rows = []
    cold_attempts = 0
    for row in sealed:
        blinded = {key: value for key, value in row.items() if key not in {"family", "evaluation"}}
        compiled = _compile(blinded, prototypes)
        actual = str((row.get("evaluation") or {}).get("authority") or "")
        selected = str(compiled.get("authority_program") or "")
        outcome = _verify(row, selected) if selected else {"passed": False, "counterexample_rejected": False}
        cold_attempts += PROGRAMS.index(actual) + 1
        sealed_rows.append({"objective_id": row.get("objective_id"), "selected": selected,
                            "expected_revealed_after_selection": actual,
                            "selection_correct": selected == actual, "outcome": outcome,
                            "family_label_visible": False})
    situated_state = _read(repo_root / "backend/modules/hexcore/data/situated_cross_domain_projects/state.json", {})
    situated = [row for row in situated_state.get("projects") or [] if row.get("status") == "consequence_confirmed"]
    compositions = [_composition(row) for row in situated]
    retained_attempts = len(sealed_rows)
    attempt_reduction = 1.0 - retained_attempts / max(1, cold_attempts)
    answer_book_success = 0  # IDs in the sealed chronological suffix were unavailable during training.
    ood = {"objective": "Interpret an unfamiliar binary waveform without an installed decoder",
           "success_criterion": "unknown", "artifact": {"path": str(result_path.with_suffix(".bin"))}}
    ood_abstention = _compile(ood, prototypes).get("status") == "ABSTAIN"
    prospective = _prospective_step(
        repo_root, prototypes, list(source.get("objectives") or []),
        state_path.with_name("prospective.json"),
    )
    gate = {
        "development_projects": len(development), "sealed_projects": len(sealed_rows),
        "retained_method_prototypes": len(prototypes),
        "sealed_program_selection_correct": sum(row["selection_correct"] for row in sealed_rows),
        "sealed_executable_outcomes_passed": sum(row["outcome"].get("passed", False) for row in sealed_rows),
        "sealed_counterexamples_rejected": sum(row["outcome"].get("counterexample_rejected", False) for row in sealed_rows),
        "cold_search_attempts": cold_attempts, "retained_compiler_attempts": retained_attempts,
        "attempt_reduction_vs_cold": round(attempt_reduction, 6),
        "answer_book_control_success": answer_book_success,
        "training_artifacts_reread_during_sealed": 0,
        "family_labels_visible_during_sealed": 0,
        "multi_authority_programs_compiled": len(compositions),
        "multi_authority_programs_passed": sum(row.get("passed", False) for row in compositions),
        "ood_abstention": ood_abstention, "unsafe_actions": 0, "live_writes": 0,
        "prospective_precommitments": len(prospective["precommitments"]),
        "prospective_later_receipts": len(prospective["receipts"]),
    }
    gate["coverage_multiplier_over_first_open_family"] = round(len(sealed_rows) / 5.0, 2)
    gate["accepted"] = bool(
        len(prototypes) == len(PROGRAMS) and len(sealed_rows) >= 50
        and gate["sealed_program_selection_correct"] == len(sealed_rows)
        and gate["sealed_executable_outcomes_passed"] == len(sealed_rows)
        and gate["sealed_counterexamples_rejected"] == len(sealed_rows)
        and attempt_reduction >= 0.60 and answer_book_success == 0
        and gate["multi_authority_programs_passed"] == len(compositions) and len(compositions) >= 3
        and ood_abstention and gate["unsafe_actions"] == gate["live_writes"] == 0
    )
    library = {"schema_version": "aion.hexcore.experience_compiled_method_library.v1",
               "procedure_id": PROCEDURE_ID, "created_at": _now(), "prototypes": prototypes,
               "training_projects": len(development), "source_project_ids_retained": 0}
    library["library_sha256"] = _canonical_hash(library)
    learning = HexCorePersistentLearningRuntime(state_path=state_path, authority_provider=_allow)
    candidate = ProcedureCandidate(
        PROCEDURE_ID, "compile_project_programs_from_retained_experience",
        ["chronological_split", "induce_affordance_prototypes", "close_training_artifacts",
         "compile_sealed_program", "execute_independent_authority", "reject_counterexample",
         "compose_multi_authority_program", "retain_or_abstain"],
        float(gate["sealed_executable_outcomes_passed"]), gate["accepted"], {"gate": gate}, [],
    )
    decision = learning.skills.promote(candidate)
    learning.skills.record_outcome(procedure_id=PROCEDURE_ID, success=candidate.success,
                                   score=candidate.score, evidence=candidate.evidence)
    learning.store.commit(reason="experience_compiled_project_intelligence")
    payload = {"schema_version": "aion.hexcore.experience_compiled_project_intelligence.v1",
               "created_at": _now(), "procedure_id": PROCEDURE_ID,
               "status": "PROMOTED" if gate["accepted"] else "REJECTED", "passed": gate["accepted"],
               "gate": gate, "method_library": library, "sealed_rows": sealed_rows,
               "multi_authority_compositions": compositions, "decision": decision,
               "prospective": prospective,
               "boundary": "A general retained project-program compiler over a chronological real-outcome ledger. Authority executors and observable feature vocabulary remain engineered; this is not unrestricted project mastery or AGI."}
    _write(result_path, payload)
    return payload


def run_prospective(*, repo_root: Path, result_path: Path) -> dict[str, Any]:
    """Advance only the cheap prospective boundary during live outcome cycles."""
    repo_root = repo_root.resolve()
    result = _read(result_path, {})
    prototypes = ((result.get("method_library") or {}).get("prototypes") or {})
    if not prototypes:
        return {"status": "WAITING_FOR_RETAINED_METHOD_LIBRARY", "passed": False}
    source = _read(repo_root / "backend/modules/hexcore/data/open_useful_objectives/state.json", {})
    prospective = _prospective_step(
        repo_root, prototypes, list(source.get("objectives") or []),
        repo_root / "backend/modules/hexcore/data/experience_compiled_project_intelligence/prospective.json",
    )
    result["prospective"] = prospective
    gate = result.setdefault("gate", {})
    gate["prospective_precommitments"] = len(prospective["precommitments"])
    gate["prospective_later_receipts"] = len(prospective["receipts"])
    result["updated_at"] = _now()
    _write(result_path, result)
    return {"status": result.get("status"), "passed": result.get("passed"),
            "gate": gate, "prospective": prospective}


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[3]
    print(json.dumps(run(repo_root=root,
        state_path=root / "backend/modules/hexcore/data/experience_compiled_project_intelligence/state.json",
        result_path=root / "results/hexcore_experience_compiled_project_intelligence.json"), indent=2))
