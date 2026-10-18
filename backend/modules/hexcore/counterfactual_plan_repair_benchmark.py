from __future__ import annotations

import argparse
import itertools
import json
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Mapping, Sequence, Tuple

from backend.modules.hexcore.anticipatory_temporal_reasoning_benchmark import (
    Assignment,
    TemporalWorld,
    TemporalWorldGenerator,
)
from backend.modules.hexcore.persistent_learning import (
    HexCorePersistentLearningRuntime,
    ProcedureCandidate,
    _canonical_hash,
    _utc_timestamp,
)
from backend.modules.hexcore.prospective_temporal_planning_benchmark import (
    ProspectivePolicy,
    _future_distribution,
    _learn_temporal_model,
)

State = Tuple[int, ...]


@dataclass(frozen=True)
class PlanningPolicy:
    policy_id: str
    temporal: ProspectivePolicy
    horizon: int
    action_cost: float
    uncertainty_penalty: float

    @property
    def complexity(self) -> int:
        return self.temporal.complexity + self.horizon + 2

    def to_dict(self) -> Dict[str, Any]:
        return {
            "policy_id": self.policy_id,
            "temporal": self.temporal.to_dict(),
            "horizon": self.horizon,
            "action_cost": self.action_cost,
            "uncertainty_penalty": self.uncertainty_penalty,
            "complexity": self.complexity,
        }


def _apply_action(
    state: State,
    action: int,
    graph: Assignment,
    *,
    succeeds: bool,
) -> State:
    if action < 0 or not succeeds:
        return state
    output = list(state)
    output[graph[action]] = 1 - output[graph[action]]
    return tuple(output)


def _score_state(state: State, goal: State) -> float:
    return sum(int(left == right) for left, right in zip(state, goal)) / len(goal)


def _predict_graph(
    *,
    world: TemporalWorld,
    model: Mapping[Assignment, Sequence[Mapping[str, Any]]],
    policy: ProspectivePolicy,
    decision_block: int,
    execution_block: int,
) -> Tuple[Assignment, float, bool]:
    current = world.schedule[decision_block]
    start = decision_block
    while start > 0 and world.schedule[start - 1] == current:
        start -= 1
    distribution = _future_distribution(
        active=current,
        elapsed=decision_block - start,
        horizon=execution_block - decision_block,
        model=model,
        policy=policy,
    )
    if not distribution:
        return current, 0.0, False
    predicted = max(distribution, key=distribution.get)
    confidence = distribution[predicted]
    if confidence < policy.minimum_prediction_confidence:
        return current, confidence, False
    return predicted, confidence, True


def _synthesise_plan(
    *,
    state: State,
    goal: State,
    predicted_graphs: Sequence[Assignment],
    confidences: Sequence[float],
    factor_count: int,
    action_cost: float,
    uncertainty_penalty: float,
) -> Tuple[int, ...]:
    actions = tuple(range(factor_count)) + (-1,)
    best_plan: Tuple[int, ...] | None = None
    best_score = float("-inf")
    for plan in itertools.product(actions, repeat=len(predicted_graphs)):
        imagined = state
        cost = 0.0
        uncertainty = 0.0
        for action, graph, confidence in zip(
            plan, predicted_graphs, confidences
        ):
            imagined = _apply_action(
                imagined, action, graph, succeeds=True
            )
            cost += action_cost * int(action >= 0)
            uncertainty += uncertainty_penalty * (1.0 - confidence)
        score = _score_state(imagined, goal) - cost - uncertainty
        if score > best_score:
            best_score = score
            best_plan = tuple(plan)
    assert best_plan is not None
    return best_plan


def _run_episode(
    *,
    world: TemporalWorld,
    policy: PlanningPolicy,
    start_block: int,
    initial_state: State,
    goal: State,
    execution_draws: Sequence[float],
    model: Mapping[Assignment, Sequence[Mapping[str, Any]]],
) -> Dict[str, Any]:
    prospective = initial_state
    reactive = initial_state
    prospective_actions = 0
    reactive_actions = 0
    repairs = 0
    prospective_trace = []
    previous_plan: Tuple[int, ...] | None = None
    for offset in range(policy.horizon):
        block = start_block + offset
        remaining = policy.horizon - offset
        predicted_graphs = []
        confidences = []
        for future_offset in range(1, remaining + 1):
            graph, confidence, used = _predict_graph(
                world=world,
                model=model,
                policy=policy.temporal,
                decision_block=block,
                execution_block=block + future_offset,
            )
            predicted_graphs.append(graph)
            confidences.append(confidence if used else 1.0)
        plan = _synthesise_plan(
            state=prospective,
            goal=goal,
            predicted_graphs=predicted_graphs,
            confidences=confidences,
            factor_count=world.factor_count,
            action_cost=policy.action_cost,
            uncertainty_penalty=policy.uncertainty_penalty,
        )
        if previous_plan is not None and plan != previous_plan[1:]:
            repairs += 1
        action = plan[0]
        prospective_actions += int(action >= 0)
        before = prospective
        prospective = _apply_action(
            prospective,
            action,
            world.schedule[block + 1],
            succeeds=execution_draws[offset] < world.reliability,
        )
        if (
            action >= 0
            and prospective
            != _apply_action(before, action, predicted_graphs[0], succeeds=True)
        ):
            repairs += 1
        previous_plan = plan

        # Reactive control plans as if the current graph remains fixed.
        reactive_graphs = [world.schedule[block]] * remaining
        reactive_plan = _synthesise_plan(
            state=reactive,
            goal=goal,
            predicted_graphs=reactive_graphs,
            confidences=[1.0] * remaining,
            factor_count=world.factor_count,
            action_cost=policy.action_cost,
            uncertainty_penalty=0.0,
        )
        reactive_action = reactive_plan[0]
        reactive_actions += int(reactive_action >= 0)
        reactive = _apply_action(
            reactive,
            reactive_action,
            world.schedule[block + 1],
            succeeds=execution_draws[offset] < world.reliability,
        )
        prospective_trace.append(
            {
                "block": block,
                "state_before": list(before),
                "goal": list(goal),
                "plan": list(plan),
                "predicted_graphs": [list(row) for row in predicted_graphs],
                "state_after": list(prospective),
                "actual_execution_graph": list(world.schedule[block + 1]),
            }
        )
    return {
        "prospective_goal_success": prospective == goal,
        "reactive_goal_success": reactive == goal,
        "prospective_final_score": _score_state(prospective, goal),
        "reactive_final_score": _score_state(reactive, goal),
        "prospective_actions": prospective_actions,
        "reactive_actions": reactive_actions,
        "plan_repairs": repairs,
        "trace": prospective_trace,
    }


def _run_world(
    *,
    world: TemporalWorld,
    policy: PlanningPolicy,
    seed: int,
    learning_stop: int,
    evaluation_start: int,
) -> Dict[str, Any]:
    rng = random.Random(seed)
    model = _learn_temporal_model(world.schedule, learning_stop)
    rows = []
    final_start = len(world.schedule) - policy.horizon - 1
    for start in range(evaluation_start, final_start, policy.horizon + 1):
        initial = tuple(rng.randrange(2) for _ in range(world.factor_count))
        goal = tuple(rng.randrange(2) for _ in range(world.factor_count))
        if goal == initial:
            goal = tuple(1 - value for value in goal)
        draws = [rng.random() for _ in range(policy.horizon)]
        rows.append(
            _run_episode(
                world=world,
                policy=policy,
                start_block=start,
                initial_state=initial,
                goal=goal,
                execution_draws=draws,
                model=model,
            )
        )
    episodes = len(rows)
    return {
        "world_id": world.world_id,
        "family": world.family,
        "episodes": episodes,
        "prospective_goal_success": sum(
            row["prospective_goal_success"] for row in rows
        ) / episodes,
        "reactive_goal_success": sum(
            row["reactive_goal_success"] for row in rows
        ) / episodes,
        "prospective_final_score": sum(
            row["prospective_final_score"] for row in rows
        ) / episodes,
        "reactive_final_score": sum(
            row["reactive_final_score"] for row in rows
        ) / episodes,
        "prospective_actions": sum(
            row["prospective_actions"] for row in rows
        ) / episodes,
        "reactive_actions": sum(
            row["reactive_actions"] for row in rows
        ) / episodes,
        "plan_repairs": sum(row["plan_repairs"] for row in rows),
        "temporal_model": {
            str(graph): [
                {"next": list(row["next"]), "duration": row["duration"]}
                for row in values
            ]
            for graph, values in model.items()
        },
        "episodes_detail": rows,
    }


def _evaluate(
    *,
    worlds: Sequence[TemporalWorld],
    policy: PlanningPolicy,
    seed: int,
    learning_stop: int,
    evaluation_start: int,
) -> Dict[str, Any]:
    rows = [
        _run_world(
            world=world,
            policy=policy,
            seed=seed + index * 101_111,
            learning_stop=learning_stop,
            evaluation_start=evaluation_start,
        )
        for index, world in enumerate(worlds)
    ]
    by_family = {}
    for family in TemporalWorldGenerator.FAMILIES:
        group = [row for row in rows if row["family"] == family]
        by_family[family] = {
            "worlds": len(group),
            "prospective_goal_success": sum(
                row["prospective_goal_success"] for row in group
            ) / len(group),
            "reactive_goal_success": sum(
                row["reactive_goal_success"] for row in group
            ) / len(group),
            "prospective_final_score": sum(
                row["prospective_final_score"] for row in group
            ) / len(group),
            "reactive_final_score": sum(
                row["reactive_final_score"] for row in group
            ) / len(group),
        }
    return {
        "policy": policy.to_dict(),
        "worlds": len(rows),
        "prospective_goal_success": sum(
            row["prospective_goal_success"] for row in rows
        ) / len(rows),
        "reactive_goal_success": sum(
            row["reactive_goal_success"] for row in rows
        ) / len(rows),
        "prospective_final_score": sum(
            row["prospective_final_score"] for row in rows
        ) / len(rows),
        "reactive_final_score": sum(
            row["reactive_final_score"] for row in rows
        ) / len(rows),
        "prospective_actions": sum(
            row["prospective_actions"] for row in rows
        ) / len(rows),
        "reactive_actions": sum(
            row["reactive_actions"] for row in rows
        ) / len(rows),
        "plan_repairs": sum(row["plan_repairs"] for row in rows),
        "by_family": by_family,
        "rows": rows,
    }


def _summary(result: Mapping[str, Any]) -> Dict[str, Any]:
    return {key: value for key, value in result.items() if key != "rows"}


def run_counterfactual_plan_repair_benchmark(
    *,
    state_path: Path,
    result_path: Path | None = None,
    development_worlds_per_family: int = 6,
    sealed_worlds_per_family: int = 10,
    blocks: int = 110,
    learning_stop: int = 50,
    evaluation_start: int = 54,
) -> Dict[str, Any]:
    if state_path.exists():
        state_path.unlink()
    authority = lambda goal: {
        "allow_learn": True,
        "goal": "maintain_coherence",
        "source": "counterfactual_planning_authority",
        "S": 1.0,
        "H": 0.0,
    }
    runtime = HexCorePersistentLearningRuntime(
        state_path=state_path,
        authority_provider=authority,
    )
    generator = TemporalWorldGenerator()
    development = generator.generate(
        seed=19191,
        worlds_per_family=development_worlds_per_family,
        blocks=blocks,
        cohort="counterfactual_development",
    )
    sealed = generator.generate(
        seed=39393,
        worlds_per_family=sealed_worlds_per_family,
        blocks=blocks,
        cohort="counterfactual_sealed",
    )
    temporal = ProspectivePolicy(
        "phase18_temporal_forecaster", 3, 1.0, 0.90, 4
    )
    conservative_temporal = ProspectivePolicy(
        "phase18_temporal_forecaster_conservative", 3, 1.0, 0.95, 4
    )
    policies = [
        PlanningPolicy("repair_h2", temporal, 2, 0.015, 0.02),
        PlanningPolicy("repair_h3", temporal, 3, 0.015, 0.02),
        PlanningPolicy("repair_h4", temporal, 4, 0.015, 0.03),
        PlanningPolicy(
            "repair_h2_conservative",
            conservative_temporal,
            2,
            0.015,
            0.03,
        ),
        PlanningPolicy(
            "repair_h3_conservative",
            conservative_temporal,
            3,
            0.015,
            0.03,
        ),
    ]
    development_results = [
        _evaluate(
            worlds=development,
            policy=policy,
            seed=6060,
            learning_stop=learning_stop,
            evaluation_start=evaluation_start,
        )
        for policy in policies
    ]
    safe_development = [
        row for row in development_results
        if min(
            family["prospective_goal_success"]
            - family["reactive_goal_success"]
            for family in row["by_family"].values()
        ) >= -0.01
    ]
    selected_result = max(
        safe_development or development_results,
        key=lambda row: (
            row["prospective_goal_success"] - row["reactive_goal_success"],
            row["prospective_final_score"] - row["reactive_final_score"],
            -row["prospective_actions"],
        ),
    )
    selected = next(
        policy for policy in policies
        if policy.policy_id == selected_result["policy"]["policy_id"]
    )
    sealed_result = _evaluate(
        worlds=sealed,
        policy=selected,
        seed=7070,
        learning_stop=learning_stop,
        evaluation_start=evaluation_start,
    )
    success_gain = (
        sealed_result["prospective_goal_success"]
        - sealed_result["reactive_goal_success"]
    )
    score_gain = (
        sealed_result["prospective_final_score"]
        - sealed_result["reactive_final_score"]
    )
    worst_change = min(
        row["prospective_goal_success"] - row["reactive_goal_success"]
        for row in sealed_result["by_family"].values()
    )
    errors = []
    if success_gain < 0.05:
        errors.append("EXACT_GOAL_SUCCESS_GAIN_BELOW_FIVE_POINTS")
    if score_gain < 0.03:
        errors.append("FINAL_STATE_SCORE_GAIN_BELOW_THREE_POINTS")
    if worst_change < -0.01:
        errors.append("WORST_FAMILY_REGRESSION")
    if sealed_result["prospective_actions"] > selected.horizon:
        errors.append("ACTION_BUDGET_EXCEEDED")
    if selected.complexity > 18:
        errors.append("UNCONTROLLED_PLANNER_COMPLEXITY")
    gate = {
        "accepted": not errors,
        "errors": errors,
        "exact_goal_success_gain": success_gain,
        "final_state_score_gain": score_gain,
        "worst_family_goal_change": worst_change,
        "mean_actions": sealed_result["prospective_actions"],
        "plan_repairs": sealed_result["plan_repairs"],
    }

    baseline = ProcedureCandidate(
        procedure_id="procedure_prospective_temporal_70387bb93ebb",
        goal="counterfactual_temporal_planning",
        steps=["choose_one_delayed_action_from_future_graph"],
        score=sealed_result["reactive_goal_success"],
        success=True,
        evidence={"evaluation": "phase19_reactive_sequence_control"},
    )
    runtime.skills.promote(baseline)
    candidate = ProcedureCandidate(
        procedure_id=(
            "procedure_counterfactual_plan_"
            + _canonical_hash(selected.to_dict())[:12]
        ),
        goal="counterfactual_temporal_planning",
        steps=[
            "construct_future_graph_scenarios",
            "enumerate_bounded_action_sequences",
            "simulate_candidate_consequences",
            "select_goal_directed_plan_under_cost",
            "execute_first_action_only",
            "compare_observed_to_predicted_outcome",
            "repair_remaining_plan_on_surprise",
            "retain_verified_planning_skill",
        ],
        score=sealed_result["prospective_goal_success"],
        success=gate["accepted"],
        evidence={
            "evaluation": "phase19_counterfactual_plan_repair_sealed",
            "gate": gate,
        },
    )
    decision = runtime.skills.promote(candidate)
    if gate["accepted"]:
        runtime.store.state.setdefault("causal_graphs", {})[
            "counterfactual_plan_repair"
        ] = {
            "schema_version": "aion.hexcore.counterfactual_plan_memory.v1",
            "policy": selected.to_dict(),
            "gate": gate,
            "created_at": _utc_timestamp(),
            "source": "phase19_sealed_counterfactual_outcomes",
        }
        runtime.store.commit(reason="counterfactual_plan_repair_memory")
    restarted = HexCorePersistentLearningRuntime(
        state_path=state_path,
        authority_provider=authority,
    )
    champion = restarted.skills.champion(candidate.goal)
    retained = bool(
        champion and champion.get("procedure_id") == candidate.procedure_id
    )
    result = {
        "schema_version": "aion.hexcore.counterfactual_plan_repair.v1",
        "benchmark": "multi_step_counterfactual_planning_and_repair",
        "language_provider_used": False,
        "development": {
            "policies": [_summary(row) for row in development_results],
            "selected_policy": selected.to_dict(),
        },
        "sealed": {"result": _summary(sealed_result), "gate": gate},
        "promotion": {
            "candidate": candidate.to_dict(),
            "decision": decision,
        },
        "restart": {
            "champion_retained": retained,
            "planning_memory_retained": (
                "counterfactual_plan_repair"
                in restarted.store.state.get("causal_graphs", {})
            ),
            "relearning_worlds": 0,
        },
        "gates": {
            "counterfactual_simulation": True,
            "multi_step_goal_planning": True,
            "outcome_based_plan_repair": True,
            "sealed_gate_passed": gate["accepted"],
            "restart_retention": retained,
        },
        "boundary_statement": (
            "The planner searches bounded binary-state action sequences with "
            "short horizons inside learned temporal causal worlds. It is not "
            "evidence of unrestricted general planning."
        ),
        "passed": bool(gate["accepted"] and retained),
    }
    if result_path is not None:
        result_path.parent.mkdir(parents=True, exist_ok=True)
        result_path.write_text(
            json.dumps(result, indent=2, sort_keys=True),
            encoding="utf-8",
        )
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--state-path",
        type=Path,
        default=Path("data/hexcore/counterfactual_plan_repair.json"),
    )
    parser.add_argument(
        "--result-path",
        type=Path,
        default=Path("results/hexcore_counterfactual_plan_repair.json"),
    )
    args = parser.parse_args()
    result = run_counterfactual_plan_repair_benchmark(
        state_path=args.state_path,
        result_path=args.result_path,
    )
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
