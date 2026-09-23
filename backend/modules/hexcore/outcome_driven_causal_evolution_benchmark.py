from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict

from backend.modules.hexcore.outcome_driven_causal_evolution import (
    OutcomeDrivenCausalEvolution,
    ProceduralCausalWorldGenerator,
)
from backend.modules.hexcore.persistent_learning import (
    HexCorePersistentLearningRuntime,
)


def _allow(goal: str) -> Dict[str, Any]:
    return {
        "allow_learn": True,
        "deny_reason": None,
        "goal": goal,
        "source": "outcome_evolution_benchmark_authority",
        "S": 1.0,
        "H": 0.0,
    }


def _summary(result: Dict[str, Any]) -> Dict[str, Any]:
    return {
        key: value for key, value in result.items()
        if key != "rows"
    }


def run_outcome_evolution_benchmark(
    *,
    state_path: Path,
    result_path: Path | None = None,
    development_worlds: int = 12,
    sealed_worlds: int = 16,
    development_episodes: int = 40,
    sealed_episodes: int = 60,
) -> Dict[str, Any]:
    if state_path.exists():
        state_path.unlink()
    runtime = HexCorePersistentLearningRuntime(
        state_path=state_path,
        authority_provider=_allow,
    )
    evolution = OutcomeDrivenCausalEvolution(runtime)
    generator = ProceduralCausalWorldGenerator()
    development = generator.generate(
        seed=79_220_501,
        count=development_worlds,
        cohort="development",
    )
    sealed = generator.generate(
        seed=79_220_777,
        count=sealed_worlds,
        cohort="sealed",
    )
    development_ids = {
        world.spec.domain_id for world in development
    }
    sealed_ids = {world.spec.domain_id for world in sealed}
    champion_development = evolution.evaluate_policy(
        policy=evolution.CHAMPION,
        worlds=development,
        episodes_per_world=development_episodes,
        seed_offset=200_000,
    )
    mutations = evolution.mutate_from_outcomes(
        champion_development
    )
    challenger_development = [
        evolution.evaluate_policy(
            policy=policy,
            worlds=development,
            episodes_per_world=development_episodes,
            seed_offset=200_000,
        )
        for policy in mutations
    ]
    selected_development = max(
        challenger_development,
        key=lambda result: (
            result["score"],
            result["worst_family_goal_success"],
            -result["average_experiments"],
        ),
    )
    selected_policy = next(
        policy for policy in mutations
        if policy.policy_id
        == selected_development["policy"]["policy_id"]
    )
    mutation_record = evolution.persist_development_outcomes(
        champion=champion_development,
        challengers=challenger_development,
        selected_policy=selected_policy,
    )

    # The sealed cohort is opened only after development selection.
    champion_sealed = evolution.evaluate_policy(
        policy=evolution.CHAMPION,
        worlds=sealed,
        episodes_per_world=sealed_episodes,
        seed_offset=500_000,
    )
    challenger_sealed = evolution.evaluate_policy(
        policy=selected_policy,
        worlds=sealed,
        episodes_per_world=sealed_episodes,
        seed_offset=500_000,
    )
    gate = evolution.promotion_gate(
        champion=champion_sealed,
        challenger=challenger_sealed,
    )
    promotion = evolution.promote(
        champion_result=champion_sealed,
        challenger_result=challenger_sealed,
        gate=gate,
    )
    restarted = HexCorePersistentLearningRuntime(
        state_path=state_path,
        authority_provider=_allow,
    )
    retained = restarted.skills.champion(
        "causal_investigation_policy"
    )
    result = {
        "schema_version": (
            "aion.hexcore.outcome_driven_causal_evolution.v1"
        ),
        "benchmark": (
            "procedural_world_outcome_memory_and_policy_mutation"
        ),
        "language_provider_used": False,
        "world_generation": {
            "development_worlds": development_worlds,
            "sealed_worlds": sealed_worlds,
            "development_episodes_per_world": (
                development_episodes
            ),
            "sealed_episodes_per_world": sealed_episodes,
            "factor_counts": [1, 2, 3],
            "probe_reliabilities": [0.75, 0.80, 0.85, 0.90, 0.95],
            "goal_reliabilities": [0.90, 0.95, 0.98, 0.99],
            "goal_patterns_include_dont_care": True,
            "symbol_vocabularies_generated": True,
            "development_sealed_identity_overlap": len(
                development_ids & sealed_ids
            ),
        },
        "development": {
            "champion": _summary(champion_development),
            "challengers": [
                _summary(row) for row in challenger_development
            ],
            "selected_policy": selected_policy.to_dict(),
            "mutation_record": mutation_record,
        },
        "sealed_evaluation": {
            "champion": _summary(champion_sealed),
            "challenger": _summary(challenger_sealed),
            "gate": gate,
        },
        "promotion": promotion,
        "restart": {
            "champion_retained": retained is not None,
            "champion_id": (
                retained.get("procedure_id") if retained else None
            ),
            "retained_steps": (
                retained.get("steps") if retained else None
            ),
            "failure_queue_records": sum(
                len(rows)
                for rows in restarted.store.state[
                    "failure_queues"
                ].values()
            ),
            "mutation_cycles": len(
                restarted.store.state[
                    "procedure_mutation_cycles"
                ]
            ),
            "relearning_worlds": 0,
        },
        "gates": {
            "development_and_sealed_worlds_disjoint": (
                not development_ids & sealed_ids
            ),
            "failure_taxonomy_recorded": bool(
                champion_development["failure_counts"]
            ),
            "challengers_created_from_outcomes": bool(mutations),
            "sealed_mean_goal_improved": (
                gate["mean_goal_gain"] >= 0.03
            ),
            "sealed_worst_family_not_regressed": (
                gate["worst_family_goal_gain"] >= 0.0
            ),
            "sealed_factor_accuracy_not_regressed": (
                gate["mean_factor_accuracy_gain"] >= 0.0
            ),
            "complexity_bounded": (
                selected_policy.complexity <= 8
                and selected_policy.maximum_experiments <= 10
            ),
            "challenger_promoted": (
                promotion["challenger_promotion"].get(
                    "promoted"
                )
                is True
            ),
            "restart_retention": bool(
                retained
                and retained.get("procedure_id")
                == promotion["challenger"]["procedure_id"]
            ),
        },
        "boundary_statement": (
            "This is a governed discrete procedure-mutation loop over generated "
            "bounded causal worlds. It does not modify source code, invent new "
            "operators, or perform unrestricted autonomous self-improvement."
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
        default=Path(
            "data/hexcore/outcome_driven_causal_evolution.json"
        ),
    )
    parser.add_argument(
        "--result-path",
        type=Path,
        default=Path(
            "results/hexcore_outcome_driven_causal_evolution.json"
        ),
    )
    args = parser.parse_args()
    result = run_outcome_evolution_benchmark(
        state_path=args.state_path,
        result_path=args.result_path,
    )
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()

