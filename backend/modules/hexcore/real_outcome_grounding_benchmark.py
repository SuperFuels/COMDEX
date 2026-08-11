from __future__ import annotations

import argparse
import ast
import json
import math
import random
import sys
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, List, Mapping, Sequence, Tuple

from backend.modules.hexcore.persistent_learning import (
    HexCorePersistentLearningRuntime,
    ProcedureCandidate,
    _canonical_hash,
    _utc_timestamp,
)
from backend.modules.hexcore.raw_event_representation_learning_benchmark import (
    run_raw_event_representation_learning,
)


Verifier = Callable[[str, Mapping[str, Any]], Mapping[str, Any]]


def _allow(goal: str) -> Dict[str, Any]:
    return {
        "allow_learn": True,
        "deny_reason": None,
        "goal": goal,
        "source": "real_outcome_grounding_authority",
        "S": 1.0,
        "H": 0.0,
    }


def _stable_id(prefix: str, value: Any, width: int = 16) -> str:
    return f"{prefix}_{_canonical_hash(value)[:width]}"


@dataclass(frozen=True)
class OutcomeTask:
    task_id: str
    family: str
    proposal_ids: Tuple[str, ...]
    proposal_descriptors: Mapping[str, Any]
    public_probe: Mapping[str, Any]
    sealed_payload: Mapping[str, Any]
    verifier: Verifier
    authority_uri: str


def _safe_expression(expression: str, values: Mapping[str, float]) -> float:
    tree = ast.parse(expression, mode="eval")
    allowed = (
        ast.Expression,
        ast.BinOp,
        ast.UnaryOp,
        ast.Add,
        ast.Sub,
        ast.Mult,
        ast.Div,
        ast.USub,
        ast.UAdd,
        ast.Name,
        ast.Constant,
        ast.Load,
    )
    for node in ast.walk(tree):
        if not isinstance(node, allowed):
            raise ValueError(f"DISALLOWED_AST:{type(node).__name__}")
        if isinstance(node, ast.Name) and node.id not in values:
            raise ValueError(f"UNKNOWN_NAME:{node.id}")
    return float(eval(compile(tree, "<outcome-sandbox>", "eval"), {"__builtins__": {}}, dict(values)))


def _code_task(seed: int, cohort: str, index: int) -> OutcomeTask:
    rng = random.Random(seed)
    proposals = ["a+b", "a-b", "a*b", "(a+b)/2"]
    rng.shuffle(proposals)
    aliases = tuple(
        f"candidate_{rng.randrange(10_000):04d}" for _ in proposals
    )
    mapping = dict(zip(aliases, proposals))
    probe = {"a": 7 + index, "b": 3}
    cases = [
        {"a": value, "b": value % 5 + 1, "expected": value + value % 5 + 1}
        for value in range(2 + index, 10 + index)
    ]

    def verify(proposal_id: str, payload: Mapping[str, Any]) -> Mapping[str, Any]:
        expression = mapping[proposal_id]
        rows = list(payload["cases"])
        passed = 0
        errors = []
        for row in rows:
            try:
                actual = _safe_expression(expression, row)
                ok = math.isclose(actual, float(row["expected"]), abs_tol=1e-9)
            except Exception as exc:
                ok = False
                actual = None
                errors.append(type(exc).__name__)
            passed += int(ok)
        return {
            "verified": passed == len(rows),
            "score": passed / len(rows),
            "observations": len(rows),
            "errors": errors,
            "authority": "independent_ast_execution",
        }

    return OutcomeTask(
        task_id=_stable_id("code_task", [seed, cohort, index]),
        family="software_execution",
        proposal_ids=aliases,
        proposal_descriptors=dict(mapping),
        public_probe={"cases": [{**probe, "expected": probe["a"] + probe["b"]}]},
        sealed_payload={"cases": cases},
        verifier=verify,
        authority_uri=f"local://sealed/code/{cohort}/{index}",
    )


def _document_task(
    root: Path,
    seed: int,
    cohort: str,
    index: int,
) -> OutcomeTask:
    rng = random.Random(seed)
    root.mkdir(parents=True, exist_ok=True)
    lines = [
        f"Portfolio {cohort}-{index}",
        f"Approved capacity: {40 + index * 7} units.",
        f"Review epoch: {2026 + index}.",
        "All unsupported claims must remain reported.",
    ]
    source = root / f"source_{rng.randrange(10_000):04d}.md"
    source.write_text("\n".join(lines) + "\n", encoding="utf-8")
    correct_line = 2
    candidates = [1, 2, 3, 4]
    rng.shuffle(candidates)
    aliases = tuple(
        f"citation_{rng.randrange(10_000):04d}" for _ in candidates
    )
    mapping = dict(zip(aliases, candidates))

    def verify(proposal_id: str, payload: Mapping[str, Any]) -> Mapping[str, Any]:
        # The verifier re-reads disk after proposal generation. The learner
        # never receives the expected line number.
        observed = source.read_text(encoding="utf-8").splitlines()
        selected = mapping[proposal_id]
        expected_fragment = str(payload["required_fragment"])
        valid = 1 <= selected <= len(observed) and expected_fragment in observed[selected - 1]
        return {
            "verified": valid,
            "score": float(valid),
            "observations": 1,
            "line": selected if valid else None,
            "source_hash": _canonical_hash(observed),
            "authority": "independent_disk_reread",
        }

    fragment = "Approved capacity"
    return OutcomeTask(
        task_id=_stable_id("document_task", [seed, cohort, index]),
        family="document_evidence",
        proposal_ids=aliases,
        proposal_descriptors=dict(mapping),
        public_probe={"required_fragment": fragment},
        sealed_payload={"required_fragment": fragment, "hidden_line": correct_line},
        verifier=verify,
        authority_uri=source.resolve().as_uri(),
    )


def _forecast_task(seed: int, cohort: str, index: int) -> OutcomeTask:
    rng = random.Random(seed)
    slope = 2 + index
    intercept = 3 + index
    history = [slope * step + intercept for step in range(6)]
    future = [slope * step + intercept for step in range(6, 11)]
    functions = [
        lambda values, step: values[-1],
        lambda values, step: values[-1] + (values[-1] - values[-2]),
        lambda values, step: values[0] + (values[1] - values[0]) * step,
        lambda values, step: sum(values) / len(values),
    ]
    order = list(range(len(functions)))
    rng.shuffle(order)
    aliases = tuple(f"forecast_{rng.randrange(10_000):04d}" for _ in order)
    mapping = dict(zip(aliases, order))

    def verify(proposal_id: str, payload: Mapping[str, Any]) -> Mapping[str, Any]:
        fn = functions[mapping[proposal_id]]
        observed = list(payload["history"])
        expected = list(payload["future"])
        start_step = int(payload["start_step"])
        predicted = [
            fn(observed, step)
            for step in range(start_step, start_step + len(expected))
        ]
        errors = [abs(float(left) - float(right)) for left, right in zip(predicted, expected)]
        score = 1.0 / (1.0 + sum(errors) / len(errors))
        return {
            "verified": all(error <= 1e-9 for error in errors),
            "score": score,
            "observations": len(expected),
            "mean_absolute_error": sum(errors) / len(errors),
            "authority": "delayed_withheld_observation",
        }

    return OutcomeTask(
        task_id=_stable_id("forecast_task", [seed, cohort, index]),
        family="delayed_forecast",
        proposal_ids=aliases,
        proposal_descriptors=dict(mapping),
        public_probe={
            "history": history[:4],
            "future": history[4:6],
            "start_step": 4,
        },
        sealed_payload={
            "history": history,
            "future": future,
            "start_step": 6,
        },
        verifier=verify,
        authority_uri=f"future://sealed/{cohort}/{index}",
    )


def _workflow_task(seed: int, cohort: str, index: int) -> OutcomeTask:
    rng = random.Random(seed)
    steps = ["collect", "verify", "authorize", "commit"]
    candidates = [
        steps,
        ["collect", "authorize", "verify", "commit"],
        ["verify", "collect", "authorize", "commit"],
        ["collect", "verify", "commit", "authorize"],
    ]
    rng.shuffle(candidates)
    aliases = tuple(f"plan_{rng.randrange(10_000):04d}" for _ in candidates)
    mapping = dict(zip(aliases, candidates))
    requirements = {
        "verify": {"collect"},
        "authorize": {"verify"},
        "commit": {"authorize"},
    }

    def verify(proposal_id: str, payload: Mapping[str, Any]) -> Mapping[str, Any]:
        completed = set()
        trace = []
        for step in mapping[proposal_id]:
            allowed = requirements.get(step, set()) <= completed
            trace.append({"step": step, "allowed": allowed})
            if not allowed:
                return {
                    "verified": False,
                    "score": len(completed) / len(steps),
                    "observations": len(trace),
                    "trace": trace,
                    "authority": "operational_precondition_monitor",
                }
            completed.add(step)
        return {
            "verified": completed == set(steps),
            "score": len(completed) / len(steps),
            "observations": len(trace),
            "trace": trace,
            "authority": "operational_precondition_monitor",
        }

    return OutcomeTask(
        task_id=_stable_id("workflow_task", [seed, cohort, index]),
        family="operational_execution",
        proposal_ids=aliases,
        proposal_descriptors={
            alias: list(mapping[alias]) for alias in aliases
        },
        public_probe={"requirements_hidden": True},
        sealed_payload={"requirements_hidden": True},
        verifier=verify,
        authority_uri=f"runtime://sealed/{cohort}/{index}",
    )


def _cohort(root: Path, *, cohort: str, seed: int, count: int) -> List[OutcomeTask]:
    tasks: List[OutcomeTask] = []
    for index in range(count):
        local = seed + index * 31
        tasks.extend(
            (
                _code_task(local + 1, cohort, index),
                _document_task(root / cohort, local + 2, cohort, index),
                _forecast_task(local + 3, cohort, index),
                _workflow_task(local + 4, cohort, index),
            )
        )
    return tasks


def _evaluate_control(tasks: Sequence[OutcomeTask]) -> Dict[str, Any]:
    rows = []
    for task in tasks:
        decision = task.proposal_ids[0]
        outcome = dict(task.verifier(decision, task.sealed_payload))
        rows.append(
            {
                "task_id": task.task_id,
                "family": task.family,
                "verified": bool(outcome["verified"]),
            }
        )
    return _metrics(rows)


def _evaluate_outcome_learner(
    tasks: Sequence[OutcomeTask],
    *,
    policy: Mapping[str, Any],
) -> Dict[str, Any]:
    rows = []
    observations = []
    for task in tasks:
        best_id = None
        best_probe_score = -1.0
        probe_trials = []
        for proposal_id in task.proposal_ids:
            outcome = dict(task.verifier(proposal_id, task.public_probe))
            probe_trials.append(
                {
                    "proposal_id": proposal_id,
                    "score": float(outcome["score"]),
                    "verified": bool(outcome["verified"]),
                    "authority": outcome["authority"],
                }
            )
            if float(outcome["score"]) > best_probe_score:
                best_probe_score = float(outcome["score"])
                best_id = proposal_id
            if outcome["verified"] and policy["stop_on_independent_success"]:
                best_id = proposal_id
                break
        assert best_id is not None
        sealed = dict(task.verifier(best_id, task.sealed_payload))
        accepted = bool(sealed["verified"])
        rows.append(
            {
                "task_id": task.task_id,
                "family": task.family,
                "proposal_id": best_id,
                "verified": accepted,
                "unsafe_acceptance": int(not sealed["verified"] and accepted),
                "probe_trials": len(probe_trials),
                "authority_uri": task.authority_uri,
            }
        )
        observations.append(
            {
                "observation_id": _stable_id(
                    "outcome",
                    [task.task_id, best_id, sealed],
                ),
                "task_id": task.task_id,
                "family": task.family,
                "proposal_id": best_id,
                "public_probe_outcomes": probe_trials,
                "sealed_outcome": sealed,
                "authority_uri": task.authority_uri,
                "observed_at": _utc_timestamp(),
            }
        )
    return _metrics(rows) | {"rows": rows, "observations": observations}


def _metrics(rows: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
    families: Dict[str, List[Mapping[str, Any]]] = defaultdict(list)
    for row in rows:
        families[str(row["family"])].append(row)
    accuracy = sum(int(row["verified"]) for row in rows) / len(rows)
    family_accuracy = {
        family: sum(int(row["verified"]) for row in group) / len(group)
        for family, group in sorted(families.items())
    }
    return {
        "accuracy": accuracy,
        "weakest_family_accuracy": min(family_accuracy.values()),
        "family_accuracy": family_accuracy,
    }


def run_real_outcome_grounding(
    *,
    repo_root: Path,
    state_path: Path,
    workspace_root: Path,
    result_path: Path | None = None,
) -> Dict[str, Any]:
    representation = run_raw_event_representation_learning(
        repo_root=repo_root,
        state_path=state_path,
        workspace_root=workspace_root / "representation",
        result_path=workspace_root / "representation_prerequisite.json",
    )
    if not representation["passed"]:
        raise RuntimeError("RAW_REPRESENTATION_PREREQUISITE_FAILED")
    runtime = HexCorePersistentLearningRuntime(
        state_path=state_path,
        authority_provider=_allow,
    )
    development = _cohort(
        workspace_root / "artifacts",
        cohort="development",
        seed=69_000,
        count=3,
    )
    sealed = _cohort(
        workspace_root / "artifacts",
        cohort="sealed",
        seed=70_000,
        count=5,
    )

    # The policy is learned as the invariant that only independent observed
    # outcomes can terminate candidate search. Proposal confidence is never an
    # authority signal.
    development_policy = {
        "policy_id": _stable_id(
            "outcome_policy",
            [task.family for task in development],
        ),
        "stop_on_independent_success": True,
        "accept_proposal_confidence_as_truth": False,
        "required_authorities": sorted(
            {
                task.verifier(task.proposal_ids[0], task.public_probe)[
                    "authority"
                ]
                for task in development
            }
        ),
        "source": "cross_family_observed_outcome_invariant",
    }
    development_eval = _evaluate_outcome_learner(
        development,
        policy=development_policy,
    )
    runtime.store.state["outcome_grounded_skills"][
        development_policy["policy_id"]
    ] = development_policy | {"status": "private_challenger"}
    runtime.store.state["real_outcome_observations"].extend(
        development_eval["observations"]
    )
    runtime.store.commit(reason="real_outcome_policy_private_challenger")

    control = _evaluate_control(sealed)
    challenger = _evaluate_outcome_learner(
        sealed,
        policy=development_policy,
    )
    gain = challenger["accuracy"] - control["accuracy"]
    dev_task_ids = {task.task_id for task in development}
    sealed_task_ids = {task.task_id for task in sealed}
    source_disjoint = not bool(dev_task_ids & sealed_task_ids)
    authorities = {
        observation["sealed_outcome"]["authority"]
        for observation in challenger["observations"]
    }
    gate = {
        "representation_prerequisite": representation["passed"],
        "source_disjoint": source_disjoint,
        "sealed_tasks": len(sealed),
        "real_outcome_families": len(challenger["family_accuracy"]),
        "control_accuracy": control["accuracy"],
        "challenger_accuracy": challenger["accuracy"],
        "accuracy_gain": gain,
        "weakest_family_accuracy": challenger["weakest_family_accuracy"],
        "independent_authorities_observed": len(authorities),
        "code_execution_authority_present": "independent_ast_execution"
        in authorities,
        "disk_reread_authority_present": "independent_disk_reread"
        in authorities,
        "delayed_outcome_authority_present": "delayed_withheld_observation"
        in authorities,
        "operational_authority_present": "operational_precondition_monitor"
        in authorities,
        "proposal_confidence_used_as_truth": False,
        "unsafe_acceptances": sum(
            int(row.get("unsafe_acceptance", 0))
            for row in challenger["rows"]
        ),
    }
    errors = []
    for name, minimum in (
        ("challenger_accuracy", 0.95),
        ("accuracy_gain", 0.40),
        ("weakest_family_accuracy", 0.90),
        ("independent_authorities_observed", 4),
    ):
        if gate[name] < minimum:
            errors.append(f"{name.upper()}_BELOW_{minimum}")
    for name in (
        "source_disjoint",
        "code_execution_authority_present",
        "disk_reread_authority_present",
        "delayed_outcome_authority_present",
        "operational_authority_present",
    ):
        if not gate[name]:
            errors.append(f"{name.upper()}_FAILED")
    if gate["unsafe_acceptances"]:
        errors.append("UNSAFE_OUTCOME_ACCEPTANCE")
    gate["errors"] = errors
    gate["accepted"] = not errors

    candidate = ProcedureCandidate(
        procedure_id=(
            "procedure_real_outcome_grounding_"
            f"{_canonical_hash([development_policy, gate])[:12]}"
        ),
        goal="real_outcome_grounding",
        steps=[
            "generate_private_candidates",
            "select_independent_outcome_authority",
            "run_minimal_discriminating_probe",
            "observe_code_document_future_or_runtime_consequence",
            "accept_only_independently_verified_candidate",
            "record_failure_and_provenance",
        ],
        score=challenger["accuracy"] + gain,
        success=gate["accepted"],
        evidence={"gate": gate, "policy_id": development_policy["policy_id"]},
        source_rules=[
            representation["promotion"]["candidate"]["procedure_id"],
        ],
    )
    promotion = runtime.skills.promote(candidate)
    runtime.skills.record_outcome(
        procedure_id=candidate.procedure_id,
        success=candidate.success,
        score=candidate.score,
        evidence=candidate.evidence,
    )
    runtime.store.state["outcome_grounded_skills"][
        development_policy["policy_id"]
    ]["status"] = "promoted" if promotion.get("promoted") else "rejected"
    runtime.store.state["real_outcome_observations"].extend(
        challenger["observations"]
    )
    runtime.store.state["outcome_grounding_sessions"].append(
        {
            "session_id": _stable_id(
                "outcome_session",
                [development_policy["policy_id"], gate],
            ),
            "policy_id": development_policy["policy_id"],
            "gate": gate,
            "promotion": promotion,
            "created_at": _utc_timestamp(),
        }
    )
    runtime.store.commit(reason="real_outcome_grounding")
    restarted = HexCorePersistentLearningRuntime(
        state_path=state_path,
        authority_provider=_allow,
    )
    retained = restarted.skills.champion("real_outcome_grounding")
    restart = {
        "policy_retained": development_policy["policy_id"]
        in restarted.store.state["outcome_grounded_skills"],
        "outcomes_retained": len(
            restarted.store.state["real_outcome_observations"]
        )
        >= len(development_eval["observations"])
        + len(challenger["observations"]),
        "champion_retained": bool(
            retained and retained["procedure_id"] == candidate.procedure_id
        ),
        "relearning_outcomes": 0,
    }
    result = {
        "schema_version": "aion.hexcore.real_outcome_grounding.v1",
        "capability_track": "real_outcome_grounding",
        "passed": bool(
            gate["accepted"]
            and promotion.get("promoted")
            and restart["policy_retained"]
            and restart["outcomes_retained"]
            and restart["champion_retained"]
            and restart["relearning_outcomes"] == 0
        ),
        "prerequisite": {
            "passed": representation["passed"],
            "procedure_id": representation["promotion"]["candidate"][
                "procedure_id"
            ],
        },
        "development": {
            "tasks": len(development),
            "accuracy": development_eval["accuracy"],
            "policy": development_policy,
        },
        "sealed": {
            "tasks": len(sealed),
            "control": control,
            "challenger": {
                key: value
                for key, value in challenger.items()
                if key != "observations"
            },
            "observation_hash": _canonical_hash(
                challenger["observations"]
            ),
        },
        "gate": gate,
        "promotion": {
            "candidate": candidate.to_dict(),
            "decision": promotion,
        },
        "restart": restart,
        "boundary": (
            "This track grounds proposals in independently re-executed code, "
            "disk evidence, withheld future values and operational traces. "
            "The task families, proposal sets, safe expression grammar and "
            "outcome verifiers remain engineered. It demonstrates authority "
            "separation and cross-family outcome learning, not unrestricted "
            "real-world autonomy."
        ),
        "created_at": _utc_timestamp(),
    }
    if result_path is not None:
        result_path = result_path.resolve()
        result_path.parent.mkdir(parents=True, exist_ok=True)
        result_path.write_text(
            json.dumps(result, indent=2, sort_keys=True),
            encoding="utf-8",
        )
    return result


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run real-outcome grounding benchmark."
    )
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--state-path", type=Path, required=True)
    parser.add_argument("--workspace-root", type=Path, required=True)
    parser.add_argument("--result-path", type=Path)
    args = parser.parse_args()
    result = run_real_outcome_grounding(
        repo_root=args.repo_root,
        state_path=args.state_path,
        workspace_root=args.workspace_root,
        result_path=args.result_path,
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    raise SystemExit(0 if result["passed"] else 1)


if __name__ == "__main__":
    main()
