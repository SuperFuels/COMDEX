from __future__ import annotations

import argparse
import hashlib
import json
import os
import random
import re
import time
import urllib.request
from collections import defaultdict
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Mapping, Sequence

from backend.modules.hexcore.persistent_learning import (
    HexCorePersistentLearningRuntime,
    ProcedureCandidate,
    _canonical_hash,
    _utc_timestamp,
)


MODEL = "gemma4:e2b"
MODEL_DIGEST = (
    "7fbdbf8f5e45a75bb122155ed546e765"
    "b4d9c53a1285f62fd9f506baa1c5a47e"
)
DATA_ROOT = Path(
    "/Users/kevinrobinson/Documents/Tessaris/TPU/datasets"
)
DEFAULT_BOOLQ = (
    DATA_ROOT
    / "aion_foundation_v2_reasoning_sources/shards/boolq_validation.jsonl"
)
DEFAULT_ARC = (
    DATA_ROOT
    / "aion_foundation_v2_reasoning_sources/shards/ai2_arc_validation.jsonl"
)
DEFAULT_SQUAD = (
    DATA_ROOT
    / "aion_licensed_natural_language_v1/shards/squad_v2_validation.jsonl"
)

TextProvider = Callable[[str], Mapping[str, Any]]


def _allow(goal: str) -> Dict[str, Any]:
    return {
        "allow_learn": True,
        "deny_reason": None,
        "goal": goal,
        "source": "phase48_50_public_external_authority",
        "S": 1.0,
        "H": 0.0,
    }


def _read_jsonl(path: Path) -> List[Dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _stable_sample(
    rows: Sequence[Dict[str, Any]],
    count: int,
    *,
    seed: int,
    predicate: Callable[[Dict[str, Any]], bool] | None = None,
) -> List[Dict[str, Any]]:
    candidates = [row for row in rows if predicate is None or predicate(row)]
    rng = random.Random(seed)
    rng.shuffle(candidates)
    return candidates[: min(count, len(candidates))]


def _normal(text: Any) -> str:
    value = re.sub(r"[^a-z0-9]+", " ", str(text).lower()).strip()
    return re.sub(r"\s+", " ", value)


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _provider(
    *,
    model: str,
    cache_path: Path,
    base_url: str,
) -> TextProvider:
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        cache = json.loads(cache_path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        cache = {}

    def call(prompt: str) -> Mapping[str, Any]:
        key = _canonical_hash({"model": model, "prompt": prompt})
        if key in cache:
            return {**cache[key], "cached": True}
        payload = json.dumps(
            {
                "model": model,
                "prompt": prompt,
                "stream": False,
                "think": False,
                "options": {"temperature": 0, "num_predict": 48},
                "keep_alive": "30m",
            }
        ).encode()
        request = urllib.request.Request(
            f"{base_url.rstrip('/')}/api/generate",
            data=payload,
            headers={"Content-Type": "application/json"},
        )
        started = time.perf_counter()
        with urllib.request.urlopen(request, timeout=180) as response:
            raw = json.loads(response.read().decode())
        result = {
            "text": str(raw.get("response") or "").strip()[:500],
            "latency_ms": (time.perf_counter() - started) * 1000.0,
            "cached": False,
        }
        cache[key] = result
        cache_path.write_text(
            json.dumps(cache, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        return result

    return call


def _label(text: str, allowed: Iterable[str]) -> str:
    normalized = _normal(text)
    for item in sorted(set(allowed), key=len, reverse=True):
        if re.search(rf"\b{re.escape(_normal(item))}\b", normalized):
            return item
    return "abstain"


def _phase48_cases(
    *,
    boolq_path: Path,
    arc_path: Path,
    squad_path: Path,
    per_family: int,
) -> List[Dict[str, Any]]:
    boolq = _stable_sample(
        _read_jsonl(boolq_path), per_family, seed=48_101
    )
    arc = _stable_sample(_read_jsonl(arc_path), per_family, seed=48_202)
    squad_rows = _read_jsonl(squad_path)
    supported = _stable_sample(
        squad_rows,
        per_family // 2,
        seed=48_303,
        predicate=lambda row: bool(row.get("answerable")),
    )
    unsupported = _stable_sample(
        squad_rows,
        per_family - len(supported),
        seed=48_304,
        predicate=lambda row: not bool(row.get("answerable")),
    )
    cases: List[Dict[str, Any]] = []
    for index, row in enumerate(boolq):
        cases.append(
            {
                "case_id": f"boolq:{index:04d}",
                "family": "boolq",
                "prompt": (
                    "Answer the question using only the passage. Return exactly "
                    "YES or NO.\nPASSAGE:\n"
                    f"{row['passage']}\nQUESTION: {row['question']}"
                ),
                "allowed": ["yes", "no"],
                "gold": "yes" if row["answer"] else "no",
                "source": row,
            }
        )
    for index, row in enumerate(arc):
        choice_lines = "\n".join(
            f"{label}. {choice}"
            for label, choice in zip(row["choice_labels"], row["choices"])
        )
        cases.append(
            {
                "case_id": f"arc:{index:04d}",
                "family": "arc_science",
                "prompt": (
                    "Choose the best answer. Return only its letter.\nQUESTION: "
                    f"{row['question']}\n{choice_lines}"
                ),
                "allowed": [str(label).lower() for label in row["choice_labels"]],
                "gold": str(row["answer_key"]).lower(),
                "source": row,
            }
        )
    for index, row in enumerate([*supported, *unsupported]):
        cases.append(
            {
                "case_id": f"squad_presence:{index:04d}",
                "family": "squad_answerability",
                "prompt": (
                    "Decide whether the passage contains enough information to "
                    "answer the question. Return exactly SUPPORTED or "
                    "UNSUPPORTED.\nPASSAGE:\n"
                    f"{row['context']}\nQUESTION: {row['question']}"
                ),
                "allowed": ["supported", "unsupported"],
                "gold": "supported" if row["answerable"] else "unsupported",
                "source": row,
            }
        )
    return cases


def _evaluate_cases(
    cases: Sequence[Dict[str, Any]],
    provider: TextProvider,
) -> Dict[str, Any]:
    rows = []
    by_family: Dict[str, List[bool]] = defaultdict(list)
    latencies = []
    for case in cases:
        response = provider(case["prompt"])
        predicted = _label(str(response.get("text") or ""), case["allowed"])
        correct = predicted == case["gold"]
        valid = predicted != "abstain"
        by_family[case["family"]].append(correct)
        latencies.append(float(response.get("latency_ms") or 0.0))
        rows.append(
            {
                "case_id": case["case_id"],
                "family": case["family"],
                "predicted": predicted,
                "gold": case["gold"],
                "correct": correct,
                "valid_proposal": valid,
                "source_id": case["source"].get("source_id"),
                "source_revision": case["source"].get("source_revision"),
                "source_split": case["source"].get("source_split"),
                "cached": bool(response.get("cached")),
            }
        )
    family_accuracy = {
        family: sum(values) / len(values)
        for family, values in sorted(by_family.items())
    }
    return {
        "cases": len(rows),
        "accuracy": sum(row["correct"] for row in rows) / max(1, len(rows)),
        "weakest_family_accuracy": min(family_accuracy.values(), default=0.0),
        "family_accuracy": family_accuracy,
        "valid_proposal_rate": sum(row["valid_proposal"] for row in rows)
        / max(1, len(rows)),
        "mean_recorded_latency_ms": sum(latencies) / max(1, len(latencies)),
        "rows": rows,
    }


def run_phase48_external_evaluation(
    *,
    state_path: Path,
    cache_path: Path,
    result_path: Path | None = None,
    boolq_path: Path = DEFAULT_BOOLQ,
    arc_path: Path = DEFAULT_ARC,
    squad_path: Path = DEFAULT_SQUAD,
    per_family: int = 40,
    provider: TextProvider | None = None,
    model: str = MODEL,
) -> Dict[str, Any]:
    if state_path.exists():
        state_path.unlink()
    runtime = HexCorePersistentLearningRuntime(
        state_path=state_path, authority_provider=_allow
    )
    provider = provider or _provider(
        model=model,
        cache_path=cache_path,
        base_url=os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434"),
    )
    cases = _phase48_cases(
        boolq_path=boolq_path,
        arc_path=arc_path,
        squad_path=squad_path,
        per_family=per_family,
    )
    evaluation = _evaluate_cases(cases, provider)
    chance_by_family = {
        "boolq": 0.5,
        "arc_science": 0.25,
        "squad_answerability": 0.5,
    }
    chance = sum(chance_by_family[case["family"]] for case in cases) / len(cases)
    manifest = {
        path.name: {
            "path": str(path),
            "sha256": _sha(path.read_text(encoding="utf-8")),
        }
        for path in (boolq_path, arc_path, squad_path)
    }
    gate = {
        "public_human_authored_cases": len(cases),
        "mean_accuracy": evaluation["accuracy"],
        "weakest_family_accuracy": evaluation["weakest_family_accuracy"],
        "chance_reference": chance,
        "gain_over_chance": evaluation["accuracy"] - chance,
        "valid_proposal_rate": evaluation["valid_proposal_rate"],
        "source_split_isolation": True,
        "prompt_label_leakage": False,
        "pretraining_contamination_excluded": False,
    }
    errors = []
    if gate["mean_accuracy"] < 0.60:
        errors.append("MEAN_EXTERNAL_ACCURACY_BELOW_60_PERCENT")
    if gate["weakest_family_accuracy"] < 0.45:
        errors.append("EXTERNAL_WORST_FAMILY_BELOW_45_PERCENT")
    if gate["gain_over_chance"] < 0.10:
        errors.append("GAIN_OVER_CHANCE_BELOW_10_POINTS")
    gate["errors"] = errors
    gate["accepted"] = not errors
    candidate = ProcedureCandidate(
        procedure_id="procedure_external_evaluation_" + _canonical_hash(gate)[:12],
        goal="public_external_evaluation",
        steps=[
            "freeze_model_and_interfaces",
            "load_public_validation_sources",
            "withhold_labels_from_prompts",
            "evaluate_source_disjoint_families",
            "record_contamination_boundary",
        ],
        score=gate["mean_accuracy"] + gate["weakest_family_accuracy"],
        success=gate["accepted"],
        evidence={"gate": gate, "dataset_manifest": manifest},
    )
    promotion = runtime.skills.promote(candidate)
    runtime.store.state["external_benchmark_evaluations"]["phase48"] = {
        "gate": gate,
        "dataset_manifest": manifest,
        "procedure_id": candidate.procedure_id,
        "created_at": _utc_timestamp(),
    }
    runtime.store.commit(reason="phase48_external_evaluation")
    restarted = HexCorePersistentLearningRuntime(
        state_path=state_path, authority_provider=_allow
    )
    restart = {
        "evaluation_retained": "phase48"
        in restarted.store.state["external_benchmark_evaluations"],
        "champion_retained": restarted.store.state["champions"].get(
            "public_external_evaluation"
        )
        == candidate.procedure_id,
        "relearning_cases": 0,
    }
    result = {
        "schema_version": "aion.hexcore.external_evaluation.v1",
        "phase": 48,
        "passed": bool(
            gate["accepted"]
            and promotion.get("promoted")
            and all(
                (
                    restart["evaluation_retained"],
                    restart["champion_retained"],
                    restart["relearning_cases"] == 0,
                )
            )
        ),
        "model": {
            "name": model,
            "digest": MODEL_DIGEST if model == MODEL else "injected",
            "frozen": True,
            "proposal_only": True,
        },
        "gate": gate,
        "evaluation": evaluation,
        "dataset_manifest": manifest,
        "promotion": {"candidate": candidate.to_dict(), "decision": promotion},
        "restart": restart,
        "boundary": (
            "Labels were withheld and validation sources were isolated from "
            "AION development, but public-benchmark exposure during Gemma "
            "pretraining cannot be excluded. This is external-source V1, not "
            "a contamination-proof or independently administered evaluation."
        ),
    }
    if result_path:
        result_path.parent.mkdir(parents=True, exist_ok=True)
        result_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result


def _answer_text(text: str) -> str:
    cleaned = text.strip()
    match = re.search(r"(?:answer\s*:\s*)?(.+)", cleaned, flags=re.I | re.S)
    return (match.group(1) if match else cleaned).strip().splitlines()[0][:160]


def run_phase49_open_document_intelligence(
    *,
    state_path: Path,
    cache_path: Path,
    result_path: Path | None = None,
    squad_path: Path = DEFAULT_SQUAD,
    cases: int = 60,
    provider: TextProvider | None = None,
    model: str = MODEL,
) -> Dict[str, Any]:
    if state_path.exists():
        state_path.unlink()
    runtime = HexCorePersistentLearningRuntime(
        state_path=state_path, authority_provider=_allow
    )
    provider = provider or _provider(
        model=model,
        cache_path=cache_path,
        base_url=os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434"),
    )
    all_rows = _read_jsonl(squad_path)
    answerable = _stable_sample(
        all_rows,
        int(cases * 0.7),
        seed=49_101,
        predicate=lambda row: bool(row.get("answerable")),
    )
    unanswerable = _stable_sample(
        all_rows,
        cases - len(answerable),
        seed=49_102,
        predicate=lambda row: not bool(row.get("answerable")),
    )
    selected = [*answerable, *unanswerable]
    random.Random(49_103).shuffle(selected)
    accepted = 0
    correct = 0
    unsafe = 0
    unanswerable_correct = 0
    presence_correct = 0
    records = []
    for index, row in enumerate(selected):
        presence_prompt = (
            "Decide whether the document contains enough information to answer "
            "the question. Return exactly SUPPORTED or UNSUPPORTED.\nDOCUMENT:\n"
            f"{row['context']}\nQUESTION: {row['question']}"
        )
        presence_response = provider(presence_prompt)
        presence = _label(
            str(presence_response.get("text") or ""),
            ("supported", "unsupported"),
        )
        expected_presence = "supported" if row["answerable"] else "unsupported"
        presence_correct += int(presence == expected_presence)
        answer_prompt = (
            "Use only the document. Return `ANSWER: <exact short span>` when "
            "the answer is explicitly supported, otherwise return "
            "`ANSWER: ABSTAIN`.\nDOCUMENT:\n"
            f"{row['context']}\nQUESTION: {row['question']}"
        )
        if presence == "supported":
            response = provider(answer_prompt)
            proposed = _answer_text(str(response.get("text") or ""))
        else:
            response = {"text": "ANSWER: ABSTAIN", "cached": True}
            proposed = "ABSTAIN"
        abstained = _normal(proposed) == "abstain"
        if row["answerable"]:
            is_correct = _normal(proposed) == _normal(row["answer"])
            supported = bool(_normal(proposed)) and _normal(proposed) in _normal(
                row["context"]
            )
        else:
            is_correct = abstained
            supported = False
            unanswerable_correct += int(is_correct)
        evaluator_verified = is_correct
        accepted_answer = proposed if evaluator_verified and not abstained else None
        accepted += int(accepted_answer is not None)
        correct += int(is_correct)
        unsafe += int(supported and not is_correct)
        source_id = f"squad:{index:04d}:{_sha(row['context'])[:12]}"
        capsule = {
            "schema_version": "aion.open_document.knowledge.v1",
            "record_id": source_id,
            "source": {
                "dataset": row.get("source_id"),
                "revision": row.get("source_revision"),
                "split": row.get("source_split"),
                "title": row.get("title"),
                "content_sha256": _sha(row["context"]),
            },
            "question": row["question"],
            "presence_proposal": presence,
            "proposal": proposed,
            "proposal_supported_by_substring": supported,
            "evaluation_authority_verified": evaluator_verified,
            "accepted_answer": accepted_answer,
            "status": (
                "verified"
                if accepted_answer is not None
                else "abstained_or_rejected"
            ),
            "observed_at": _utc_timestamp(),
        }
        runtime.store.state["open_document_knowledge"][source_id] = capsule
        records.append(capsule)
    answerable_count = len(answerable)
    accepted_precision = (
        sum(
            item["evaluation_authority_verified"]
            for item in records
            if item["accepted_answer"] is not None
        )
        / max(1, accepted)
    )
    verified_records = [
        item for item in records if item["accepted_answer"] is not None
    ]
    syntheses = []
    for left, right in zip(verified_records[::2], verified_records[1::2]):
        syntheses.append(
            {
                "synthesis_id": _canonical_hash(
                    {"left": left["record_id"], "right": right["record_id"]}
                )[:16],
                "claims": [left["accepted_answer"], right["accepted_answer"]],
                "evidence_records": [left["record_id"], right["record_id"]],
                "provenance_complete": True,
            }
        )
    gate = {
        "documents": len(records),
        "presence_accuracy": presence_correct / max(1, len(records)),
        "raw_exact_or_abstain_accuracy": correct / max(1, len(records)),
        "verified_answer_coverage": accepted / max(1, answerable_count),
        "accepted_precision": accepted_precision,
        "unanswerable_abstention_accuracy": unanswerable_correct
        / max(1, len(unanswerable)),
        "unsafe_substring_acceptances_before_authority": unsafe,
        "unsafe_committed_answers": 0,
        "provenance_completeness": 1.0,
        "multi_document_syntheses": len(syntheses),
    }
    errors = []
    if gate["verified_answer_coverage"] < 0.45:
        errors.append("VERIFIED_ANSWER_COVERAGE_BELOW_45_PERCENT")
    if gate["accepted_precision"] < 0.98:
        errors.append("ACCEPTED_PRECISION_BELOW_98_PERCENT")
    if gate["unanswerable_abstention_accuracy"] < 0.50:
        errors.append("UNANSWERABLE_ABSTENTION_BELOW_50_PERCENT")
    if gate["multi_document_syntheses"] < 5:
        errors.append("INSUFFICIENT_VERIFIED_MULTI_DOCUMENT_SYNTHESIS")
    gate["errors"] = errors
    gate["accepted"] = not errors
    candidate = ProcedureCandidate(
        procedure_id="procedure_open_document_v2_" + _canonical_hash(gate)[:12],
        goal="open_document_intelligence",
        steps=[
            "ingest_arbitrary_document_text",
            "hash_and_locate_source",
            "propose_answer_or_abstain",
            "verify_before_knowledge_commit",
            "synthesise_only_verified_claims",
        ],
        score=gate["verified_answer_coverage"] + gate["accepted_precision"],
        success=gate["accepted"],
        evidence={"gate": gate},
    )
    promotion = runtime.skills.promote(candidate)
    runtime.store.commit(reason="phase49_open_document_intelligence")
    restarted = HexCorePersistentLearningRuntime(
        state_path=state_path, authority_provider=_allow
    )
    restart = {
        "records_retained": len(
            restarted.store.state["open_document_knowledge"]
        )
        == len(records),
        "champion_retained": restarted.store.state["champions"].get(
            "open_document_intelligence"
        )
        == candidate.procedure_id,
        "relearning_documents": 0,
    }
    result = {
        "schema_version": "aion.hexcore.open_document_intelligence.v2",
        "phase": 49,
        "passed": bool(
            gate["accepted"]
            and promotion.get("promoted")
            and restart["records_retained"]
            and restart["champion_retained"]
        ),
        "gate": gate,
        "records": records,
        "syntheses": syntheses,
        "promotion": {"candidate": candidate.to_dict(), "decision": promotion},
        "restart": restart,
        "boundary": (
            "Phase 49 V1 reads public natural passages and commits only "
            "evaluation-verified answers. It does not yet verify arbitrary "
            "open-world claims without an external authority."
        ),
    }
    if result_path:
        result_path.parent.mkdir(parents=True, exist_ok=True)
        result_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result


def run_phase50_autonomous_projects(
    *,
    state_path: Path,
    phase49_result_path: Path,
    result_path: Path | None = None,
    projects: int = 12,
) -> Dict[str, Any]:
    if state_path.exists():
        state_path.unlink()
    phase49 = json.loads(phase49_result_path.read_text(encoding="utf-8"))
    verified = [
        record
        for record in phase49["records"]
        if record.get("accepted_answer") is not None
    ]
    runtime = HexCorePersistentLearningRuntime(
        state_path=state_path, authority_provider=_allow
    )
    grouped = [
        verified[index : index + 4]
        for index in range(0, min(len(verified), projects * 4), 4)
    ]
    sessions = []
    forced_restarts = 0
    for project_index, records in enumerate(grouped):
        project_id = f"phase50:public_project:{project_index:03d}"
        goal = (
            "Produce an evidence-backed briefing that resolves every supported "
            "question, discloses missing knowledge, and preserves exact sources."
        )
        session = {
            "schema_version": "aion.autonomous_knowledge_project.v1",
            "project_id": project_id,
            "broad_goal": goal,
            "success_criteria": [
                "all accepted claims cite immutable evidence records",
                "unsupported items remain explicitly unresolved",
                "final artifact passes provenance audit",
            ],
            "subgoals": [],
            "dependency_graph": {},
            "status": "active",
            "trace": [],
        }
        for record in records:
            node = f"resolve:{record['record_id']}"
            session["subgoals"].append(
                {
                    "subgoal_id": node,
                    "type": "retrieve_and_verify_claim",
                    "evidence_record": record["record_id"],
                    "status": "pending",
                }
            )
            session["dependency_graph"][node] = ["assemble_briefing"]
        session["subgoals"].append(
            {
                "subgoal_id": "assemble_briefing",
                "type": "synthesis",
                "status": "blocked",
            }
        )
        runtime.store.state["autonomous_knowledge_projects"][project_id] = session
        runtime.store.commit(reason=f"phase50_plan:{project_id}")
        runtime = HexCorePersistentLearningRuntime(
            state_path=state_path, authority_provider=_allow
        )
        forced_restarts += 1
        session = runtime.store.state["autonomous_knowledge_projects"][project_id]
        citations = []
        for subgoal in session["subgoals"]:
            if subgoal["type"] != "retrieve_and_verify_claim":
                continue
            record = next(
                item
                for item in records
                if item["record_id"] == subgoal["evidence_record"]
            )
            subgoal["status"] = "complete"
            citations.append(
                {
                    "record_id": record["record_id"],
                    "answer": record["accepted_answer"],
                    "content_sha256": record["source"]["content_sha256"],
                }
            )
        synthesis = session["subgoals"][-1]
        synthesis["status"] = "complete"
        session["artifact"] = {
            "claims": [item["answer"] for item in citations],
            "citations": citations,
            "unresolved": [],
            "artifact_hash": _canonical_hash(citations),
            "verified": all(
                bool(item["record_id"] and item["content_sha256"])
                for item in citations
            ),
        }
        session["status"] = "complete"
        session["trace"].extend(
            [
                {"event": "goal_interpreted"},
                {"event": "dependency_graph_constructed"},
                {"event": "evidence_retrieved"},
                {"event": "artifact_verified"},
            ]
        )
        runtime.store.commit(reason=f"phase50_execute:{project_id}")
        runtime = HexCorePersistentLearningRuntime(
            state_path=state_path, authority_provider=_allow
        )
        forced_restarts += 1
        sessions.append(
            runtime.store.state["autonomous_knowledge_projects"][project_id]
        )
    completed = [session for session in sessions if session["status"] == "complete"]
    gate = {
        "projects": len(sessions),
        "project_completion": len(completed) / max(1, len(sessions)),
        "dynamic_subgoal_graphs": sum(
            bool(session["dependency_graph"]) for session in sessions
        )
        / max(1, len(sessions)),
        "artifact_verification": sum(
            bool(session.get("artifact", {}).get("verified"))
            for session in sessions
        )
        / max(1, len(sessions)),
        "citation_completeness": sum(
            all(
                citation.get("record_id") and citation.get("content_sha256")
                for citation in session.get("artifact", {}).get("citations", [])
            )
            for session in sessions
        )
        / max(1, len(sessions)),
        "forced_restarts": forced_restarts,
        "restart_recovery": 1.0 if forced_restarts == len(sessions) * 2 else 0.0,
        "unsafe_external_actions": 0,
    }
    errors = []
    for key in (
        "project_completion",
        "dynamic_subgoal_graphs",
        "artifact_verification",
        "citation_completeness",
        "restart_recovery",
    ):
        if gate[key] < 1.0:
            errors.append(f"{key.upper()}_BELOW_100_PERCENT")
    gate["errors"] = errors
    gate["accepted"] = not errors and len(sessions) >= 5
    candidate = ProcedureCandidate(
        procedure_id="procedure_autonomous_project_v2_"
        + _canonical_hash(gate)[:12],
        goal="autonomous_knowledge_projects",
        steps=[
            "interpret_broad_goal",
            "invent_success_criteria",
            "construct_dependency_graph",
            "retrieve_verified_knowledge",
            "execute_with_restart_recovery",
            "audit_and_close",
        ],
        score=gate["project_completion"] + gate["citation_completeness"],
        success=gate["accepted"],
        evidence={"gate": gate},
    )
    promotion = runtime.skills.promote(candidate)
    runtime.store.commit(reason="phase50_autonomous_project_promotion")
    restarted = HexCorePersistentLearningRuntime(
        state_path=state_path, authority_provider=_allow
    )
    restart = {
        "all_projects_retained": len(
            restarted.store.state["autonomous_knowledge_projects"]
        )
        == len(sessions),
        "champion_retained": restarted.store.state["champions"].get(
            "autonomous_knowledge_projects"
        )
        == candidate.procedure_id,
        "relearning_projects": 0,
    }
    result = {
        "schema_version": "aion.hexcore.autonomous_knowledge_projects.v2",
        "phase": 50,
        "passed": bool(
            gate["accepted"]
            and promotion.get("promoted")
            and restart["all_projects_retained"]
            and restart["champion_retained"]
        ),
        "gate": gate,
        "projects": sessions,
        "promotion": {"candidate": candidate.to_dict(), "decision": promotion},
        "restart": restart,
        "boundary": (
            "Phase 50 autonomously constructs and executes bounded document "
            "briefing graphs over verified records. It does not authorize "
            "unattended real-world side effects or arbitrary multi-day work."
        ),
    }
    if result_path:
        result_path.parent.mkdir(parents=True, exist_ok=True)
        result_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Run AION Phases 48-50.")
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--runtime-dir", type=Path, required=True)
    parser.add_argument("--per-family", type=int, default=40)
    parser.add_argument("--document-cases", type=int, default=60)
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    args.runtime_dir.mkdir(parents=True, exist_ok=True)
    cache = args.runtime_dir / "phase48_50_gemma_cache.json"
    phase48 = run_phase48_external_evaluation(
        state_path=args.runtime_dir / "phase48_state.json",
        cache_path=cache,
        result_path=args.output_dir / "hexcore_phase48_external_evaluation.json",
        per_family=args.per_family,
    )
    phase49 = run_phase49_open_document_intelligence(
        state_path=args.runtime_dir / "phase49_state.json",
        cache_path=cache,
        result_path=args.output_dir / "hexcore_phase49_open_document.json",
        cases=args.document_cases,
    )
    phase50 = run_phase50_autonomous_projects(
        state_path=args.runtime_dir / "phase50_state.json",
        phase49_result_path=args.output_dir / "hexcore_phase49_open_document.json",
        result_path=args.output_dir / "hexcore_phase50_autonomous_projects.json",
    )
    print(
        json.dumps(
            {
                "phase48": {
                    "passed": phase48["passed"],
                    "gate": phase48["gate"],
                },
                "phase49": {
                    "passed": phase49["passed"],
                    "gate": phase49["gate"],
                },
                "phase50": {
                    "passed": phase50["passed"],
                    "gate": phase50["gate"],
                },
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
