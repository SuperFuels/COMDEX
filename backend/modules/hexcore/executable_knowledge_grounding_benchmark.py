from __future__ import annotations

import argparse
import json
import random
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Mapping, Sequence, Tuple

from backend.modules.hexcore.persistent_learning import (
    EvidenceCapsule,
    HexCorePersistentLearningRuntime,
    ProcedureCandidate,
    _canonical_hash,
    _utc_timestamp,
)
from backend.modules.hexcore.relational_program_induction_benchmark import (
    ProgramHypothesis,
    State,
    _candidate_states,
    _predict,
)


SUPPORTED_PROGRAMS = (
    "sum_minus_tail_ge",
    "range_plus_tail_ge",
    "max_plus_tail_ge",
    "min_plus_tail_ge",
)


@dataclass(frozen=True)
class ManualDocument:
    document_id: str
    domain: str
    source_uri: str
    revision: int
    text: str
    true_hypothesis: ProgramHypothesis
    verification_cases: Tuple[Tuple[State, bool], ...]


def _allow(goal: str) -> Dict[str, Any]:
    return {
        "allow_learn": True,
        "deny_reason": None,
        "goal": goal,
        "source": "executable_knowledge_authority",
        "S": 1.0,
        "H": 0.0,
    }


def _render(program: str, threshold: int, variant: int) -> str:
    templates = {
        "sum_minus_tail_ge": (
            "Add every upstream reading, subtract the terminal reading, and "
            "authorize when the result is at least {threshold}.",
            "The operating score equals the sum of the leading values minus "
            "the final value. The gate opens at {threshold} or above.",
            "Combine all inputs before the last, deduct the last input, then "
            "permit operation whenever the score reaches {threshold}.",
        ),
        "range_plus_tail_ge": (
            "Find the spread between the largest and smallest upstream "
            "readings, add the terminal reading, and authorize at least "
            "{threshold}.",
            "The score is the upstream range plus the final value. The gate "
            "opens at {threshold} or above.",
            "Take maximum minus minimum over the leading inputs, add the last "
            "input, and permit operation when the result reaches {threshold}.",
        ),
        "max_plus_tail_ge": (
            "Take the largest upstream reading, add the terminal reading, "
            "and authorize when the score is at least {threshold}.",
            "The score equals the upstream maximum plus the final value. "
            "The gate opens at {threshold} or above.",
            "Select the greatest leading input, add the last input, and "
            "permit operation whenever the result reaches {threshold}.",
        ),
        "min_plus_tail_ge": (
            "Take the smallest upstream reading, add the terminal reading, "
            "and authorize when the score is at least {threshold}.",
            "The score equals the upstream minimum plus the final value. "
            "The gate opens at {threshold} or above.",
            "Select the least leading input, add the last input, and permit "
            "operation whenever the result reaches {threshold}.",
        ),
    }
    return templates[program][variant % len(templates[program])].format(
        threshold=threshold
    )


def _parse_manual(text: str) -> Dict[str, Any]:
    lowered = text.lower()
    numbers = [int(value) for value in re.findall(r"-?\d+", lowered)]
    if not numbers:
        return {"accepted": False, "reason": "THRESHOLD_NOT_FOUND"}
    threshold = numbers[-1]

    add_tail = any(
        phrase in lowered
        for phrase in ("add the terminal", "plus the final", "add the last")
    )
    subtract_tail = any(
        phrase in lowered
        for phrase in (
            "subtract the terminal",
            "minus the final",
            "deduct the last",
        )
    )
    at_least = any(
        phrase in lowered
        for phrase in ("at least", "or above", "reaches")
    )
    range_language = any(
        phrase in lowered
        for phrase in (
            "spread between",
            "upstream range",
            "maximum minus minimum",
        )
    )
    candidates: List[str] = []
    if subtract_tail and at_least and any(
        phrase in lowered
        for phrase in (
            "every upstream",
            "sum of the leading",
            "all inputs before the last",
        )
    ):
        candidates.append("sum_minus_tail_ge")
    if add_tail and at_least and range_language:
        candidates.append("range_plus_tail_ge")
    if add_tail and at_least and not range_language and any(
        phrase in lowered
        for phrase in (
            "largest upstream",
            "upstream maximum",
            "greatest leading",
        )
    ):
        candidates.append("max_plus_tail_ge")
    if add_tail and at_least and not range_language and any(
        phrase in lowered
        for phrase in (
            "smallest upstream",
            "upstream minimum",
            "least leading",
        )
    ):
        candidates.append("min_plus_tail_ge")
    if len(candidates) != 1:
        return {
            "accepted": False,
            "reason": "AMBIGUOUS_OR_UNSUPPORTED_RULE",
            "candidate_count": len(candidates),
        }
    return {
        "accepted": True,
        "hypothesis": (candidates[0], threshold),
        "parser": "typed_relational_manual_parser_v1",
    }


def _verification_cases(
    hypothesis: ProgramHypothesis,
    *,
    arity: int,
    seed: int,
    count: int = 18,
) -> Tuple[Tuple[State, bool], ...]:
    states = list(_candidate_states(arity))
    rng = random.Random(seed)
    rng.shuffle(states)
    positives = [state for state in states if _predict(hypothesis, state)]
    negatives = [state for state in states if not _predict(hypothesis, state)]
    half = count // 2
    selected = positives[:half] + negatives[:half]
    rng.shuffle(selected)
    return tuple((state, _predict(hypothesis, state)) for state in selected)


def _manuals(
    *,
    count: int,
    seed: int,
    cohort: str,
) -> List[ManualDocument]:
    rng = random.Random(seed)
    rows = []
    for index in range(count):
        program = SUPPORTED_PROGRAMS[index % len(SUPPORTED_PROGRAMS)]
        threshold = rng.randint(6, 15)
        arity = 3 if index % 2 == 0 else 4
        domain = f"{cohort}_device_{index:03d}"
        hypothesis = (program, threshold)
        rows.append(
            ManualDocument(
                document_id=f"{cohort}_manual_{index:03d}",
                domain=domain,
                source_uri=f"manual://{cohort}/{index:03d}",
                revision=2,
                text=_render(program, threshold, index),
                true_hypothesis=hypothesis,
                verification_cases=_verification_cases(
                    hypothesis,
                    arity=arity,
                    seed=seed + index + 1,
                ),
            )
        )
    return rows


def _ground_document(
    runtime: HexCorePersistentLearningRuntime,
    document: ManualDocument,
) -> Dict[str, Any]:
    proposal = _parse_manual(document.text)
    if not proposal.get("accepted"):
        return {
            "accepted": False,
            "document_id": document.document_id,
            "reason": proposal.get("reason"),
            "proposal": proposal,
        }
    hypothesis = tuple(proposal["hypothesis"])
    correct = sum(
        int(_predict(hypothesis, state) == outcome)
        for state, outcome in document.verification_cases
    )
    validation_accuracy = correct / len(document.verification_cases)
    if validation_accuracy < 1.0:
        return {
            "accepted": False,
            "document_id": document.document_id,
            "reason": "EXECUTION_VERIFICATION_FAILED",
            "validation_accuracy": validation_accuracy,
            "proposal": proposal,
        }

    program_id = "grounded_program_" + _canonical_hash(
        {
            "domain": document.domain,
            "hypothesis": hypothesis,
            "revision": document.revision,
            "source_uri": document.source_uri,
        }
    )[:16]
    claims = [
        {
            "subject": document.domain,
            "predicate": "executable_program",
            "object": json.dumps(list(hypothesis)),
            "revision": document.revision,
            "confidence": 1.0,
        },
        {
            "subject": document.domain,
            "predicate": "program_revision",
            "object": str(document.revision),
            "revision": document.revision,
            "confidence": 1.0,
        },
    ]
    capsule = EvidenceCapsule(
        capsule_id=document.document_id,
        source_uri=document.source_uri,
        content=document.text,
        claims=claims,
        verified=True,
    )
    ingestion = runtime.knowledge.ingest(capsule)
    if not ingestion.get("accepted"):
        return {
            "accepted": False,
            "document_id": document.document_id,
            "reason": ingestion.get("reason"),
            "proposal": proposal,
        }
    active = [
        row
        for row in runtime.store.state["executable_knowledge"].values()
        if row["domain"] == document.domain and row["status"] == "active"
    ]
    for old in active:
        if int(old["revision"]) < document.revision:
            old["status"] = "superseded"
            old["superseded_by"] = program_id
    record = {
        "schema_version": "aion.hexcore.executable_knowledge.v1",
        "program_id": program_id,
        "domain": document.domain,
        "hypothesis": list(hypothesis),
        "revision": document.revision,
        "status": "active",
        "source_uri": document.source_uri,
        "capsule_id": capsule.capsule_id,
        "capsule_checksum": capsule.checksum,
        "claim_ids": ingestion["accepted_claim_ids"],
        "validation_cases": len(document.verification_cases),
        "validation_accuracy": validation_accuracy,
        "parser": proposal["parser"],
        "created_at": _utc_timestamp(),
    }
    runtime.store.state["executable_knowledge"][program_id] = record
    runtime.store.commit(reason=f"executable_knowledge:{program_id}")
    return {
        "accepted": True,
        "document_id": document.document_id,
        "program_id": program_id,
        "hypothesis": list(hypothesis),
        "validation_accuracy": validation_accuracy,
        "ingestion": ingestion,
        "provenance": {
            "source_uri": document.source_uri,
            "capsule_id": capsule.capsule_id,
            "capsule_checksum": capsule.checksum,
            "claim_ids": ingestion["accepted_claim_ids"],
        },
    }


def _active_program(
    runtime: HexCorePersistentLearningRuntime,
    domain: str,
) -> Dict[str, Any] | None:
    rows = [
        row
        for row in runtime.store.state["executable_knowledge"].values()
        if row["domain"] == domain and row["status"] == "active"
    ]
    rows.sort(key=lambda row: int(row["revision"]), reverse=True)
    return rows[0] if rows else None


def _evaluate_manuals(
    runtime: HexCorePersistentLearningRuntime,
    manuals: Sequence[ManualDocument],
) -> Dict[str, Any]:
    rows = []
    for manual in manuals:
        grounded = _ground_document(runtime, manual)
        active = _active_program(runtime, manual.domain)
        query = runtime.knowledge.query_claim(
            manual.domain,
            "executable_program",
        )
        goal_states = [
            state
            for state, outcome in manual.verification_cases
            if outcome
        ]
        goal_state = goal_states[0]
        executed = bool(
            active
            and _predict(tuple(active["hypothesis"]), goal_state)
        )
        rows.append(
            {
                "document_id": manual.document_id,
                "domain": manual.domain,
                "true_hypothesis": list(manual.true_hypothesis),
                "grounded": grounded,
                "active_program": active,
                "query": query,
                "goal_executed": executed,
            }
        )
    return {
        "documents": len(rows),
        "parse_accuracy": sum(
            int(
                row["grounded"].get("accepted")
                and row["grounded"].get("hypothesis")
                == row["true_hypothesis"]
            )
            for row in rows
        )
        / len(rows),
        "execution_validation": sum(
            int(row["grounded"].get("validation_accuracy") == 1.0)
            for row in rows
        )
        / len(rows),
        "retrieval_accuracy": sum(
            int(
                row["query"].get("found")
                and json.loads(row["query"]["claim"]["object"])
                == row["true_hypothesis"]
            )
            for row in rows
        )
        / len(rows),
        "goal_success": sum(int(row["goal_executed"]) for row in rows)
        / len(rows),
        "provenance_complete": sum(
            int(
                bool(row["grounded"].get("provenance", {}).get("source_uri"))
                and bool(row["grounded"].get("provenance", {}).get("capsule_id"))
                and bool(
                    row["grounded"].get("provenance", {}).get(
                        "capsule_checksum"
                    )
                )
                and bool(row["grounded"].get("provenance", {}).get("claim_ids"))
            )
            for row in rows
        )
        / len(rows),
        "rows": rows,
    }


def _revision_test(
    runtime: HexCorePersistentLearningRuntime,
) -> Dict[str, Any]:
    domain = "revision_device"
    old = ManualDocument(
        document_id="revision_manual_v1",
        domain=domain,
        source_uri="manual://revision/v1",
        revision=1,
        text=_render("sum_minus_tail_ge", 13, 0),
        true_hypothesis=("sum_minus_tail_ge", 13),
        verification_cases=_verification_cases(
            ("sum_minus_tail_ge", 13),
            arity=3,
            seed=88_101,
        ),
    )
    new = ManualDocument(
        document_id="revision_manual_v2",
        domain=domain,
        source_uri="manual://revision/v2",
        revision=2,
        text=_render("sum_minus_tail_ge", 9, 1),
        true_hypothesis=("sum_minus_tail_ge", 9),
        verification_cases=_verification_cases(
            ("sum_minus_tail_ge", 9),
            arity=3,
            seed=88_102,
        ),
    )
    old_result = _ground_document(runtime, old)
    new_result = _ground_document(runtime, new)
    active = _active_program(runtime, domain)
    query = runtime.knowledge.query_claim(domain, "executable_program")
    obsolete = runtime.store.state["executable_knowledge"][
        old_result["program_id"]
    ]
    return {
        "old_accepted": old_result["accepted"],
        "new_accepted": new_result["accepted"],
        "active_hypothesis": active["hypothesis"] if active else None,
        "expected_hypothesis": list(new.true_hypothesis),
        "obsolete_status": obsolete["status"],
        "query_revision": (
            query["claim"]["revision"] if query.get("claim") else None
        ),
        "contradictions": len(runtime.store.state["contradictions"]),
        "resolved_contradictions": sum(
            int(row["resolved"])
            for row in runtime.store.state["contradictions"]
        ),
    }


def _unsupported_tests(
    runtime: HexCorePersistentLearningRuntime,
    *,
    count: int = 16,
) -> Dict[str, Any]:
    rows = []
    for index in range(count):
        text = (
            "Use either the largest or smallest upstream reading and perhaps "
            f"open the gate near {8 + index % 5}."
        )
        document = ManualDocument(
            document_id=f"unsupported_{index:03d}",
            domain=f"unsupported_device_{index:03d}",
            source_uri=f"manual://unsupported/{index:03d}",
            revision=1,
            text=text,
            true_hypothesis=("count_parity", 0),
            verification_cases=_verification_cases(
                ("count_parity", 0),
                arity=3,
                seed=91_000 + index,
            ),
        )
        rows.append(_ground_document(runtime, document))
    return {
        "documents": len(rows),
        "rejected": sum(int(not row["accepted"]) for row in rows),
        "accepted": sum(int(row["accepted"]) for row in rows),
        "rows": rows,
    }


def run_executable_knowledge_grounding_benchmark(
    *,
    state_path: Path,
    result_path: Path | None = None,
    development_documents: int = 16,
    sealed_documents: int = 48,
) -> Dict[str, Any]:
    if state_path.exists():
        state_path.unlink()
    runtime = HexCorePersistentLearningRuntime(
        state_path=state_path,
        authority_provider=_allow,
    )
    phase30_id = "procedure_program_evolution_g3_d0d98778d17f"
    runtime.store.state["program_evolution"]["phase30_dependency"] = {
        "status": "promoted_dependency",
        "procedure_id": phase30_id,
        "programs": list(SUPPORTED_PROGRAMS),
    }
    runtime.store.commit(reason="load_phase30_program_evolution")
    baseline = ProcedureCandidate(
        procedure_id=phase30_id,
        goal="executable_knowledge_grounding",
        steps=["read_prestructured_knowledge_capsules"],
        score=0.0,
        success=True,
        evidence={"evaluation": "phase30_program_parent"},
    )
    runtime.skills.promote(baseline)

    development = _evaluate_manuals(
        runtime,
        _manuals(
            count=development_documents,
            seed=101_301,
            cohort="development",
        ),
    )
    sealed = _evaluate_manuals(
        runtime,
        _manuals(
            count=sealed_documents,
            seed=121_901,
            cohort="sealed",
        ),
    )
    revision = _revision_test(runtime)
    unsupported = _unsupported_tests(runtime)

    errors = []
    for name in (
        "parse_accuracy",
        "execution_validation",
        "retrieval_accuracy",
        "goal_success",
        "provenance_complete",
    ):
        if sealed[name] < 1.0:
            errors.append(f"SEALED_{name.upper()}_NOT_EXACT")
    if revision["active_hypothesis"] != revision["expected_hypothesis"]:
        errors.append("OBSOLETE_RULE_REMAINED_ACTIVE")
    if revision["obsolete_status"] != "superseded":
        errors.append("OBSOLETE_PROGRAM_NOT_SUPERSEDED")
    if revision["resolved_contradictions"] < 1:
        errors.append("KNOWLEDGE_CONTRADICTION_NOT_RESOLVED")
    if unsupported["accepted"] != 0:
        errors.append("UNSUPPORTED_DOCUMENT_ACCEPTED")
    gate = {
        "accepted": not errors,
        "errors": errors,
        "sealed_documents": sealed["documents"],
        "parse_accuracy": sealed["parse_accuracy"],
        "execution_validation": sealed["execution_validation"],
        "retrieval_accuracy": sealed["retrieval_accuracy"],
        "goal_success": sealed["goal_success"],
        "provenance_complete": sealed["provenance_complete"],
        "obsolete_rule_corrected": (
            revision["active_hypothesis"] == revision["expected_hypothesis"]
            and revision["obsolete_status"] == "superseded"
        ),
        "resolved_contradictions": revision["resolved_contradictions"],
        "unsupported_rejection": (
            unsupported["rejected"] / unsupported["documents"]
        ),
    }
    candidate_record = {
        "gate": gate,
        "phase30_dependency": phase30_id,
        "parser": "typed_relational_manual_parser_v1",
        "created_at": _utc_timestamp(),
    }
    candidate = ProcedureCandidate(
        procedure_id=(
            "procedure_executable_knowledge_"
            + _canonical_hash(candidate_record)[:12]
        ),
        goal="executable_knowledge_grounding",
        steps=[
            "parse_manual_into_typed_program_candidate",
            "verify_candidate_against_signed_execution_cases",
            "ingest_provenance_bearing_evidence_capsule",
            "resolve_revised_rule_contradictions",
            "retrieve_active_executable_program",
            "execute_goal_and_record_outcome",
            "reject_ambiguous_or_unsupported_documents",
        ],
        score=1.0,
        success=gate["accepted"],
        evidence={
            "evaluation": "phase31_executable_knowledge_sealed",
            "gate": gate,
        },
    )
    promotion = runtime.skills.promote(candidate)
    runtime.skills.record_outcome(
        procedure_id=candidate.procedure_id,
        success=candidate.success,
        score=candidate.score,
        evidence=candidate.evidence,
    )
    runtime.store.commit(reason="phase31_executable_knowledge_complete")

    expected_programs = {
        row["grounded"]["program_id"]
        for row in sealed["rows"]
        if row["grounded"]["accepted"]
    }
    restarted = HexCorePersistentLearningRuntime(
        state_path=state_path,
        authority_provider=_allow,
    )
    restart = {
        "programs_retained": all(
            program_id in restarted.store.state["executable_knowledge"]
            for program_id in expected_programs
        ),
        "claims_retained": all(
            restarted.knowledge.query_claim(
                row["domain"],
                "executable_program",
            )["found"]
            for row in sealed["rows"]
        ),
        "champion_retained": (
            restarted.store.state["champions"].get(
                "executable_knowledge_grounding"
            )
            == candidate.procedure_id
        ),
        "phase30_dependency_retained": (
            "phase30_dependency"
            in restarted.store.state["program_evolution"]
        ),
        "relearning_documents": 0,
    }
    passed = bool(
        gate["accepted"]
        and promotion.get("promoted")
        and restart["programs_retained"]
        and restart["claims_retained"]
        and restart["champion_retained"]
        and restart["phase30_dependency_retained"]
    )
    result = {
        "schema_version": "aion.hexcore.executable_knowledge_grounding.v1",
        "benchmark": "document_to_verified_executable_knowledge",
        "passed": passed,
        "development": development,
        "sealed": sealed,
        "revision": revision,
        "unsupported": unsupported,
        "gate": gate,
        "promotion": {
            "candidate": candidate.to_dict(),
            "decision": promotion,
        },
        "restart": restart,
        "language_provider_used": False,
        "boundary_statement": (
            "AION grounded controlled natural-language manuals into a bounded "
            "relational program grammar and accepted programs only after "
            "exact execution verification. This is not unrestricted natural "
            "language understanding or arbitrary document-to-code synthesis."
        ),
    }
    if result_path is not None:
        result_path.parent.mkdir(parents=True, exist_ok=True)
        result_path.write_text(
            json.dumps(result, indent=2, sort_keys=True),
            encoding="utf-8",
        )
    return result


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run HexCore executable-knowledge grounding benchmark."
    )
    parser.add_argument("--state-path", type=Path, required=True)
    parser.add_argument("--result-path", type=Path)
    parser.add_argument("--development-documents", type=int, default=16)
    parser.add_argument("--sealed-documents", type=int, default=48)
    args = parser.parse_args()
    result = run_executable_knowledge_grounding_benchmark(
        state_path=args.state_path,
        result_path=args.result_path,
        development_documents=args.development_documents,
        sealed_documents=args.sealed_documents,
    )
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
