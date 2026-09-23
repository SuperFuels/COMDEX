from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, Sequence

from backend.modules.hexcore.active_causal_discovery import (
    CausalHypothesis,
    GovernedActiveCausalLearner,
    StochasticHiddenModeEnvironment,
)
from backend.modules.hexcore.persistent_learning import (
    HexCorePersistentLearningRuntime,
    ProcedureCandidate,
)


HYPOTHESES = [
    CausalHypothesis(
        hypothesis_id="alpha",
        action_outcomes={"amber": "positive", "cobalt": "negative"},
        action_deltas={"amber": 2.0, "cobalt": -1.0},
        reliability=0.9,
    ),
    CausalHypothesis(
        hypothesis_id="beta",
        action_outcomes={"amber": "negative", "cobalt": "positive"},
        action_deltas={"amber": -1.0, "cobalt": 2.0},
        reliability=0.9,
    ),
]
ACTIONS = ["amber", "cobalt"]
ACTION_COSTS = {"amber": 0.10, "cobalt": 0.30}


def _allow(goal: str) -> Dict[str, Any]:
    return {
        "allow_learn": True,
        "deny_reason": None,
        "goal": goal,
        "source": "active_causal_benchmark_authority",
        "S": 1.0,
        "H": 0.0,
    }


def _verify_procedure(
    *,
    mode: str,
    steps: Sequence[str],
    rollouts: int = 200,
) -> Dict[str, Any]:
    results = [
        StochasticHiddenModeEnvironment(
            mode=mode,
            hypotheses=HYPOTHESES,
            threshold=4.0,
            seed=10000 + index,
        ).run(steps)
        for index in range(rollouts)
    ]
    successes = sum(1 for result in results if result["success"])
    success_rate = successes / rollouts
    average_score = sum(float(result["score"]) for result in results) / rollouts
    return {
        "success": success_rate >= 0.95,
        "score": round(average_score, 6),
        "success_rate": round(success_rate, 6),
        "rollouts": rollouts,
        "verified": True,
        "verification_method": "stochastic_simulator_rollout",
    }


def _evaluated_candidate(
    candidate: ProcedureCandidate,
    verification: Dict[str, Any],
) -> ProcedureCandidate:
    return ProcedureCandidate(
        procedure_id=candidate.procedure_id,
        goal=candidate.goal,
        steps=list(candidate.steps),
        score=float(verification["score"]),
        success=bool(verification["success"]),
        evidence={**candidate.evidence, "verification": verification},
        source_rules=list(candidate.source_rules),
    )


def run_active_causal_benchmark(
    *,
    state_path: Path,
    result_path: Path | None = None,
    seeds_per_mode: int = 60,
) -> Dict[str, Any]:
    if state_path.exists():
        state_path.unlink()
    runtime = HexCorePersistentLearningRuntime(
        state_path=state_path,
        authority_provider=_allow,
    )
    learner = GovernedActiveCausalLearner(runtime.store)

    # --------------------------------------------------------------
    # Multi-seed independent audit.
    # --------------------------------------------------------------
    audit_rows = []
    for mode_index, mode in enumerate(["alpha", "beta"]):
        for seed in range(seeds_per_mode):
            environment = StochasticHiddenModeEnvironment(
                mode=mode,
                hypotheses=HYPOTHESES,
                threshold=4.0,
                seed=mode_index * 1000 + seed,
            )
            session = learner.discover(
                world_id=f"audit_{mode}_{seed}",
                hypotheses=HYPOTHESES,
                actions=ACTIONS,
                action_costs=ACTION_COSTS,
                experiment_runner=environment.probe,
                confidence_gate=0.95,
                maximum_experiments=8,
                persist=False,
            )
            audit_rows.append(
                {
                    "mode": mode,
                    "seed": seed,
                    "winner": session["winner"],
                    "correct": session["winner"] == mode,
                    "calibrated": session["calibrated"],
                    "confidence": session["confidence"],
                    "experiment_count": session["experiment_count"],
                    "total_experiment_cost": session["total_experiment_cost"],
                    "stop_reason": session["stop_reason"],
                }
            )

    accuracy = sum(1 for row in audit_rows if row["correct"]) / len(audit_rows)
    calibration_rate = sum(1 for row in audit_rows if row["calibrated"]) / len(audit_rows)
    average_experiments = sum(row["experiment_count"] for row in audit_rows) / len(audit_rows)
    average_cost = sum(row["total_experiment_cost"] for row in audit_rows) / len(audit_rows)

    # --------------------------------------------------------------
    # Persistent alpha discovery and robust procedure promotion.
    # --------------------------------------------------------------
    adaptive_world_id = "adaptive_hidden_mode_device_v1"
    alpha_environment = StochasticHiddenModeEnvironment(
        mode="alpha",
        hypotheses=HYPOTHESES,
        threshold=4.0,
        seed=101,
    )
    alpha_session = learner.discover(
        world_id=adaptive_world_id,
        hypotheses=HYPOTHESES,
        actions=ACTIONS,
        action_costs=ACTION_COSTS,
        experiment_runner=alpha_environment.probe,
        confidence_gate=0.95,
        maximum_experiments=8,
        reset_belief=True,
        persist=True,
    )
    alpha_candidate = learner.build_robust_procedure(
        world_id=adaptive_world_id,
        hypotheses=HYPOTHESES,
        terminal_action="open",
        threshold=4.0,
        target_success_probability=0.95,
    )
    alpha_verification = _verify_procedure(mode="alpha", steps=alpha_candidate.steps)
    alpha_evaluated = _evaluated_candidate(alpha_candidate, alpha_verification)
    alpha_promotion = runtime.skills.promote(alpha_evaluated)
    runtime.skills.record_outcome(
        procedure_id=alpha_evaluated.procedure_id,
        success=alpha_evaluated.success,
        score=alpha_evaluated.score,
        evidence=alpha_evaluated.evidence,
    )

    # --------------------------------------------------------------
    # The hidden mode changes. A surprising observation must reset
    # the old belief before beta is learned.
    # --------------------------------------------------------------
    beta_environment = StochasticHiddenModeEnvironment(
        mode="beta",
        hypotheses=HYPOTHESES,
        threshold=4.0,
        seed=7,
    )
    change_observation = beta_environment.probe("amber")
    change_event = learner.detect_change(
        world_id=adaptive_world_id,
        hypotheses=HYPOTHESES,
        action="amber",
        outcome=change_observation["outcome"],
        surprise_threshold=0.2,
    )
    beta_session = learner.discover(
        world_id=adaptive_world_id,
        hypotheses=HYPOTHESES,
        actions=ACTIONS,
        action_costs=ACTION_COSTS,
        experiment_runner=beta_environment.probe,
        confidence_gate=0.95,
        maximum_experiments=8,
        persist=True,
    )
    beta_candidate = learner.build_robust_procedure(
        world_id=adaptive_world_id,
        hypotheses=HYPOTHESES,
        terminal_action="open",
        threshold=4.0,
        target_success_probability=0.95,
    )
    beta_verification = _verify_procedure(mode="beta", steps=beta_candidate.steps)
    beta_evaluated = _evaluated_candidate(beta_candidate, beta_verification)
    beta_promotion = runtime.skills.promote(beta_evaluated)
    runtime.skills.record_outcome(
        procedure_id=beta_evaluated.procedure_id,
        success=beta_evaluated.success,
        score=beta_evaluated.score,
        evidence=beta_evaluated.evidence,
    )

    # --------------------------------------------------------------
    # Restart: both mode-specific skills and the latest belief survive.
    # --------------------------------------------------------------
    restarted = HexCorePersistentLearningRuntime(
        state_path=state_path,
        authority_provider=_allow,
    )
    alpha_champion = restarted.skills.champion("opened=True:mode=alpha")
    beta_champion = restarted.skills.champion("opened=True:mode=beta")
    retained_belief = restarted.store.state["causal_beliefs"].get(adaptive_world_id)
    alpha_restart = (
        _verify_procedure(mode="alpha", steps=alpha_champion["steps"], rollouts=100)
        if alpha_champion
        else {"success": False}
    )
    beta_restart = (
        _verify_procedure(mode="beta", steps=beta_champion["steps"], rollouts=100)
        if beta_champion
        else {"success": False}
    )

    result = {
        "schema_version": "aion.hexcore.active_causal_discovery_benchmark.v1",
        "benchmark": "stochastic_hidden_mode_active_discovery",
        "language_provider_used": False,
        "partial_observability": True,
        "stochastic_consequences": True,
        "experiment_costs_enabled": True,
        "information_gain_selection_enabled": True,
        "independent_seed_audit": {
            "seeds_per_mode": seeds_per_mode,
            "episode_count": len(audit_rows),
            "mode_identification_accuracy": round(accuracy, 6),
            "calibration_rate": round(calibration_rate, 6),
            "average_experiment_count": round(average_experiments, 6),
            "average_experiment_cost": round(average_cost, 6),
            "maximum_experiments": max(row["experiment_count"] for row in audit_rows),
            "rows": audit_rows,
        },
        "alpha": {
            "session": alpha_session,
            "procedure": alpha_evaluated.to_dict(),
            "verification": alpha_verification,
            "promotion": alpha_promotion,
        },
        "change": {
            "observation": change_observation,
            "event": change_event,
            "detected": change_event.get("change_detected") is True,
        },
        "beta": {
            "session": beta_session,
            "procedure": beta_evaluated.to_dict(),
            "verification": beta_verification,
            "promotion": beta_promotion,
        },
        "restart": {
            "retained_belief": retained_belief,
            "alpha_procedure_retained": alpha_champion is not None,
            "beta_procedure_retained": beta_champion is not None,
            "alpha_verified_after_restart": bool(alpha_restart.get("success")),
            "beta_verified_after_restart": bool(beta_restart.get("success")),
            "relearning_experiments": 0,
        },
        "status": restarted.status(),
        "gates": {
            "mode_accuracy_at_least_90_percent": accuracy >= 0.90,
            "calibration_at_least_90_percent": calibration_rate >= 0.90,
            "average_experiments_at_most_5": average_experiments <= 5.0,
            "alpha_discovered": alpha_session["winner"] == "alpha"
            and alpha_session["calibrated"],
            "change_detected": change_event.get("change_detected") is True,
            "beta_discovered": beta_session["winner"] == "beta"
            and beta_session["calibrated"],
            "robust_procedures_verified": alpha_verification["success"]
            and beta_verification["success"],
            "restart_retention": bool(
                alpha_champion
                and beta_champion
                and alpha_restart.get("success")
                and beta_restart.get("success")
                and retained_belief
                and retained_belief.get("winner") == "beta"
            ),
        },
        "boundary_statement": (
            "This demonstrates bounded active causal discovery under stochastic "
            "partial observation and mode change. It is not open-world causal intelligence."
        ),
    }
    result["passed"] = all(result["gates"].values())
    if result_path is not None:
        result_path.parent.mkdir(parents=True, exist_ok=True)
        result_path.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--state-path",
        type=Path,
        default=Path("data/hexcore/active_causal_learning_state.json"),
    )
    parser.add_argument(
        "--result-path",
        type=Path,
        default=Path("results/hexcore_active_causal_discovery_benchmark.json"),
    )
    parser.add_argument("--seeds-per-mode", type=int, default=60)
    args = parser.parse_args()
    result = run_active_causal_benchmark(
        state_path=args.state_path,
        result_path=args.result_path,
        seeds_per_mode=args.seeds_per_mode,
    )
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
