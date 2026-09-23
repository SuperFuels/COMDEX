from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict

from backend.modules.hexcore.persistent_learning import (
    HexCorePersistentLearningRuntime,
)
from backend.modules.hexcore.stochastic_multilatent_discovery import (
    GovernedStochasticMultiLatentLearner,
    StochasticTwoFactorVault,
)


ACTIONS = [
    "flip_left",
    "flip_right",
    "inspect_left",
    "inspect_right",
    "open",
]
SIGNALS = ["left_signal", "right_signal"]


def _allow(goal: str) -> Dict[str, Any]:
    return {
        "allow_learn": True,
        "deny_reason": None,
        "goal": goal,
        "source": "stochastic_multilatent_benchmark_authority",
        "S": 1.0,
        "H": 0.0,
    }


def run_stochastic_multilatent_benchmark(
    *,
    state_path: Path,
    result_path: Path | None = None,
    audit_episodes: int = 100,
) -> Dict[str, Any]:
    if state_path.exists():
        state_path.unlink()
    runtime = HexCorePersistentLearningRuntime(
        state_path=state_path,
        authority_provider=_allow,
    )
    learner = GovernedStochasticMultiLatentLearner(runtime.store)
    sequences = learner.diagnostic_sequences(
        actions=ACTIONS,
        episodes=50,
        steps=15,
    )

    def training_factory(episode: int):
        return StochasticTwoFactorVault(
            seed=10_000 + episode
        ).step

    rows = learner.collect(
        runner_factory=training_factory,
        sequences=sequences,
        phase="structure",
    )
    discovery = learner.discover(
        world_id="two_factor_vault_v1",
        actions=ACTIONS,
        signal_targets=SIGNALS,
        rows=rows,
        maximum_factors=2,
        maximum_complexity=12,
        persist=True,
    )
    graph = learner.graph_from_record(
        runtime.store.state["causal_graphs"]["two_factor_vault_v1"]
    )

    audit_rows = []
    for episode in range(audit_episodes):
        environment = StochasticTwoFactorVault(
            seed=20_000 + episode
        )
        result = learner.investigate_and_plan(
            graph=graph,
            runner=environment.step,
            initial_visible=dict(environment.visible),
            action_costs={
                "inspect_left": 0.1,
                "inspect_right": 0.1,
            },
            confidence_gate=0.95,
            maximum_experiments=6,
        )
        actual = environment.audit_hidden_factors()
        predicted = tuple(
            row["value"] for row in result["marginals"]
        )
        confidence = min(
            row["confidence"] for row in result["marginals"]
        )
        audit_rows.append(
            {
                "episode": episode,
                "actual_factors_after_plan": actual,
                "predicted_factors_after_plan": predicted,
                "factor_state_correct": predicted == actual,
                "confidence": confidence,
                **result,
            }
        )

    factor_accuracy = sum(
        row["factor_state_correct"] for row in audit_rows
    ) / len(audit_rows)
    goal_success_rate = sum(
        row["goal_success"] for row in audit_rows
    ) / len(audit_rows)
    average_confidence = sum(
        row["confidence"] for row in audit_rows
    ) / len(audit_rows)
    calibration_error = abs(average_confidence - factor_accuracy)
    average_experiments = sum(
        row["experiment_count"] for row in audit_rows
    ) / len(audit_rows)

    restarted = HexCorePersistentLearningRuntime(
        state_path=state_path,
        authority_provider=_allow,
    )
    retained = restarted.store.state["causal_graphs"].get(
        "two_factor_vault_v1"
    )
    restart_graph = learner.graph_from_record(retained)
    restart_environment = StochasticTwoFactorVault(seed=99_001)
    restart_result = learner.investigate_and_plan(
        graph=restart_graph,
        runner=restart_environment.step,
        initial_visible=dict(restart_environment.visible),
        action_costs={"inspect_left": 0.1, "inspect_right": 0.1},
        confidence_gate=0.95,
        maximum_experiments=6,
    )

    result = {
        "schema_version": (
            "aion.hexcore.stochastic_multilatent_benchmark.v1"
        ),
        "benchmark": (
            "stochastic_two_factor_active_investigation_and_planning"
        ),
        "language_provider_used": False,
        "hidden_factor_labels_supplied_to_learner": False,
        "candidate_graphs_supplied": False,
        "discovery": discovery,
        "independent_audit": {
            "episodes": audit_episodes,
            "factor_state_accuracy": round(factor_accuracy, 8),
            "goal_success_rate": round(goal_success_rate, 8),
            "average_confidence": round(average_confidence, 8),
            "calibration_error": round(calibration_error, 8),
            "average_experiments": round(average_experiments, 8),
            "maximum_experiments": max(
                row["experiment_count"] for row in audit_rows
            ),
            "rows": audit_rows,
        },
        "restart": {
            "graph_retained": retained is not None,
            "factor_count": restart_graph.factor_count,
            "goal_success": restart_result["goal_success"],
            "relearning_experiments": 0,
        },
        "gates": {
            "two_factor_structure_selected": (
                discovery["accepted"]
                and discovery["graph"]["factor_count"] == 2
            ),
            "two_factor_model_beats_one_factor_control": (
                discovery[
                    "held_out_normalized_log_likelihood_gain"
                ]
                >= 0.05
            ),
            "active_information_gain_enabled": all(
                row["trace"]
                and all(
                    trace["expected_information_gain"] > 0
                    for trace in row["trace"]
                )
                for row in audit_rows
            ),
            "factor_accuracy_at_least_90_percent": (
                factor_accuracy >= 0.90
            ),
            "calibration_error_at_most_10_percent": (
                calibration_error <= 0.10
            ),
            "average_experiments_at_most_6": (
                average_experiments <= 6.0
            ),
            "goal_success_at_least_90_percent": (
                goal_success_rate >= 0.90
            ),
            "restart_retention_without_structural_relearning": (
                retained is not None
                and restart_graph.factor_count == 2
                and restart_result["goal_success"]
            ),
        },
        "boundary_statement": (
            "This demonstrates bounded discovery and use of two binary hidden "
            "factors under noisy observation. Roles and factors are selected "
            "from a fixed grammar; it is not unrestricted world modelling."
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
        default=Path("data/hexcore/stochastic_multilatent.json"),
    )
    parser.add_argument(
        "--result-path",
        type=Path,
        default=Path(
            "results/hexcore_stochastic_multilatent_benchmark.json"
        ),
    )
    parser.add_argument("--audit-episodes", type=int, default=100)
    args = parser.parse_args()
    result = run_stochastic_multilatent_benchmark(
        state_path=args.state_path,
        result_path=args.result_path,
        audit_episodes=args.audit_episodes,
    )
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()

