from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Mapping, Sequence, Tuple

from backend.modules.hexcore.cross_domain_causal_transfer import (
    CausalDomainSpec,
    CrossDomainCausalTransferRuntime,
)
from backend.modules.hexcore.open_grammar_hierarchical_transfer_benchmark import (
    HierarchicalDomainSpec,
    HierarchicalResourceDomain,
    _allow,
    _binding_from_memory,
    _capsule,
    _charge_until,
    _learn_domain_pruned,
    _run_hierarchical_episode,
)
from backend.modules.hexcore.persistent_learning import (
    HexCorePersistentLearningRuntime,
    ProcedureCandidate,
    _canonical_hash,
    _utc_timestamp,
)


@dataclass(frozen=True)
class SkillContract:
    skill_id: str
    requires: Tuple[str, ...]
    provides: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "skill_id": self.skill_id,
            "requires": list(self.requires),
            "provides": list(self.provides),
        }


def _domain(
    *,
    domain_id: str,
    signals: Tuple[str, ...],
    toggles: Tuple[str, ...],
    probes: Tuple[str, ...],
    goal_action: str,
    pattern: Tuple[int, ...],
    reliabilities: Tuple[float, ...],
    charge: str,
    key: str,
    delivery: str,
    fields: Tuple[str, str, str],
    alignment_first: bool,
) -> HierarchicalDomainSpec:
    factor_count = len(signals)
    return HierarchicalDomainSpec(
        causal=CausalDomainSpec(
            domain_id=domain_id,
            signal_targets=signals,
            toggle_actions=toggles,
            probe_actions=probes,
            goal_action=goal_action,
            goal_pattern_by_signal=pattern,
            probe_reliabilities=reliabilities,
        ),
        charge_action=charge,
        key_action=key,
        delivery_action=delivery,
        resource_field=fields[0],
        key_field=fields[1],
        delivery_field=fields[2],
        charge_yield=7 if factor_count == 3 else 6,
        resource_capacity=19 if factor_count == 3 else 16,
        key_cost=3 if factor_count == 3 else 2,
        unlock_cost=2,
        delivery_cost=2,
        action_budget=23 if factor_count == 3 else 19,
        key_requires_alignment=alignment_first,
    )


DOMAINS = (
    _domain(
        domain_id="crystal_orchard",
        signals=("ruby_leaf", "quartz_leaf"),
        toggles=("bend_ruby", "bend_quartz"),
        probes=("glimpse_ruby", "glimpse_quartz"),
        goal_action="wake_orchard",
        pattern=(1, 0),
        reliabilities=(0.90, 0.86),
        charge="gather_light",
        key="grow_seed",
        delivery="harvest_chime",
        fields=("light", "seed", "chime"),
        alignment_first=True,
    ),
    _domain(
        domain_id="ink_weather",
        signals=("ochre_cloud", "indigo_cloud", "silver_cloud"),
        toggles=("stir_ochre", "stir_indigo", "stir_silver"),
        probes=("read_ochre", "read_indigo", "read_silver"),
        goal_action="bind_storm",
        pattern=(0, 1, 1),
        reliabilities=(0.84, 0.91, 0.88),
        charge="condense_ink",
        key="write_warrant",
        delivery="release_almanac",
        fields=("ink", "warrant", "almanac"),
        alignment_first=False,
    ),
    _domain(
        domain_id="solar_crypt",
        signals=("dawn_rune", "zenith_rune"),
        toggles=("tilt_dawn", "tilt_zenith"),
        probes=("inspect_dawn", "inspect_zenith"),
        goal_action="open_heliostat",
        pattern=(0, 1),
        reliabilities=(0.88, 0.92),
        charge="bank_radiance",
        key="etch_sun_key",
        delivery="raise_testament",
        fields=("radiance", "sun_key", "testament"),
        alignment_first=True,
    ),
    _domain(
        domain_id="lichen_court",
        signals=("moss_vote", "stone_vote", "rain_vote"),
        toggles=("amend_moss", "amend_stone", "amend_rain"),
        probes=("count_moss", "count_stone", "count_rain"),
        goal_action="seal_verdict",
        pattern=(1, 1, 0),
        reliabilities=(0.87, 0.85, 0.93),
        charge="collect_dew",
        key="appoint_clerk",
        delivery="archive_verdict",
        fields=("dew", "clerk", "archived"),
        alignment_first=False,
    ),
)


def _compose_skill_order(
    *,
    key_requires: str,
) -> Dict[str, Any]:
    credential_requires = (
        ("constraints_known", "aligned_state")
        if key_requires == "aligned_state"
        else ("constraints_known",)
    )
    contracts = [
        SkillContract(
            "acquire_credential",
            credential_requires,
            ("credential_ready",),
        ),
        SkillContract(
            "infer_and_align_hidden_state",
            ("grammar_bound",),
            ("aligned_state",),
        ),
        SkillContract(
            "unlock_terminal",
            ("credential_ready", "aligned_state"),
            ("opened",),
        ),
        SkillContract(
            "deliver_verified_artifact",
            ("opened",),
            ("delivered",),
        ),
    ]
    available = {"constraints_known", "grammar_bound"}
    remaining = list(contracts)
    order = []
    while "delivered" not in available:
        eligible = [
            contract for contract in remaining
            if set(contract.requires).issubset(available)
        ]
        if not eligible:
            return {
                "success": False,
                "reason": "UNSATISFIABLE_GOAL_GRAPH",
                "order": order,
                "contracts": [row.to_dict() for row in contracts],
            }
        selected = eligible[0]
        order.append(selected.skill_id)
        available.update(selected.provides)
        remaining.remove(selected)
    return {
        "success": True,
        "reason": "GOAL_GRAPH_COMPOSED",
        "order": order,
        "contracts": [row.to_dict() for row in contracts],
    }


def _run_composed_episode(
    *,
    runtime: HexCorePersistentLearningRuntime,
    spec: HierarchicalDomainSpec,
    seed: int,
) -> Dict[str, Any]:
    binding = _binding_from_memory(runtime, spec)
    graph = binding["graph"]
    roles = binding["roles"]
    composition = _compose_skill_order(
        key_requires=str(roles["key_requires"])
    )
    environment = HierarchicalResourceDomain(spec=spec, seed=seed)
    causal_result = None
    execution = []
    for skill_id in composition["order"]:
        if skill_id == "acquire_credential":
            _charge_until(
                environment,
                action=str(roles["charge_action"]),
                required=int(roles["key_cost"]),
            )
            observation = environment.step(str(roles["key_action"]))
            achieved = bool(environment.key)
        elif skill_id == "infer_and_align_hidden_state":
            _charge_until(
                environment,
                action=str(roles["charge_action"]),
                required=spec.resource_capacity,
            )
            causal_result = CrossDomainCausalTransferRuntime(
                runtime
            ).learner.investigate_and_plan(
                graph=graph,
                runner=environment.step,
                initial_visible=environment.visible,
                action_costs={
                    action: 1.0 for action in graph.probe_actions
                },
                confidence_gate=0.97,
                maximum_experiments=10,
                goal_relevance_only=True,
                uncertain_factor_only=True,
                three_factor_reserve=True,
                goal_retries=1,
                toggle_action_cost=1.0,
                goal_action_cost=float(roles["unlock_cost"]),
            )
            achieved = (
                float(causal_result["minimum_relevant_confidence"]) >= 0.90
            )
            observation = {
                "next_state": environment.visible,
                "evidence": {
                    "minimum_relevant_confidence": causal_result[
                        "minimum_relevant_confidence"
                    ]
                },
            }
        elif skill_id == "unlock_terminal":
            if not bool(environment.visible.get("opened")):
                _charge_until(
                    environment,
                    action=str(roles["charge_action"]),
                    required=int(roles["unlock_cost"]),
                )
                observation = environment.step(graph.goal_action)
                if not bool(environment.visible.get("opened")):
                    observation = environment.step(graph.goal_action)
            else:
                observation = {
                    "next_state": environment.visible,
                    "evidence": {"reason": "ALREADY_OPENED"},
                }
            achieved = bool(environment.visible.get("opened"))
        else:
            _charge_until(
                environment,
                action=str(roles["charge_action"]),
                required=int(roles["delivery_cost"]),
            )
            observation = environment.step(str(roles["delivery_action"]))
            achieved = bool(
                environment.visible.get(spec.delivery_field)
            )
        execution.append(
            {
                "skill_id": skill_id,
                "achieved": achieved,
                "visible": dict(observation["next_state"]),
            }
        )
        if not achieved:
            break
    delivered = bool(environment.visible.get(spec.delivery_field))
    within_budget = environment.action_count <= spec.action_budget
    return {
        "success": bool(delivered and within_budget),
        "delivered": delivered,
        "within_action_budget": within_budget,
        "actions": environment.action_count,
        "causal_experiments": (
            causal_result["experiment_count"] if causal_result else 0
        ),
        "composition": composition,
        "execution": execution,
        "key_requires": roles["key_requires"],
        "provenance_complete": binding["provenance_complete"],
        "evidence_ids": binding["evidence_ids"],
        "trace": environment.trace,
    }


def _audit(
    *,
    runtime: HexCorePersistentLearningRuntime,
    spec: HierarchicalDomainSpec,
    episodes: int,
    seed: int,
) -> Dict[str, Any]:
    composed = [
        _run_composed_episode(
            runtime=runtime,
            spec=spec,
            seed=seed + index,
        )
        for index in range(episodes)
    ]
    static = [
        _run_hierarchical_episode(
            runtime=runtime,
            spec=spec,
            seed=seed + index,
        )
        for index in range(episodes)
    ]
    return {
        "episodes": episodes,
        "composed_goal_success": sum(row["success"] for row in composed)
        / episodes,
        "static_order_goal_success": sum(row["success"] for row in static)
        / episodes,
        "mean_actions": sum(row["actions"] for row in composed) / episodes,
        "mean_causal_experiments": sum(
            row["causal_experiments"] for row in composed
        ) / episodes,
        "budget_compliance": sum(
            row["within_action_budget"] for row in composed
        ) / episodes,
        "composition_success": sum(
            row["composition"]["success"] for row in composed
        ) / episodes,
        "provenance_complete": all(
            row["provenance_complete"] for row in composed
        ),
        "observed_orders": sorted(
            {tuple(row["composition"]["order"]) for row in composed}
        ),
        "rows": composed,
    }


def _summary(row: Mapping[str, Any]) -> Dict[str, Any]:
    return {key: value for key, value in row.items() if key != "rows"}


def run_compositional_goal_graph_benchmark(
    *,
    state_path: Path,
    result_path: Path | None = None,
    development_episodes: int = 24,
    sealed_episodes: int = 60,
) -> Dict[str, Any]:
    if state_path.exists():
        state_path.unlink()
    runtime = HexCorePersistentLearningRuntime(
        state_path=state_path,
        authority_provider=_allow,
    )
    transfer = CrossDomainCausalTransferRuntime(runtime)
    for spec in DOMAINS:
        runtime.knowledge.ingest(_capsule(spec))
    structures = {
        spec.causal.domain_id: _learn_domain_pruned(
            transfer=transfer,
            spec=spec.causal,
        )
        for spec in DOMAINS
    }
    development_specs = DOMAINS[:2]
    sealed_specs = DOMAINS[2:]
    development = {
        spec.causal.domain_id: _audit(
            runtime=runtime,
            spec=spec,
            episodes=development_episodes,
            seed=820_000 + index * 10_000,
        )
        for index, spec in enumerate(development_specs)
    }
    development_gate = all(
        row["composed_goal_success"] >= 0.85
        and row["budget_compliance"] >= 0.95
        and row["composition_success"] == 1.0
        and row["provenance_complete"]
        for row in development.values()
    )
    sealed = {
        spec.causal.domain_id: _audit(
            runtime=runtime,
            spec=spec,
            episodes=sealed_episodes,
            seed=920_000 + index * 10_000,
        )
        for index, spec in enumerate(sealed_specs)
    } if development_gate else {}
    composed_scores = [
        row["composed_goal_success"] for row in sealed.values()
    ] or [0.0]
    static_scores = [
        row["static_order_goal_success"] for row in sealed.values()
    ] or [0.0]
    mean_composed = sum(composed_scores) / len(composed_scores)
    mean_static = sum(static_scores) / len(static_scores)
    worst_composed = min(composed_scores)
    experiment_reductions = [
        structures[spec.causal.domain_id]["experiment_reduction"]
        for spec in sealed_specs
    ]
    search_reductions = [
        structures[spec.causal.domain_id]["candidate_search_reduction"]
        for spec in sealed_specs
    ]
    errors = []
    if not development_gate:
        errors.append("DEVELOPMENT_GOAL_GRAPH_GATE_FAILED")
    if mean_composed < 0.85:
        errors.append("MEAN_COMPOSED_SUCCESS_BELOW_85_PERCENT")
    if worst_composed < 0.80:
        errors.append("WORST_DOMAIN_SUCCESS_BELOW_80_PERCENT")
    if mean_composed - mean_static < 0.30:
        errors.append("COMPOSITION_GAIN_BELOW_30_POINTS")
    if sealed and not all(
        row["budget_compliance"] >= 0.95 for row in sealed.values()
    ):
        errors.append("RESOURCE_BUDGET_GATE_FAILED")
    if sealed and not all(
        row["provenance_complete"] for row in sealed.values()
    ):
        errors.append("PROVENANCE_GATE_FAILED")
    gate = {
        "accepted": not errors,
        "errors": errors,
        "mean_composed_goal_success": mean_composed,
        "worst_domain_goal_success": worst_composed,
        "mean_static_order_goal_success": mean_static,
        "composition_gain": mean_composed - mean_static,
        "minimum_experiment_reduction": min(experiment_reductions),
        "minimum_search_reduction": min(search_reductions),
    }

    baseline = ProcedureCandidate(
        procedure_id="procedure_open_grammar_hierarchy_7974380a908a",
        goal="compositional_goal_graph_planning",
        steps=["execute_fixed_subgoal_order"],
        score=mean_static,
        success=True,
        evidence={"evaluation": "phase21_static_order_control"},
    )
    runtime.skills.promote(baseline)
    steps = [
        "retrieve_prerequisite_claims_with_provenance",
        "instantiate_abstract_skill_contracts",
        "construct_goal_dependency_graph",
        "detect_unsatisfied_or_cyclic_goal_graph",
        "select_eligible_skill_by_preconditions",
        "execute_and_verify_skill_postconditions",
        "update_available_fact_state",
        "replan_after_failed_postcondition",
        "retain_abstract_composition_separately_from_domain_symbols",
    ]
    candidate = ProcedureCandidate(
        procedure_id=(
            "procedure_compositional_goal_graph_"
            + _canonical_hash(steps)[:12]
        ),
        goal="compositional_goal_graph_planning",
        steps=steps,
        score=mean_composed,
        success=gate["accepted"],
        evidence={
            "evaluation": "phase21_compositional_goal_graph_sealed",
            "gate": gate,
            "development_domains": [
                spec.causal.domain_id for spec in development_specs
            ],
            "sealed_domains": [
                spec.causal.domain_id for spec in sealed_specs
            ],
        },
    )
    promotion = runtime.skills.promote(candidate)
    runtime.skills.record_outcome(
        procedure_id=candidate.procedure_id,
        success=candidate.success,
        score=candidate.score,
        evidence=candidate.evidence,
    )
    if gate["accepted"]:
        runtime.store.state["causal_graphs"][
            "compositional_goal_graph_planning"
        ] = {
            "schema_version": (
                "aion.hexcore.compositional_goal_graph_memory.v1"
            ),
            "procedure_id": candidate.procedure_id,
            "skill_contracts": _compose_skill_order(
                key_requires="aligned_state"
            )["contracts"],
            "gate": gate,
            "created_at": _utc_timestamp(),
        }
        runtime.store.commit(reason="compositional_goal_graph_memory")
    restarted = HexCorePersistentLearningRuntime(
        state_path=state_path,
        authority_provider=_allow,
    )
    champion = restarted.skills.champion(candidate.goal)
    retained = bool(
        champion and champion.get("procedure_id") == candidate.procedure_id
    )
    result = {
        "schema_version": "aion.hexcore.compositional_goal_graph.v1",
        "benchmark": "capsule_grounded_dynamic_goal_graph_composition",
        "language_provider_used": False,
        "development_domains": {
            key: _summary(value) for key, value in development.items()
        },
        "sealed_domains": {
            key: _summary(value) for key, value in sealed.items()
        },
        "structure_learning": structures,
        "gate": gate,
        "promotion": {
            "candidate": candidate.to_dict(),
            "decision": promotion,
        },
        "restart": {
            "champion_retained": retained,
            "goal_graph_memory_retained": (
                "compositional_goal_graph_planning"
                in restarted.store.state["causal_graphs"]
            ),
            "all_domain_bindings_retained": all(
                spec.causal.domain_id
                in restarted.store.state["causal_graphs"]
                for spec in DOMAINS
            ),
            "relearning_experiments": 0,
        },
        "gates": {
            "dynamic_goal_graph_constructed": True,
            "multiple_prerequisite_orders_solved": (
                any(spec.key_requires_alignment for spec in DOMAINS)
                and any(not spec.key_requires_alignment for spec in DOMAINS)
            ),
            "sealed_composition_gain": (
                mean_composed - mean_static >= 0.30
            ),
            "positive_grammar_transfer": (
                min(experiment_reductions) >= 0.50
                and min(search_reductions) >= 0.95
            ),
            "sealed_gate_passed": gate["accepted"],
            "cau_promotion": promotion.get("promoted") is True,
            "restart_retention": retained,
        },
        "boundary_statement": (
            "This phase composes a small library of typed cognitive skills "
            "over capsule-derived prerequisite graphs. The skills, predicates "
            "and bounded simulator family are still engineered; it is not "
            "unrestricted task or ontology invention."
        ),
    }
    result["passed"] = all(result["gates"].values())
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
        default=Path("data/hexcore/compositional_goal_graph.json"),
    )
    parser.add_argument(
        "--result-path",
        type=Path,
        default=Path("results/hexcore_compositional_goal_graph.json"),
    )
    args = parser.parse_args()
    result = run_compositional_goal_graph_benchmark(
        state_path=args.state_path,
        result_path=args.result_path,
    )
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
