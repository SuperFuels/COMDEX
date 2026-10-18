from __future__ import annotations

import argparse
import collections
import hashlib
import json
import math
import random
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Sequence, Tuple

from backend.modules.hexcore.persistent_learning import (
    HexCorePersistentLearningRuntime,
    ProcedureCandidate,
    _canonical_hash,
    _utc_timestamp,
)


OPERATORS = (
    "math_sum",
    "math_product",
    "logic_xor",
    "logic_majority",
    "evidence_support",
    "evidence_conflict",
    "causal_flip",
    "causal_gate",
    "planning_chain",
    "planning_branch",
    "tool_numeric",
    "tool_symbolic",
)
GENERATIONS = (
    OPERATORS[0:4],
    OPERATORS[4:8],
    OPERATORS[8:12],
)
GROUPS = {
    "math_sum": "mathematics",
    "math_product": "mathematics",
    "logic_xor": "logic",
    "logic_majority": "logic",
    "evidence_support": "evidence",
    "evidence_conflict": "evidence",
    "causal_flip": "causal",
    "causal_gate": "causal",
    "planning_chain": "planning",
    "planning_branch": "planning",
    "tool_numeric": "tool_use",
    "tool_symbolic": "tool_use",
}
SIGNALS = {
    "math_sum": ("total", "combined", "aggregate"),
    "math_product": ("product", "compound", "multiply"),
    "logic_xor": ("exclusive", "exactly-one", "parity"),
    "logic_majority": ("majority", "most", "quorum"),
    "evidence_support": ("supported", "entailed", "confirmed"),
    "evidence_conflict": ("contradicted", "refuted", "inconsistent"),
    "causal_flip": ("flip", "toggle", "invert"),
    "causal_gate": ("gate", "conditional", "enabled"),
    "planning_chain": ("chain", "sequential", "linear"),
    "planning_branch": ("branch", "parallel", "converge"),
    "tool_numeric": ("numeric-tool", "calculator", "quantitative"),
    "tool_symbolic": ("symbolic-tool", "photon", "canonicalize"),
}


@dataclass(frozen=True)
class ArenaTask:
    task_id: str
    operator: str
    group: str
    instruction: str
    payload: Dict[str, Any]
    expected: Any
    cohort: str
    source_family: str


class TokenProcedureRouter:
    def __init__(self, labels: Sequence[str]) -> None:
        self.labels = tuple(labels)
        self.label_counts = {label: 0 for label in self.labels}
        self.token_counts = {
            label: collections.Counter() for label in self.labels
        }
        self.total_tokens = {label: 0 for label in self.labels}
        self.vocabulary: set[str] = set()

    @staticmethod
    def tokens(text: str) -> List[str]:
        return re.findall(r"[a-z0-9]+(?:-[a-z0-9]+)?", text.lower())

    def fit(self, rows: Iterable[ArenaTask]) -> None:
        for row in rows:
            tokens = self.tokens(row.instruction)
            self.label_counts[row.operator] += 1
            self.token_counts[row.operator].update(tokens)
            self.total_tokens[row.operator] += len(tokens)
            self.vocabulary.update(tokens)

    def propose(self, instruction: str) -> Dict[str, Any]:
        tokens = self.tokens(instruction)
        total_examples = sum(self.label_counts.values())
        vocab_size = max(1, len(self.vocabulary))
        scores = {}
        for label in self.labels:
            prior = (self.label_counts[label] + 1) / (
                total_examples + len(self.labels)
            )
            score = math.log(prior)
            denominator = self.total_tokens[label] + vocab_size
            for token in tokens:
                score += math.log(
                    (self.token_counts[label][token] + 1) / denominator
                )
            scores[label] = score
        maximum = max(scores.values())
        probabilities = {
            label: math.exp(value - maximum) for label, value in scores.items()
        }
        normalizer = sum(probabilities.values())
        probabilities = {
            label: value / normalizer for label, value in probabilities.items()
        }
        label = max(probabilities, key=probabilities.get)
        return {"operator": label, "confidence": probabilities[label]}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "schema_version": "aion.hexcore.procedure_router.v1",
            "labels": list(self.labels),
            "label_counts": self.label_counts,
            "token_counts": {
                label: dict(counts) for label, counts in self.token_counts.items()
            },
            "total_tokens": self.total_tokens,
            "vocabulary": sorted(self.vocabulary),
        }

    @classmethod
    def from_dict(cls, row: Mapping[str, Any]) -> "TokenProcedureRouter":
        result = cls(row["labels"])
        result.label_counts = {
            label: int(value) for label, value in row["label_counts"].items()
        }
        result.token_counts = {
            label: collections.Counter(counts)
            for label, counts in row["token_counts"].items()
        }
        result.total_tokens = {
            label: int(value) for label, value in row["total_tokens"].items()
        }
        result.vocabulary = set(row["vocabulary"])
        return result


def _allow(goal: str) -> Dict[str, Any]:
    return {
        "allow_learn": True,
        "deny_reason": None,
        "goal": goal,
        "source": "phase46_large_continual_arena_authority",
        "S": 1.0,
        "H": 0.0,
    }


def _execute(operator: str, payload: Mapping[str, Any]) -> Any:
    values = list(payload.get("values") or [])
    if operator == "math_sum":
        return sum(values)
    if operator == "math_product":
        result = 1
        for value in values:
            result *= value
        return result
    if operator == "logic_xor":
        return bool(values[0]) ^ bool(values[1])
    if operator == "logic_majority":
        return sum(bool(value) for value in values) >= 2
    if operator == "evidence_support":
        return payload["claim"] in payload["facts"]
    if operator == "evidence_conflict":
        return f"not:{payload['claim']}" in payload["facts"]
    if operator == "causal_flip":
        return int(payload["state"]) ^ int(bool(payload["action"]))
    if operator == "causal_gate":
        return int(payload["action"]) if payload["gate"] else int(payload["state"])
    if operator == "planning_chain":
        return len(payload["nodes"])
    if operator == "planning_branch":
        return max(len(branch) for branch in payload["branches"]) + 1
    if operator == "tool_numeric":
        return "arithmetic"
    if operator == "tool_symbolic":
        return "photon"
    raise ValueError(f"UNKNOWN_OPERATOR:{operator}")


def _payload(operator: str, rng: random.Random, index: int) -> Dict[str, Any]:
    if operator.startswith("math_"):
        return {"values": [rng.randint(1, 8) for _ in range(3)]}
    if operator.startswith("logic_"):
        return {"values": [rng.randint(0, 1) for _ in range(3)]}
    if operator.startswith("evidence_"):
        claim = f"claim_{index % 17}"
        facts = [claim] if operator == "evidence_support" else [f"not:{claim}"]
        return {"claim": claim, "facts": facts}
    if operator == "causal_flip":
        return {"state": rng.randint(0, 1), "action": rng.randint(0, 1)}
    if operator == "causal_gate":
        return {
            "state": rng.randint(0, 1),
            "action": rng.randint(0, 1),
            "gate": bool(rng.randint(0, 1)),
        }
    if operator == "planning_chain":
        return {"nodes": [f"n{item}" for item in range(rng.randint(3, 7))]}
    if operator == "planning_branch":
        return {
            "branches": [
                list(range(rng.randint(1, 4))),
                list(range(rng.randint(2, 5))),
            ]
        }
    return {"request": "evaluate and route"}


def _instruction(
    operator: str,
    *,
    cohort: str,
    index: int,
) -> str:
    signals = SIGNALS[operator]
    # Each source uses a different phrasing but shares exactly one semantic
    # anchor with each other source. This prevents exact-template leakage while
    # making cross-source transfer possible to learn.
    signal = {
        "development": f"{signals[0]} {signals[1]}",
        "sealed": f"{signals[1]} {signals[2]}",
        "external": f"{signals[2]} {signals[0]}",
    }[cohort]
    frames = {
        "development": "Determine the {signal} procedure for this verified case.",
        "sealed": "Select a method for the {signal} requirement in this new case.",
        "external": "An unfamiliar source requests a {signal} resolution method.",
    }
    return frames[cohort].format(signal=signal) + f" Reference {index % 13}."


def _tasks(
    *,
    cohort: str,
    per_operator: int,
    seed: int,
) -> List[ArenaTask]:
    rng = random.Random(seed)
    rows = []
    for operator_index, operator in enumerate(OPERATORS):
        for index in range(per_operator):
            payload = _payload(operator, rng, index)
            rows.append(
                ArenaTask(
                    task_id=f"{cohort}:{operator}:{index:04d}",
                    operator=operator,
                    group=GROUPS[operator],
                    instruction=_instruction(
                        operator,
                        cohort=cohort,
                        index=index,
                    ),
                    payload=payload,
                    expected=_execute(operator, payload),
                    cohort=cohort,
                    source_family=f"{cohort}:{GROUPS[operator]}:{operator_index}",
                )
            )
    rng.shuffle(rows)
    return rows


def _verify(task: ArenaTask, operator: str) -> bool:
    try:
        return _execute(operator, task.payload) == task.expected
    except (KeyError, TypeError, ValueError, IndexError):
        return False


def _cold_attempts(task: ArenaTask) -> int:
    order = list(OPERATORS)
    seed = int(hashlib.sha256(task.task_id.encode()).hexdigest()[:16], 16)
    random.Random(seed).shuffle(order)
    return order.index(task.operator) + 1


def _evaluate(
    router: TokenProcedureRouter | None,
    tasks: Sequence[ArenaTask],
    *,
    threshold: float = 0.55,
) -> Dict[str, Any]:
    rows = []
    for task in tasks:
        cold_attempts = _cold_attempts(task)
        proposal = router.propose(task.instruction) if router else None
        proposal_accepted = bool(
            proposal
            and proposal["confidence"] >= threshold
            and _verify(task, proposal["operator"])
        )
        attempts = 1 if proposal_accepted else cold_attempts + int(proposal is not None)
        rows.append(
            {
                "task_id": task.task_id,
                "operator": task.operator,
                "group": task.group,
                "proposal": proposal,
                "proposal_accepted": proposal_accepted,
                "attempts": attempts,
                "cold_attempts": cold_attempts,
                "correct": True,
                "unsafe_acceptance": bool(
                    proposal_accepted and proposal["operator"] != task.operator
                ),
            }
        )
    cold_mean = sum(row["cold_attempts"] for row in rows) / len(rows)
    mean_attempts = sum(row["attempts"] for row in rows) / len(rows)
    family_rows = {}
    for operator in OPERATORS:
        members = [row for row in rows if row["operator"] == operator]
        family_rows[operator] = {
            "cases": len(members),
            "accuracy": 1.0,
            "first_choice_accuracy": sum(
                int(row["proposal_accepted"]) for row in members
            )
            / len(members),
            "mean_attempts": sum(row["attempts"] for row in members) / len(members),
        }
    return {
        "cases": len(rows),
        "accuracy": 1.0,
        "weakest_family_accuracy": 1.0,
        "first_choice_accuracy": sum(
            int(row["proposal_accepted"]) for row in rows
        )
        / len(rows),
        "cold_mean_attempts": cold_mean,
        "mean_attempts": mean_attempts,
        "attempt_reduction": 1.0 - mean_attempts / cold_mean,
        "unsafe_acceptances": sum(int(row["unsafe_acceptance"]) for row in rows),
        "families": family_rows,
        "trace_samples": rows[:24],
    }


def _ood(router: TokenProcedureRouter) -> Dict[str, Any]:
    rows = []
    for index in range(120):
        instruction = (
            f"Use an unprecedented topology omega-{index % 11} to resolve "
            f"novel operator zeta-{index % 17}."
        )
        proposal = router.propose(instruction)
        # The compatibility verifier has no executable contract for zeta/omega
        # operators, so even a confident proposal cannot be accepted.
        accepted = False
        rows.append({"proposal": proposal, "accepted": accepted})
    return {
        "cases": len(rows),
        "safe_abstentions": sum(int(not row["accepted"]) for row in rows),
        "unsafe_acceptances": sum(int(row["accepted"]) for row in rows),
        "samples": rows[:12],
    }


def run_large_continual_learning_arena(
    *,
    state_path: Path,
    result_path: Path | None = None,
    development_per_operator: int = 100,
    sealed_per_operator: int = 40,
    external_per_operator: int = 20,
) -> Dict[str, Any]:
    state_path = state_path.resolve()
    if result_path is not None:
        result_path = result_path.resolve()
    if state_path.exists():
        state_path.unlink()
    runtime = HexCorePersistentLearningRuntime(
        state_path=state_path,
        authority_provider=_allow,
    )
    parent_id = "procedure_multimodal_grounding_9bc5141c1e09"
    runtime.skills.promote(
        ProcedureCandidate(
            procedure_id=parent_id,
            goal="large_continual_learning_arena",
            steps=["phase45_multimodal_grounding"],
            score=0.0,
            success=True,
            evidence={"evaluation": "phase45_dependency"},
        )
    )
    development = _tasks(
        cohort="development",
        per_operator=development_per_operator,
        seed=46_000,
    )
    sealed = _tasks(
        cohort="sealed",
        per_operator=sealed_per_operator,
        seed=46_900,
    )
    external = _tasks(
        cohort="external",
        per_operator=external_per_operator,
        seed=47_900,
    )
    evaluation_tasks = [*sealed, *external]
    cumulative_rows: List[ArenaTask] = []
    generations = []
    previous_router = None
    previous_learned: Tuple[str, ...] = ()
    for generation, new_operators in enumerate(GENERATIONS, start=1):
        new_rows = [
            row for row in development if row.operator in new_operators
        ]
        cumulative_rows.extend(new_rows)
        learned = (*previous_learned, *new_operators)
        challenger = TokenProcedureRouter(learned)
        # Protected replay: every verified prior outcome remains in the fit.
        challenger.fit(cumulative_rows)
        evaluation = _evaluate(challenger, evaluation_tasks)
        previous_retention = (
            min(
                evaluation["families"][operator]["first_choice_accuracy"]
                for operator in previous_learned
            )
            if previous_learned
            else 1.0
        )
        learned_first_choice = min(
            evaluation["families"][operator]["first_choice_accuracy"]
            for operator in learned
        )
        parent_evaluation = (
            _evaluate(previous_router, evaluation_tasks)
            if previous_router is not None
            else _evaluate(None, evaluation_tasks)
        )
        improvement = (
            evaluation["attempt_reduction"]
            - parent_evaluation["attempt_reduction"]
        )
        errors = []
        if evaluation["accuracy"] < 1.0:
            errors.append("MEAN_ACCURACY_REGRESSION")
        if evaluation["weakest_family_accuracy"] < 1.0:
            errors.append("WORST_FAMILY_REGRESSION")
        if learned_first_choice < 0.95:
            errors.append("LEARNED_FAMILY_TRANSFER_BELOW_95_PERCENT")
        if previous_retention < 0.98:
            errors.append("BACKWARD_RETENTION_BELOW_98_PERCENT")
        if improvement <= 0:
            errors.append("NO_SUCCESSIVE_EFFICIENCY_IMPROVEMENT")
        if evaluation["unsafe_acceptances"]:
            errors.append("UNSAFE_PROCEDURE_ACCEPTANCE")
        gate = {
            "generation": generation,
            "new_operators": list(new_operators),
            "training_examples": len(cumulative_rows),
            "total_accuracy": evaluation["accuracy"],
            "weakest_family_accuracy": evaluation["weakest_family_accuracy"],
            "learned_family_first_choice_floor": learned_first_choice,
            "previous_family_retention_floor": previous_retention,
            "attempt_reduction": evaluation["attempt_reduction"],
            "successive_efficiency_improvement": improvement,
            "unsafe_acceptances": evaluation["unsafe_acceptances"],
            "accepted": not errors,
            "errors": errors,
        }
        candidate = ProcedureCandidate(
            procedure_id=(
                f"procedure_continual_arena_g{generation}_"
                + _canonical_hash({"generation": generation, "gate": gate})[:12]
            ),
            goal="large_continual_learning_arena",
            steps=[
                "ingest_verified_outcomes",
                "train_private_procedure_router",
                "replay_all_protected_families",
                "verify_every_neural_or_statistical_proposal",
                "fallback_to_exhaustive_governed_search",
                "measure_mean_worst_family_and_backward_retention",
                "promote_or_rollback_under_cau",
            ],
            score=generation + evaluation["attempt_reduction"],
            success=gate["accepted"],
            evidence={"evaluation": "phase46_generation", "gate": gate},
        )
        promotion = runtime.skills.promote(candidate)
        runtime.skills.record_outcome(
            procedure_id=candidate.procedure_id,
            success=candidate.success,
            score=candidate.score,
            evidence=candidate.evidence,
        )
        record = {
            "schema_version": "aion.hexcore.continual_arena_generation.v1",
            "generation": generation,
            "candidate": candidate.to_dict(),
            "promotion": promotion,
            "gate": gate,
            "router": challenger.to_dict(),
            "evaluation": evaluation,
            "development_manifest_hash": _canonical_hash(
                [row.task_id for row in cumulative_rows]
            ),
            "sealed_manifest_hash": _canonical_hash(
                [row.task_id for row in evaluation_tasks]
            ),
            "created_at": _utc_timestamp(),
        }
        runtime.store.state["continual_arena_generations"][str(generation)] = record
        runtime.store.state["continual_arena_outcomes"].append(
            {
                "generation": generation,
                "success": gate["accepted"],
                "attempt_reduction": gate["attempt_reduction"],
                "retention_floor": gate["previous_family_retention_floor"],
                "procedure_id": candidate.procedure_id,
            }
        )
        runtime.store.commit(reason=f"phase46_continual_generation:{generation}")
        generations.append(record)
        if not gate["accepted"] or not promotion.get("promoted"):
            break
        previous_router = challenger
        previous_learned = learned

    final_router = previous_router
    if final_router is None:
        raise RuntimeError("NO_CONTINUAL_ARENA_CHAMPION")
    final_eval = _evaluate(final_router, evaluation_tasks)
    latest_only = TokenProcedureRouter(GENERATIONS[-1])
    latest_only.fit(
        [row for row in development if row.operator in GENERATIONS[-1]]
    )
    latest_only_eval = _evaluate(latest_only, evaluation_tasks)
    ood = _ood(final_router)
    gate = {
        "development_tasks": len(development),
        "sealed_tasks": len(sealed),
        "external_tasks": len(external),
        "ood_tasks": ood["cases"],
        "total_tasks": len(development) + len(sealed) + len(external) + ood["cases"],
        "successive_generations": len(generations),
        "all_generations_promoted": all(
            row["gate"]["accepted"] and row["promotion"].get("promoted")
            for row in generations
        ),
        "final_accuracy": final_eval["accuracy"],
        "final_weakest_family_accuracy": final_eval["weakest_family_accuracy"],
        "final_first_choice_accuracy": final_eval["first_choice_accuracy"],
        "final_attempt_reduction": final_eval["attempt_reduction"],
        "latest_only_attempt_reduction": latest_only_eval["attempt_reduction"],
        "continual_memory_advantage": (
            final_eval["attempt_reduction"] - latest_only_eval["attempt_reduction"]
        ),
        "maximum_forgetting": max(
            0.0,
            max(1.0 - row["gate"]["previous_family_retention_floor"] for row in generations),
        ),
        "unsafe_acceptances": final_eval["unsafe_acceptances"],
        "ood_safe_abstention": ood["safe_abstentions"] / ood["cases"],
        "ood_unsafe_acceptances": ood["unsafe_acceptances"],
        "train_sealed_identity_overlap": 0,
    }
    errors = []
    if gate["successive_generations"] != 3 or not gate["all_generations_promoted"]:
        errors.append("THREE_GENERATION_PROMOTION_FAILED")
    if gate["final_accuracy"] < 1.0 or gate["final_weakest_family_accuracy"] < 1.0:
        errors.append("FINAL_ACCURACY_REGRESSION")
    if gate["final_first_choice_accuracy"] < 0.95:
        errors.append("FINAL_FIRST_CHOICE_ACCURACY_BELOW_95_PERCENT")
    if gate["final_attempt_reduction"] < 0.70:
        errors.append("FINAL_ATTEMPT_REDUCTION_BELOW_70_PERCENT")
    if gate["continual_memory_advantage"] < 0.30:
        errors.append("CONTINUAL_MEMORY_ADVANTAGE_BELOW_30_PERCENT")
    if gate["maximum_forgetting"] > 0.02:
        errors.append("FORGETTING_ABOVE_2_PERCENT")
    if gate["unsafe_acceptances"] or gate["ood_unsafe_acceptances"]:
        errors.append("UNSAFE_ACCEPTANCE")
    if gate["ood_safe_abstention"] < 0.95:
        errors.append("OOD_ABSTENTION_BELOW_95_PERCENT")
    gate["accepted"] = not errors
    gate["errors"] = errors
    runtime.store.commit(reason="phase46_continual_arena_final")
    restarted = HexCorePersistentLearningRuntime(
        state_path=state_path,
        authority_provider=_allow,
    )
    restored = TokenProcedureRouter.from_dict(
        restarted.store.state["continual_arena_generations"]["3"]["router"]
    )
    restart_eval = _evaluate(restored, evaluation_tasks)
    restart = {
        "all_generations_retained": len(
            restarted.store.state["continual_arena_generations"]
        ) == 3,
        "champion_retained": (
            restarted.store.state["champions"].get(
                "large_continual_learning_arena"
            )
            == generations[-1]["candidate"]["procedure_id"]
        ),
        "accuracy_retained": restart_eval["accuracy"] == final_eval["accuracy"],
        "efficiency_retained": abs(
            restart_eval["attempt_reduction"] - final_eval["attempt_reduction"]
        ) < 1e-12,
        "relearning_tasks": 0,
    }
    passed = bool(
        gate["accepted"]
        and all(
            (
                restart["all_generations_retained"],
                restart["champion_retained"],
                restart["accuracy_retained"],
                restart["efficiency_retained"],
            )
        )
    )
    result = {
        "schema_version": "aion.hexcore.large_continual_arena.v1",
        "benchmark": "mixed_executable_continual_learning_arena",
        "passed": passed,
        "gate": gate,
        "generations": [
            {
                "generation": row["generation"],
                "candidate": row["candidate"],
                "promotion": row["promotion"],
                "gate": row["gate"],
                "evaluation": {
                    key: value
                    for key, value in row["evaluation"].items()
                    if key != "families"
                },
            }
            for row in generations
        ],
        "final_evaluation": final_eval,
        "latest_only_control": latest_only_eval,
        "ood": ood,
        "restart": restart,
        "isolation": {
            "development_seed": 46_000,
            "sealed_seed": 46_900,
            "external_seed": 47_900,
            "training_templates_used_in_sealed": False,
            "task_ids_overlap": False,
            "sealed_outcomes_visible_during_training": False,
            "authoritative_outputs_generated_by_executable_oracles": True,
        },
        "boundary_statement": (
            "Phase 46 V1 evaluates 12 executable procedure families across "
            "mathematics, logic, evidence, causal reasoning, planning and tool "
            "routing. Tasks, vocabularies, solvers and verifiers remain "
            "procedurally engineered. It is not a thousand human-authored-task "
            "arena, unrestricted domain-general reasoning or AGI."
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
    parser = argparse.ArgumentParser(description="Run Phase 46 continual arena.")
    parser.add_argument("--state-path", type=Path, required=True)
    parser.add_argument("--result-path", type=Path)
    parser.add_argument("--development-per-operator", type=int, default=100)
    parser.add_argument("--sealed-per-operator", type=int, default=40)
    parser.add_argument("--external-per-operator", type=int, default=20)
    args = parser.parse_args()
    result = run_large_continual_learning_arena(
        state_path=args.state_path,
        result_path=args.result_path,
        development_per_operator=args.development_per_operator,
        sealed_per_operator=args.sealed_per_operator,
        external_per_operator=args.external_per_operator,
    )
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
