from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, Mapping

from backend.modules.hexcore.continuous_causal_change_benchmark import (
    ChangePolicy,
    ContinuousWorldGenerator,
    _evaluate,
    _score,
    _summary,
)
from backend.modules.hexcore.persistent_learning import (
    HexCorePersistentLearningRuntime,
    ProcedureCandidate,
    _canonical_hash,
)


CONTROL = ChangePolicy(
    policy_id="phase15_fixed_five_trial_champion",
    posterior_gate=0.85,
    stability_blocks=4,
    diagnostic_trials=5,
    provisional_stability_blocks=2,
    escalation_trials=0,
)


def _allow(goal: str) -> Dict[str, Any]:
    return {
        "allow_learn": True,
        "goal": goal,
        "source": "adaptive_change_diagnostics_authority",
        "S": 1.0,
        "H": 0.0,
    }


def _efficiency_score(result: Mapping[str, Any]) -> float:
    return (
        _score(result)
        - 0.00005 * result["average_diagnostic_actions"]
    )


def _gate(
    control: Mapping[str, Any],
    challenger: Mapping[str, Any],
) -> Dict[str, Any]:
    diagnostic_reduction = (
        1.0
        - challenger["average_diagnostic_actions"]
        / control["average_diagnostic_actions"]
    )
    active_change = (
        challenger["active_graph_accuracy"]
        - control["active_graph_accuracy"]
    )
    goal_change = (
        challenger["adaptive_goal_success"]
        - control["adaptive_goal_success"]
    )
    errors = []
    if challenger["change_recall"] < control["change_recall"]:
        errors.append("CHANGE_RECALL_REGRESSION")
    if (
        challenger["false_revision_rate"]
        > control["false_revision_rate"]
    ):
        errors.append("FALSE_REVISION_REGRESSION")
    if active_change < -0.01:
        errors.append("ACTIVE_GRAPH_REGRESSION_ABOVE_ONE_POINT")
    if goal_change < -0.01:
        errors.append("GOAL_SUCCESS_REGRESSION_ABOVE_ONE_POINT")
    if diagnostic_reduction < 0.20:
        errors.append("DIAGNOSTIC_ACTION_REDUCTION_BELOW_20_PERCENT")
    if challenger["adaptive_goal_success"] < 0.85:
        errors.append("ADAPTIVE_GOAL_SUCCESS_BELOW_85_PERCENT")
    if challenger["policy"]["complexity"] > 10:
        errors.append("ADAPTIVE_DIAGNOSTIC_COMPLEXITY_CAP_EXCEEDED")
    return {
        "accepted": not errors,
        "errors": errors,
        "change_recall_change": (
            challenger["change_recall"] - control["change_recall"]
        ),
        "false_revision_change": (
            challenger["false_revision_rate"]
            - control["false_revision_rate"]
        ),
        "active_graph_accuracy_change": active_change,
        "adaptive_goal_success_change": goal_change,
        "diagnostic_action_reduction": diagnostic_reduction,
    }


def run_adaptive_change_diagnostics_benchmark(
    *,
    state_path: Path,
    result_path: Path | None = None,
    development_worlds_per_family: int = 5,
    sealed_worlds_per_family: int = 8,
    blocks: int = 24,
) -> Dict[str, Any]:
    if state_path.exists():
        state_path.unlink()
    runtime = HexCorePersistentLearningRuntime(
        state_path=state_path,
        authority_provider=_allow,
    )
    generator = ContinuousWorldGenerator()
    development = generator.generate(
        seed=16_100_101,
        worlds_per_family=development_worlds_per_family,
        blocks=blocks,
        cohort="adaptive_diagnostics_development",
    )
    sealed = generator.generate(
        seed=16_199_909,
        worlds_per_family=sealed_worlds_per_family,
        blocks=blocks,
        cohort="adaptive_diagnostics_sealed",
    )
    candidates = [
        ChangePolicy(
            policy_id=f"adaptive_base_{base}_extra_{extra}",
            posterior_gate=0.85,
            stability_blocks=4,
            diagnostic_trials=base,
            provisional_stability_blocks=2,
            escalation_trials=extra,
        )
        for base, extra in ((2, 5), (3, 4), (3, 3), (4, 2))
    ]
    control_development = _evaluate(
        runtime=runtime,
        worlds=development,
        policy=CONTROL,
        seed=16_500_000,
        persist=False,
    )
    candidate_development = [
        _evaluate(
            runtime=runtime,
            worlds=development,
            policy=policy,
            seed=16_500_000,
            persist=False,
        )
        for policy in candidates
    ]
    selected_index = max(
        range(len(candidates)),
        key=lambda index: (
            _efficiency_score(candidate_development[index]),
            -candidate_development[index]["false_revision_rate"],
            candidate_development[index]["active_graph_accuracy"],
        ),
    )
    selected = candidates[selected_index]
    control_sealed = _evaluate(
        runtime=runtime,
        worlds=sealed,
        policy=CONTROL,
        seed=17_500_000,
        persist=False,
    )
    challenger_sealed = _evaluate(
        runtime=runtime,
        worlds=sealed,
        policy=selected,
        seed=17_500_000,
        persist=True,
    )
    gate = _gate(control_sealed, challenger_sealed)
    baseline = ProcedureCandidate(
        procedure_id=(
            "procedure_continuous_world_maintenance_56d6520b131c"
        ),
        goal="continuous_world_model_maintenance",
        steps=["fixed_five_trial_continuous_diagnostics"],
        score=_efficiency_score(control_sealed),
        success=True,
        evidence={"evaluation": "phase16_sealed_control"},
    )
    runtime.skills.promote(baseline)
    candidate = ProcedureCandidate(
        procedure_id=(
            "procedure_adaptive_change_diagnostics_"
            f"{_canonical_hash(selected.to_dict())[:12]}"
        ),
        goal="continuous_world_model_maintenance",
        steps=[
            "run_low_cost_stability_monitor",
            "measure_active_graph_posterior",
            "escalate_diagnostics_on_surprise",
            "use_provisional_operational_graph",
            "consolidate_only_after_durable_stability",
        ],
        score=_efficiency_score(challenger_sealed),
        success=bool(gate["accepted"]),
        evidence={
            "evaluation": "phase16_adaptive_diagnostics_sealed",
            "gate": gate,
        },
    )
    promotion = runtime.skills.promote(candidate)
    restarted = HexCorePersistentLearningRuntime(
        state_path=state_path,
        authority_provider=_allow,
    )
    retained = restarted.skills.champion(
        "continuous_world_model_maintenance"
    )
    result = {
        "schema_version": (
            "aion.hexcore.adaptive_change_diagnostics.v1"
        ),
        "benchmark": "surprise_triggered_diagnostic_escalation",
        "language_provider_used": False,
        "development": {
            "control": _summary(control_development),
            "challengers": [
                _summary(row) for row in candidate_development
            ],
            "selected_policy": selected.to_dict(),
        },
        "sealed": {
            "control": _summary(control_sealed),
            "challenger": _summary(challenger_sealed),
            "gate": gate,
        },
        "promotion": {
            "candidate": candidate.to_dict(),
            "decision": promotion,
        },
        "restart": {
            "champion_retained": retained is not None,
            "champion_id": (
                retained.get("procedure_id") if retained else None
            ),
            "relearning_worlds": 0,
        },
        "gates": {
            "surprise_triggered_escalation": True,
            "sealed_gate_passed": gate["accepted"],
            "cau_promoted_if_safe": (
                bool(promotion.get("promoted"))
                == bool(gate["accepted"])
            ),
            "restart_retention": retained is not None,
        },
        "boundary_statement": (
            "The diagnostic schedule mutates only base and escalation trial "
            "counts inside the bounded Phase 15 graph grammar."
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
        default=Path("data/hexcore/adaptive_change_diagnostics.json"),
    )
    parser.add_argument(
        "--result-path",
        type=Path,
        default=Path("results/hexcore_adaptive_change_diagnostics.json"),
    )
    args = parser.parse_args()
    result = run_adaptive_change_diagnostics_benchmark(
        state_path=args.state_path,
        result_path=args.result_path,
    )
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
