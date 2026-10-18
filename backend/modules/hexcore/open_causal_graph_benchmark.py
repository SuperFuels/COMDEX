from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict

from backend.modules.hexcore.open_causal_graph_discovery import (
    GovernedOpenCausalGraphLearner,
    MultiVariableBooleanEnvironment,
)
from backend.modules.hexcore.persistent_learning import (
    HexCorePersistentLearningRuntime,
)


def _allow(goal: str) -> Dict[str, Any]:
    return {
        "allow_learn": True,
        "deny_reason": None,
        "goal": goal,
        "source": "open_causal_graph_benchmark_authority",
        "S": 1.0,
        "H": 0.0,
    }


def _evaluate_retained_graph(graph: Dict[str, Any]) -> Dict[str, Any]:
    from backend.modules.hexcore.open_causal_graph_discovery import (
        BooleanRule,
        CausalGraph,
    )

    restored = CausalGraph(
        graph_id=graph["graph_id"],
        source=graph["source"],
        rules={
            target: BooleanRule(
                row["kind"], tuple(row["arguments"]), int(row["complexity"])
            )
            for target, row in graph["rules"].items()
        },
    )
    correct = 0
    total = 0
    for initial_state in (
        {"signal": 0, "gate": 0, "output": 0},
        {"signal": 1, "gate": 0, "output": 1},
        {"signal": 0, "gate": 1, "output": 1},
        {"signal": 1, "gate": 1, "output": 0},
    ):
        for action in ("flip_signal", "flip_gate", "pulse", "idle"):
            environment = MultiVariableBooleanEnvironment(
                initial_state=initial_state
            )
            expected = environment.step(action)["next_state"]
            predicted = restored.predict(initial_state, action)
            for target in expected:
                total += 1
                correct += int(predicted[target] == expected[target])
    return {
        "transition_accuracy": correct / total,
        "correct_fields": correct,
        "total_fields": total,
        "worlds": 4,
        "actions_per_world": 4,
    }


def run_open_causal_graph_benchmark(
    *,
    state_path: Path,
    result_path: Path | None = None,
) -> Dict[str, Any]:
    if state_path.exists():
        state_path.unlink()
    runtime = HexCorePersistentLearningRuntime(
        state_path=state_path,
        authority_provider=_allow,
    )
    learner = GovernedOpenCausalGraphLearner(runtime.store)
    environment = MultiVariableBooleanEnvironment()
    variables = ["signal", "gate", "output"]
    actions = ["flip_signal", "flip_gate", "pulse", "idle"]
    initial_graph = learner.persistence_graph(
        "open_boolean_device_v1", variables
    )
    session = learner.discover(
        world_id="open_boolean_device_v1",
        variables=variables,
        actions=actions,
        action_costs={
            "flip_signal": 0.1,
            "flip_gate": 0.1,
            "pulse": 0.3,
            "idle": 0.05,
        },
        experiment_runner=environment.step,
        initial_state=environment.state,
        initial_graph=initial_graph,
        experiments=64,
        adequacy_gate=0.95,
        minimum_held_out_gain=0.10,
        maximum_graph_complexity=12,
        persist=True,
    )
    restarted = HexCorePersistentLearningRuntime(
        state_path=state_path,
        authority_provider=_allow,
    )
    retained = restarted.store.state["causal_graphs"].get(
        "open_boolean_device_v1"
    )
    restart_evaluation = (
        _evaluate_retained_graph(retained)
        if retained
        else {"transition_accuracy": 0.0}
    )
    result = {
        "schema_version": "aion.hexcore.open_causal_graph_benchmark.v1",
        "benchmark": "bounded_open_hypothesis_construction",
        "language_provider_used": False,
        "initial_hypothesis_set_supplied": False,
        "variable_and_action_vocabulary_supplied": True,
        "rule_grammar_bounded": True,
        "active_experiment_selection_enabled": True,
        "session": session,
        "restart": {
            "graph_retained": retained is not None,
            "relearning_experiments": 0,
            "evaluation": restart_evaluation,
        },
        "gates": {
            "inadequate_model_rejected": (
                session["initial_model_criticism"]["decision"]
                == "NONE_ADEQUATE"
            ),
            "novel_structure_constructed": bool(session["novel_edges"]),
            "constructed_graph_held_out_accuracy_at_least_95_percent": (
                session["constructed_model_criticism"][
                    "held_out_transition_accuracy"
                ]
                >= 0.95
            ),
            "held_out_gain_at_least_10_points": (
                session["held_out_gain"] >= 0.10
            ),
            "complexity_bounded": (
                session["constructed_graph"]["complexity"]
                <= session["complexity_cap"]
            ),
            "cau_governed_persistence": retained is not None,
            "restart_retention_without_relearning": (
                retained is not None
                and restart_evaluation["transition_accuracy"] >= 0.95
            ),
        },
        "boundary_statement": (
            "This demonstrates bounded construction and revision of inspectable "
            "Boolean causal graphs. Variables, actions, and the rule grammar are "
            "provided; this is not unrestricted open-world causal invention."
        ),
    }
    result["passed"] = all(result["gates"].values())
    if result_path is not None:
        result_path.parent.mkdir(parents=True, exist_ok=True)
        result_path.write_text(
            json.dumps(result, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--state-path",
        type=Path,
        default=Path("data/hexcore/open_causal_graph_state.json"),
    )
    parser.add_argument(
        "--result-path",
        type=Path,
        default=Path("results/hexcore_open_causal_graph_benchmark.json"),
    )
    args = parser.parse_args()
    result = run_open_causal_graph_benchmark(
        state_path=args.state_path,
        result_path=args.result_path,
    )
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()

