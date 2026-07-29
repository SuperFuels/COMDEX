from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict

from backend.modules.hexcore.cross_domain_causal_transfer import (
    CausalDomainSpec,
    CrossDomainCausalTransferRuntime,
)
from backend.modules.hexcore.persistent_learning import (
    HexCorePersistentLearningRuntime,
)


DOMAINS = [
    CausalDomainSpec(
        domain_id="aster_lock",
        signal_targets=("aura",),
        toggle_actions=("invert",),
        probe_actions=("listen",),
        goal_action="seal",
        goal_pattern_by_signal=(1,),
    ),
    CausalDomainSpec(
        domain_id="reef_gate",
        signal_targets=("tide_mark", "salt_mark"),
        toggle_actions=("turn_tide", "turn_salt"),
        probe_actions=("sample_tide", "sample_salt"),
        goal_action="release",
        goal_pattern_by_signal=(1, 1),
    ),
    CausalDomainSpec(
        domain_id="orbital_latch",
        signal_targets=("phase_echo", "spin_echo"),
        toggle_actions=("phase_kick", "spin_kick"),
        probe_actions=("phase_scan", "spin_scan"),
        goal_action="dock",
        goal_pattern_by_signal=(1, 0),
    ),
]


def _allow(goal: str) -> Dict[str, Any]:
    return {
        "allow_learn": True,
        "deny_reason": None,
        "goal": goal,
        "source": "cross_domain_transfer_benchmark_authority",
        "S": 1.0,
        "H": 0.0,
    }


def run_cross_domain_transfer_benchmark(
    *,
    state_path: Path,
    result_path: Path | None = None,
    audit_episodes: int = 60,
) -> Dict[str, Any]:
    if state_path.exists():
        state_path.unlink()
    runtime = HexCorePersistentLearningRuntime(
        state_path=state_path,
        authority_provider=_allow,
    )
    transfer = CrossDomainCausalTransferRuntime(runtime)
    domain_results = [
        transfer.learn_domain(spec=spec) for spec in DOMAINS
    ]
    audits = [
        transfer.audit_planning(
            spec=spec,
            episodes=audit_episodes,
            seed_offset=120_000 + index * 10_000,
        )
        for index, spec in enumerate(DOMAINS)
    ]
    promotion = transfer.promote_abstract_procedure(
        domain_results=domain_results,
        audits=audits,
    )

    restarted = HexCorePersistentLearningRuntime(
        state_path=state_path,
        authority_provider=_allow,
    )
    champion = restarted.skills.champion(
        "cross_domain_causal_investigation_and_planning"
    )
    reductions = [
        row["experiment_reduction"] for row in domain_results
    ]
    goal_rates = [row["goal_success_rate"] for row in audits]
    factor_rates = [row["factor_accuracy"] for row in audits]
    average_runtime_experiments = [
        row["average_experiments"] for row in audits
    ]
    result = {
        "schema_version": (
            "aion.hexcore.cross_domain_causal_transfer_benchmark.v1"
        ),
        "benchmark": "cross_domain_causal_operator_transfer",
        "language_provider_used": False,
        "symbol_dictionary_supplied": False,
        "domain_count": len(DOMAINS),
        "domains": domain_results,
        "planning_audits": {
            spec.domain_id: audit
            for spec, audit in zip(DOMAINS, audits)
        },
        "skill": promotion,
        "restart": {
            "abstract_champion_retained": champion is not None,
            "retained_steps": champion.get("steps") if champion else None,
            "domain_graphs_retained": all(
                spec.domain_id
                in restarted.store.state["causal_graphs"]
                for spec in DOMAINS
            ),
            "relearning_experiments": 0,
        },
        "aggregate": {
            "mean_structure_experiment_reduction": (
                sum(reductions) / len(reductions)
            ),
            "minimum_structure_experiment_reduction": min(
                reductions
            ),
            "mean_factor_accuracy": (
                sum(factor_rates) / len(factor_rates)
            ),
            "minimum_factor_accuracy": min(factor_rates),
            "mean_goal_success": (
                sum(goal_rates) / len(goal_rates)
            ),
            "minimum_goal_success": min(goal_rates),
            "mean_runtime_experiments": (
                sum(average_runtime_experiments)
                / len(average_runtime_experiments)
            ),
        },
        "gates": {
            "all_transfer_structures_correct": all(
                row["transfer"]["structure_correct"]
                for row in domain_results
            ),
            "all_cold_structures_correct": all(
                row["cold"]["structure_correct"]
                for row in domain_results
            ),
            "minimum_50_percent_structure_experiment_reduction": (
                min(reductions) >= 0.50
            ),
            "minimum_85_percent_factor_accuracy": (
                min(factor_rates) >= 0.85
            ),
            "minimum_85_percent_goal_success": (
                min(goal_rates) >= 0.85
            ),
            "abstract_skill_promoted": (
                promotion["promotion"].get("promoted") is True
            ),
            "restart_retention": bool(
                champion
                and all(
                    spec.domain_id
                    in restarted.store.state["causal_graphs"]
                    for spec in DOMAINS
                )
            ),
        },
        "boundary_statement": (
            "This demonstrates transfer of a fixed causal-operator procedure "
            "across three generated symbol families and two bounded graph "
            "shapes. It is not unrestricted cross-domain intelligence."
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
        default=Path("data/hexcore/cross_domain_causal.json"),
    )
    parser.add_argument(
        "--result-path",
        type=Path,
        default=Path(
            "results/hexcore_cross_domain_causal_benchmark.json"
        ),
    )
    parser.add_argument("--audit-episodes", type=int, default=60)
    args = parser.parse_args()
    result = run_cross_domain_transfer_benchmark(
        state_path=args.state_path,
        result_path=args.result_path,
        audit_episodes=args.audit_episodes,
    )
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()

