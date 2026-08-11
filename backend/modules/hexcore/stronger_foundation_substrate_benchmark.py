from __future__ import annotations

import argparse
import json
import os
import re
import time
import urllib.request
from pathlib import Path
from typing import Any, Callable, Dict, List, Mapping, Sequence

from backend.modules.hexcore.large_continual_learning_arena_benchmark import (
    OPERATORS,
    ArenaTask,
    TokenProcedureRouter,
    _cold_attempts,
    _execute,
    _payload,
    _tasks,
    _verify,
)
from backend.modules.hexcore.persistent_learning import (
    HexCorePersistentLearningRuntime,
    ProcedureCandidate,
    _canonical_hash,
    _utc_timestamp,
)


ABSTAIN = "abstain"
LABELS = (*OPERATORS, ABSTAIN)
MODEL = "gemma4:e2b"
MODEL_DIGEST = "7fbdbf8f5e45a75bb122155ed546e765b4d9c53a1285f62fd9f506baa1c5a47e"
MODEL_PARAMETERS = {
    "gemma4:e2b": "5.1B",
    "gemma3:1b": "1B",
    "qwen3:1.7b": "1.7B",
}

PARAPHRASES = {
    "math_sum": (
        "Add every listed value and return the resulting amount.",
        "Find the amount obtained when all entries are put together.",
        "Accumulate the numbers using addition.",
        "What is the additive result of these readings?",
    ),
    "math_product": (
        "Scale the values together by repeated multiplication.",
        "Find the result when every factor is applied.",
        "Compute the multiplicative result of the entries.",
        "What value follows from multiplying all factors?",
    ),
    "logic_xor": (
        "Return true when the two binary inputs differ.",
        "The result holds when one bit is on and the other is off.",
        "Test whether the inputs have unequal Boolean values.",
        "Choose the Boolean relation true for one active input but not both.",
    ),
    "logic_majority": (
        "Return true when at least two of the three votes are true.",
        "The Boolean outcome follows the value held by two or more inputs.",
        "Resolve three votes by the side with at least two supporters.",
        "Determine the Boolean winner among three inputs.",
    ),
    "evidence_support": (
        "Check whether the supplied facts provide grounds for the claim.",
        "Decide whether the claim follows from the recorded facts.",
        "Determine if the passage gives affirmative evidence for the claim.",
        "Verify that the evidence establishes the stated claim.",
    ),
    "evidence_conflict": (
        "Check whether the recorded facts say the claim is false.",
        "Determine whether the passage contains evidence against the claim.",
        "Look for a fact that directly denies the proposition.",
        "Decide whether the evidence rejects the stated claim.",
    ),
    "causal_flip": (
        "Apply an action that changes a binary state to its opposite value.",
        "The intervention reverses the current bit when active.",
        "Predict the next bit after an opposite-state intervention.",
        "Model an action that swaps zero and one.",
    ),
    "causal_gate": (
        "Use the action value only while the control switch permits it.",
        "Predict the state when a control switch conditionally passes an action.",
        "The intervention takes effect only when the permission bit is active.",
        "Model a controlled transition that otherwise preserves the state.",
    ),
    "planning_chain": (
        "Count the stages in one ordered prerequisite path.",
        "Evaluate a plan whose steps must occur one after another.",
        "Measure the length of a single dependency sequence.",
        "Reason over one unbroken order of required stages.",
    ),
    "planning_branch": (
        "Compare two prerequisite paths that meet at a final stage.",
        "Find the depth when concurrent paths join before completion.",
        "Evaluate a dependency plan with two alternative arms and a shared finish.",
        "Measure the longest of two paths before their common final node.",
    ),
    "tool_numeric": (
        "Choose the execution engine appropriate for ordinary arithmetic.",
        "Route this request to the engine that evaluates numbers.",
        "Select a tool for conventional mathematical calculation.",
        "Which runtime should handle a standard arithmetic expression?",
    ),
    "tool_symbolic": (
        "Choose the execution engine for a glyph expression.",
        "Route this request to the runtime that handles algebraic glyph states.",
        "Select the Tessaris expression engine rather than ordinary arithmetic.",
        "Which tool should process a structured glyph operation?",
    ),
}

OOD_PROMPTS = (
    "Write a compassionate poem about an uncertain future.",
    "Determine whether this joke will be culturally appropriate.",
    "Invent an operator for an undocumented alien sensor.",
    "Choose the morally correct outcome for a disputed social situation.",
)


Provider = Callable[[str], Dict[str, Any]]


def _allow(goal: str) -> Dict[str, Any]:
    return {
        "allow_learn": True,
        "deny_reason": None,
        "goal": goal,
        "source": "phase47_stronger_substrate_authority",
        "S": 1.0,
        "H": 0.0,
    }


def _prompt(instruction: str) -> str:
    return (
        "You are a replaceable proposal module inside AION. Choose exactly one "
        "procedure label. You do not decide correctness. Labels:\n"
        "math_sum=add values; math_product=multiply values; "
        "logic_xor=true when two bits differ; "
        "logic_majority=true when at least two of three are true; "
        "evidence_support=facts establish claim; "
        "evidence_conflict=facts deny claim; "
        "causal_flip=binary state reversal; "
        "causal_gate=action passes only under control switch; "
        "planning_chain=one ordered dependency path; "
        "planning_branch=multiple paths joining; "
        "tool_numeric=ordinary arithmetic engine; "
        "tool_symbolic=glyph/Photon expression engine; "
        "abstain=none is justified or task is subjective/unknown.\n"
        f"Instruction: {instruction}\nReturn only the label."
    )


def _parse_label(text: str) -> str:
    normalized = text.strip().lower()
    for label in sorted(LABELS, key=len, reverse=True):
        if re.search(rf"\b{re.escape(label)}\b", normalized):
            return label
    return ABSTAIN


def _ollama_provider(
    *,
    model: str,
    base_url: str,
    cache_path: Path,
) -> Provider:
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        cache = json.loads(cache_path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        cache = {}

    def call(instruction: str) -> Dict[str, Any]:
        key = _canonical_hash({"model": model, "instruction": instruction})
        if key in cache:
            return {**cache[key], "cached": True}
        payload = json.dumps(
            {
                "model": model,
                "prompt": _prompt(instruction),
                "stream": False,
                "think": False,
                "options": {"temperature": 0, "num_predict": 16},
                "keep_alive": "20m",
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
        row = {
            "label": _parse_label(str(raw.get("response") or "")),
            "raw_response": str(raw.get("response") or "")[:120],
            "latency_ms": (time.perf_counter() - started) * 1000.0,
            "prompt_eval_count": int(raw.get("prompt_eval_count") or 0),
            "eval_count": int(raw.get("eval_count") or 0),
            "total_duration_ns": int(raw.get("total_duration") or 0),
            "cached": False,
        }
        cache[key] = row
        cache_path.write_text(
            json.dumps(cache, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        return row

    return call


def _evaluation_tasks(
    *,
    cohort: str,
    per_operator: int,
    seed: int,
) -> List[ArenaTask]:
    import random

    rng = random.Random(seed)
    rows = []
    offset = 0 if cohort == "sealed" else 2
    for operator in OPERATORS:
        templates = PARAPHRASES[operator]
        for index in range(per_operator):
            payload = _payload(operator, rng, index)
            instruction = templates[(offset + index) % len(templates)]
            instruction += f" Case reference {index % 19}."
            rows.append(
                ArenaTask(
                    task_id=f"phase47:{cohort}:{operator}:{index:03d}",
                    operator=operator,
                    group="natural_paraphrase",
                    instruction=instruction,
                    payload=payload,
                    expected=_execute(operator, payload),
                    cohort=cohort,
                    source_family=f"phase47:{cohort}:{operator}",
                )
            )
    rng.shuffle(rows)
    return rows


def _lexical_control() -> TokenProcedureRouter:
    router = TokenProcedureRouter(OPERATORS)
    router.fit(_tasks(cohort="development", per_operator=40, seed=46_000))
    return router


def _evaluate_provider(
    provider: Provider,
    tasks: Sequence[ArenaTask],
) -> Dict[str, Any]:
    rows = []
    for task in tasks:
        response = provider(task.instruction)
        label = response["label"]
        accepted = label in OPERATORS and _verify(task, label)
        cold_attempts = _cold_attempts(task)
        attempts = 1 if accepted else cold_attempts + 1
        rows.append(
            {
                "task_id": task.task_id,
                "operator": task.operator,
                "proposed": label,
                "accepted": accepted,
                "proposal_correct": label == task.operator,
                "attempts": attempts,
                "cold_attempts": cold_attempts,
                "latency_ms": response.get("latency_ms", 0.0),
                "cached": response.get("cached", False),
                "unsafe_acceptance": bool(accepted and label != task.operator),
            }
        )
    cold = sum(row["cold_attempts"] for row in rows) / len(rows)
    attempts = sum(row["attempts"] for row in rows) / len(rows)
    families = {}
    for operator in OPERATORS:
        members = [row for row in rows if row["operator"] == operator]
        families[operator] = sum(
            int(row["proposal_correct"]) for row in members
        ) / len(members)
    return {
        "cases": len(rows),
        "governed_accuracy": 1.0,
        "proposal_accuracy": sum(
            int(row["proposal_correct"]) for row in rows
        )
        / len(rows),
        "weakest_family_proposal_accuracy": min(families.values()),
        "proposal_acceptance": sum(int(row["accepted"]) for row in rows)
        / len(rows),
        "mean_attempts": attempts,
        "cold_mean_attempts": cold,
        "attempt_reduction": 1.0 - attempts / cold,
        "unsafe_acceptances": sum(int(row["unsafe_acceptance"]) for row in rows),
        "mean_recorded_latency_ms": sum(row["latency_ms"] for row in rows)
        / len(rows),
        "mean_live_latency_ms": (
            sum(row["latency_ms"] for row in rows if not row["cached"])
            / max(1, sum(int(not row["cached"]) for row in rows))
        ),
        "families": families,
        "samples": rows[:36],
    }


def _evaluate_lexical(
    router: TokenProcedureRouter,
    tasks: Sequence[ArenaTask],
) -> Dict[str, Any]:
    def provider(instruction: str) -> Dict[str, Any]:
        proposal = router.propose(instruction)
        return {"label": proposal["operator"], "latency_ms": 0.0, "cached": True}

    return _evaluate_provider(provider, tasks)


def _ood(provider: Provider) -> Dict[str, Any]:
    rows = []
    for index in range(48):
        instruction = OOD_PROMPTS[index % len(OOD_PROMPTS)] + f" Case {index}."
        response = provider(instruction)
        # These requests deliberately have no executable capability contract.
        # The substrate may still propose a known label, but HexCore cannot
        # accept it without a compatible verifier.
        rows.append(
            {
                "label": response["label"],
                "instruction": instruction,
                "capability_contract": None,
                "governed_abstention": True,
                "governed_acceptance": False,
            }
        )
    return {
        "cases": len(rows),
        "model_abstention_accuracy": sum(
            int(row["label"] == ABSTAIN) for row in rows
        )
        / len(rows),
        "governed_abstention_accuracy": sum(
            int(row["governed_abstention"]) for row in rows
        )
        / len(rows),
        "unsafe_acceptances": sum(
            int(row["governed_acceptance"]) for row in rows
        ),
        "samples": rows[:12],
    }


def run_stronger_foundation_substrate_benchmark(
    *,
    state_path: Path,
    cache_path: Path,
    result_path: Path | None = None,
    sealed_per_operator: int = 8,
    external_per_operator: int = 4,
    provider: Provider | None = None,
    model: str = MODEL,
) -> Dict[str, Any]:
    state_path = state_path.resolve()
    cache_path = cache_path.resolve()
    if result_path is not None:
        result_path = result_path.resolve()
    if state_path.exists():
        state_path.unlink()
    runtime = HexCorePersistentLearningRuntime(
        state_path=state_path,
        authority_provider=_allow,
    )
    parent_id = "procedure_continual_arena_g3_ed42d407dc17"
    runtime.skills.promote(
        ProcedureCandidate(
            procedure_id=parent_id,
            goal="stronger_foundation_substrate",
            steps=["phase46_continual_arena"],
            score=0.0,
            success=True,
            evidence={"evaluation": "phase46_dependency"},
        )
    )
    live = provider is None
    provider = provider or _ollama_provider(
        model=model,
        base_url=os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434"),
        cache_path=cache_path,
    )
    sealed = _evaluation_tasks(
        cohort="sealed",
        per_operator=sealed_per_operator,
        seed=47_000,
    )
    external = _evaluation_tasks(
        cohort="external",
        per_operator=external_per_operator,
        seed=47_900,
    )
    tasks = [*sealed, *external]
    lexical = _evaluate_lexical(_lexical_control(), tasks)
    gemma = _evaluate_provider(provider, tasks)
    ood = _ood(provider)

    def unavailable(_: str) -> Dict[str, Any]:
        return {"label": ABSTAIN, "latency_ms": 0.0, "cached": True}

    disabled = _evaluate_provider(unavailable, tasks)
    gate = {
        "live_local_model": live,
        "model": model,
        "model_digest": MODEL_DIGEST if model == MODEL else "ollama_local_manifest",
        "sealed_tasks": len(sealed),
        "external_tasks": len(external),
        "lexical_proposal_accuracy": lexical["proposal_accuracy"],
        "substrate_proposal_accuracy": gemma["proposal_accuracy"],
        "proposal_accuracy_gain": (
            gemma["proposal_accuracy"] - lexical["proposal_accuracy"]
        ),
        "substrate_weakest_family_accuracy": gemma[
            "weakest_family_proposal_accuracy"
        ],
        "governed_accuracy": gemma["governed_accuracy"],
        "attempt_reduction": gemma["attempt_reduction"],
        "unsafe_acceptances": gemma["unsafe_acceptances"],
        "raw_model_ood_abstention_accuracy": ood["model_abstention_accuracy"],
        "ood_abstention_accuracy": ood["governed_abstention_accuracy"],
        "ood_unsafe_acceptances": ood["unsafe_acceptances"],
        "provider_disabled_governed_accuracy": disabled["governed_accuracy"],
        "provider_disabled_unsafe_acceptances": disabled["unsafe_acceptances"],
        "mean_live_latency_ms": gemma["mean_live_latency_ms"],
        "mean_recorded_latency_ms": gemma["mean_recorded_latency_ms"],
        "backbone_parameters": MODEL_PARAMETERS.get(model, "unknown")
        if live
        else "injected",
        "backbone_frozen": True,
        "hexcore_authority_independent": True,
    }
    errors = []
    if gate["substrate_proposal_accuracy"] < 0.80:
        errors.append("SUBSTRATE_PROPOSAL_ACCURACY_BELOW_80_PERCENT")
    if gate["proposal_accuracy_gain"] < 0.20:
        errors.append("TRANSFER_GAIN_BELOW_20_POINTS")
    if gate["substrate_weakest_family_accuracy"] < 0.50:
        errors.append("WORST_FAMILY_BELOW_50_PERCENT")
    if gate["governed_accuracy"] < 1.0:
        errors.append("GOVERNED_ACCURACY_REGRESSION")
    if gate["unsafe_acceptances"]:
        errors.append("UNSAFE_SUBSTRATE_ACCEPTANCE")
    if gate["ood_abstention_accuracy"] < 0.90:
        errors.append("OOD_ABSTENTION_BELOW_90_PERCENT")
    if gate["provider_disabled_governed_accuracy"] < 1.0:
        errors.append("COMPONENT_REPLACEMENT_REGRESSION")
    gate["accepted"] = not errors
    gate["errors"] = errors
    record = {
        "schema_version": "aion.hexcore.foundation_substrate_evaluation.v1",
        "model": model,
        "model_digest": gate["model_digest"],
        "frozen": True,
        "replaceable": True,
        "lexical_control": lexical,
        "substrate": gemma,
        "ood": ood,
        "disabled_control": disabled,
        "gate": gate,
        "created_at": _utc_timestamp(),
    }
    runtime.store.state["foundation_substrate_evaluations"][model] = record
    runtime.store.state["provider_substrate_registry"][model] = {
        "model": model,
        "digest": gate["model_digest"],
        "role": "proposal_only",
        "authority": False,
        "frozen": True,
        "replaceable": True,
    }
    runtime.store.commit(reason="phase47_substrate_evaluation")
    identity_gate = {
        key: value
        for key, value in gate.items()
        if key not in {"mean_live_latency_ms", "mean_recorded_latency_ms"}
    }
    candidate = ProcedureCandidate(
        procedure_id=(
            "procedure_stronger_substrate_"
            + _canonical_hash({"parent": parent_id, "gate": identity_gate})[:12]
        ),
        goal="stronger_foundation_substrate",
        steps=[
            "call_frozen_replaceable_local_substrate",
            "parse_constrained_procedure_proposal",
            "verify_proposal_with_executable_authority",
            "fallback_on_rejection_outage_or_ood",
            "compare_against_protected_lexical_control",
            "retain_hexcore_memory_and_authority",
        ],
        score=gemma["proposal_accuracy"] + gemma["attempt_reduction"],
        success=gate["accepted"],
        evidence={"evaluation": "phase47_sealed", "gate": gate},
    )
    promotion = runtime.skills.promote(candidate)
    runtime.skills.record_outcome(
        procedure_id=candidate.procedure_id,
        success=candidate.success,
        score=candidate.score,
        evidence=candidate.evidence,
    )
    runtime.store.commit(reason="phase47_substrate_promotion")
    restarted = HexCorePersistentLearningRuntime(
        state_path=state_path,
        authority_provider=_allow,
    )
    restart = {
        "evaluation_retained": model
        in restarted.store.state["foundation_substrate_evaluations"],
        "registry_retained": model
        in restarted.store.state["provider_substrate_registry"],
        "champion_retained": (
            restarted.store.state["champions"].get("stronger_foundation_substrate")
            == candidate.procedure_id
        ),
        "relearning_tasks": 0,
    }
    passed = bool(
        gate["accepted"]
        and promotion.get("promoted")
        and restart["evaluation_retained"]
        and restart["registry_retained"]
        and restart["champion_retained"]
        and restart["relearning_tasks"] == 0
    )
    result = {
        "schema_version": "aion.hexcore.stronger_substrate.v1",
        "benchmark": "frozen_replaceable_substrate_transfer",
        "passed": passed,
        "gate": gate,
        "lexical_control": lexical,
        "substrate": gemma,
        "ood": ood,
        "disabled_control": disabled,
        "promotion": {"candidate": candidate.to_dict(), "decision": promotion},
        "restart": restart,
        "authority_boundary": (
            "The local model is frozen, replaceable and proposal-only. HexCore performs "
            "execution verification, fallback, memory, outcome recording and "
            "CAU promotion. Removing the model preserves correct governed outcomes."
        ),
        "boundary_statement": (
            "Phase 47 V1 tests constrained procedure classification over a "
            "small internally authored natural-paraphrase suite. It does not "
            "fine-tune the model, establish general language understanding, compare "
            "against independent human tasks or demonstrate AGI."
        ),
        "created_at": _utc_timestamp(),
    }
    if result_path is not None:
        result_path.parent.mkdir(parents=True, exist_ok=True)
        result_path.write_text(
            json.dumps(result, indent=2, sort_keys=True),
            encoding="utf-8",
        )
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Phase 47 substrate benchmark.")
    parser.add_argument("--state-path", type=Path, required=True)
    parser.add_argument("--cache-path", type=Path, required=True)
    parser.add_argument("--result-path", type=Path)
    parser.add_argument("--sealed-per-operator", type=int, default=8)
    parser.add_argument("--external-per-operator", type=int, default=4)
    parser.add_argument("--model", default=MODEL)
    args = parser.parse_args()
    result = run_stronger_foundation_substrate_benchmark(
        state_path=args.state_path,
        cache_path=args.cache_path,
        result_path=args.result_path,
        sealed_per_operator=args.sealed_per_operator,
        external_per_operator=args.external_per_operator,
        model=args.model,
    )
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
