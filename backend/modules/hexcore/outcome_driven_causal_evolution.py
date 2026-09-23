from __future__ import annotations

import random
import uuid
from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Mapping, Sequence, Tuple

from backend.modules.hexcore.cross_domain_causal_transfer import (
    CausalDomainSpec,
    NamedStochasticLatentDomain,
)
from backend.modules.hexcore.persistent_learning import (
    HexCorePersistentLearningRuntime,
    ProcedureCandidate,
    _canonical_hash,
    _json_safe,
    _utc_timestamp,
)
from backend.modules.hexcore.stochastic_multilatent_discovery import (
    GovernedStochasticMultiLatentLearner,
    StochasticLatentGraph,
)


@dataclass(frozen=True)
class InvestigationPolicy:
    policy_id: str
    confidence_gate: float
    maximum_experiments: int
    cost_weight: float
    mutation: str
    parent_policy_id: str | None = None
    goal_relevance_only: bool = False
    uncertain_factor_only: bool = False
    goal_retries: int = 0
    adaptive_confidence: bool = False
    reliability_slope: float = 0.0
    adaptive_experiment_budget: bool = False
    low_reliability_budget: int = 10
    high_reliability_budget: int = 5
    online_reliability_learning: bool = False
    reliability_prior: float = 0.80
    value_of_information_ratio: bool = False
    three_factor_reserve: bool = False
    minimum_voi_per_cost: float = 0.0
    policy_bank_enabled: bool = False
    router_low_reliability_threshold: float = 0.75
    router_high_reliability_threshold: float = 0.85

    @property
    def complexity(self) -> int:
        # Three independently mutable controls plus the fixed five-step
        # abstract procedure inherited from Phase 7.
        return (
            8
            + int(
                self.goal_relevance_only
                or self.uncertain_factor_only
            )
            + int(self.goal_retries > 0)
            + int(self.adaptive_confidence)
            + int(self.adaptive_experiment_budget)
            + int(self.online_reliability_learning)
            + int(self.value_of_information_ratio)
            + int(self.three_factor_reserve)
            + int(self.minimum_voi_per_cost > 0.0)
            + int(self.policy_bank_enabled)
        )

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self) | {"complexity": self.complexity}


@dataclass(frozen=True)
class GeneratedCausalWorld:
    spec: CausalDomainSpec
    probe_costs: Dict[str, float]
    family: str
    graph: StochasticLatentGraph


class ProceduralCausalWorldGenerator:
    """Creates reproducible world families without semantic name hints."""

    NOUNS = (
        "amber",
        "brine",
        "cinder",
        "delta",
        "ember",
        "flux",
        "glint",
        "helix",
        "ion",
        "jade",
        "kepler",
        "lumen",
        "mistral",
        "nova",
        "onyx",
        "prism",
    )

    def generate(
        self,
        *,
        seed: int,
        count: int,
        cohort: str,
    ) -> List[GeneratedCausalWorld]:
        rng = random.Random(seed)
        worlds = []
        for index in range(count):
            factor_count = rng.choice((1, 2, 2, 3))
            words = rng.sample(self.NOUNS, factor_count * 3 + 1)
            prefix = f"{cohort}_{index}_{rng.randrange(100000):05d}"
            signals = tuple(
                f"{prefix}_{words[offset]}_trace"
                for offset in range(factor_count)
            )
            toggles = tuple(
                f"{prefix}_{words[factor_count + offset]}_shift"
                for offset in range(factor_count)
            )
            probes = tuple(
                f"{prefix}_{words[2 * factor_count + offset]}_sample"
                for offset in range(factor_count)
            )
            goal_action = f"{prefix}_{words[-1]}_commit"
            pattern = tuple(
                rng.choice((-1, 0, 1)) for _ in range(factor_count)
            )
            if all(value == -1 for value in pattern):
                replacement = list(pattern)
                replacement[rng.randrange(factor_count)] = rng.randint(0, 1)
                pattern = tuple(replacement)
            probe_reliability = rng.choice((0.75, 0.80, 0.85, 0.90, 0.95))
            goal_reliability = rng.choice((0.90, 0.95, 0.98, 0.99))
            costs = {
                probe: rng.choice((0.05, 0.10, 0.20, 0.35))
                for probe in probes
            }
            spec = CausalDomainSpec(
                domain_id=prefix,
                signal_targets=signals,
                toggle_actions=toggles,
                probe_actions=probes,
                goal_action=goal_action,
                goal_pattern_by_signal=pattern,
                probe_reliability=probe_reliability,
                goal_reliability=goal_reliability,
            )
            graph = StochasticLatentGraph(
                graph_id=(
                    f"generated_graph_"
                    f"{_canonical_hash([seed, index, spec])[:16]}"
                ),
                factor_count=factor_count,
                toggle_actions=toggles,
                signal_targets=signals,
                signal_factor_assignments=tuple(range(factor_count)),
                probe_actions=probes,
                goal_action=goal_action,
                goal_pattern=pattern,
                probe_reliability=probe_reliability,
                goal_reliability=goal_reliability,
            )
            relevant = sum(value != -1 for value in pattern)
            family = (
                f"factors_{factor_count}:"
                f"relevant_{relevant}:"
                f"noise_{int(probe_reliability * 100)}"
            )
            worlds.append(
                GeneratedCausalWorld(
                    spec=spec,
                    probe_costs=costs,
                    family=family,
                    graph=graph,
                )
            )
        return worlds


class OutcomeDrivenCausalEvolution:
    """Mutates governed investigation policies from explicit failure queues."""

    CHAMPION = InvestigationPolicy(
        policy_id="phase7_champion",
        confidence_gate=0.95,
        maximum_experiments=6,
        cost_weight=0.10,
        mutation="immutable_phase7_control",
    )

    def __init__(self, runtime: HexCorePersistentLearningRuntime) -> None:
        self.runtime = runtime
        self.learner = GovernedStochasticMultiLatentLearner(runtime.store)

    @staticmethod
    def _predicted_factors(
        graph: StochasticLatentGraph,
        result: Mapping[str, Any],
    ) -> Tuple[int, ...]:
        predicted = [0] * graph.factor_count
        for signal_index, factor in enumerate(
            graph.signal_factor_assignments
        ):
            predicted[factor] = int(
                result["marginals"][factor]["value"]
            )
        return tuple(predicted)

    @staticmethod
    def _goal_satisfied(
        factors: Sequence[int],
        pattern: Sequence[int],
    ) -> bool:
        return all(
            required == -1 or factors[index] == required
            for index, required in enumerate(pattern)
        )

    def evaluate_policy(
        self,
        *,
        policy: InvestigationPolicy,
        worlds: Sequence[GeneratedCausalWorld],
        episodes_per_world: int,
        seed_offset: int,
    ) -> Dict[str, Any]:
        rows = []
        for world_index, world in enumerate(worlds):
            for episode in range(episodes_per_world):
                environment = NamedStochasticLatentDomain(
                    spec=world.spec,
                    seed=(
                        seed_offset
                        + world_index * 10_000
                        + episode
                    ),
                )
                result = self.learner.investigate_and_plan(
                    graph=world.graph,
                    runner=environment.step,
                    initial_visible=dict(environment.visible),
                    action_costs=world.probe_costs,
                    confidence_gate=policy.confidence_gate,
                    maximum_experiments=policy.maximum_experiments,
                    cost_weight=policy.cost_weight,
                    goal_relevance_only=policy.goal_relevance_only,
                    uncertain_factor_only=policy.uncertain_factor_only,
                    goal_retries=policy.goal_retries,
                    adaptive_confidence=policy.adaptive_confidence,
                    reliability_slope=policy.reliability_slope,
                    adaptive_experiment_budget=(
                        policy.adaptive_experiment_budget
                    ),
                    low_reliability_budget=(
                        policy.low_reliability_budget
                    ),
                    high_reliability_budget=(
                        policy.high_reliability_budget
                    ),
                    online_reliability_learning=(
                        policy.online_reliability_learning
                    ),
                    reliability_prior=policy.reliability_prior,
                    value_of_information_ratio=(
                        policy.value_of_information_ratio
                    ),
                    three_factor_reserve=policy.three_factor_reserve,
                    minimum_voi_per_cost=policy.minimum_voi_per_cost,
                    policy_bank_enabled=policy.policy_bank_enabled,
                    router_low_reliability_threshold=(
                        policy.router_low_reliability_threshold
                    ),
                    router_high_reliability_threshold=(
                        policy.router_high_reliability_threshold
                    ),
                )
                actual = environment.audit_hidden_factors()
                predicted = self._predicted_factors(
                    world.graph, result
                )
                factor_correct = predicted == actual
                relevant = [
                    index for index, required in enumerate(
                        world.spec.goal_pattern_by_signal
                    )
                    if required != -1
                ]
                relevant_factor_correct = all(
                    predicted[index] == actual[index]
                    for index in relevant
                )
                goal_state_correct = self._goal_satisfied(
                    actual, world.spec.goal_pattern_by_signal
                )
                verified_goal_success = bool(
                    result["goal_success"] and goal_state_correct
                )
                actual_reliabilities = (
                    world.spec.probe_reliabilities
                    or tuple(
                        world.spec.probe_reliability
                        for _ in world.spec.probe_actions
                    )
                )
                estimated_reliabilities = result[
                    "estimated_probe_reliabilities"
                ]
                reliability_mae = sum(
                    abs(
                        float(estimated_reliabilities[action])
                        - float(actual_reliabilities[index])
                    )
                    for index, action in enumerate(
                        world.spec.probe_actions
                    )
                ) / len(world.spec.probe_actions)
                confidence = float(
                    result["minimum_relevant_confidence"]
                )
                causes = []
                if not relevant_factor_correct:
                    causes.append("belief_error")
                if not relevant_factor_correct and confidence >= 0.90:
                    causes.append("calibration_error")
                if not goal_state_correct:
                    causes.append("planning_error")
                if goal_state_correct and not result["goal_success"]:
                    causes.append("execution_noise")
                if (
                    result["experiment_count"]
                    >= result["effective_maximum_experiments"]
                ):
                    causes.append("experiment_budget_exhausted")
                if verified_goal_success:
                    causes.append("success")
                rows.append(
                    {
                        "policy_id": policy.policy_id,
                        "world_id": world.spec.domain_id,
                        "family": world.family,
                        "episode": episode,
                        "factor_count": world.spec.factor_count,
                        "probe_reliability": (
                            world.spec.probe_reliability
                        ),
                        "goal_reliability": (
                            world.spec.goal_reliability
                        ),
                        "factor_correct": factor_correct,
                        "relevant_factor_correct": (
                            relevant_factor_correct
                        ),
                        "goal_state_correct": goal_state_correct,
                        "observed_goal_success": bool(
                            result["goal_success"]
                        ),
                        "goal_success": verified_goal_success,
                        "confidence": confidence,
                        "experiment_count": result["experiment_count"],
                        "effective_maximum_experiments": result[
                            "effective_maximum_experiments"
                        ],
                        "goal_attempts": result["goal_attempts"],
                        "toggle_count": result["toggle_count"],
                        "total_action_count": result[
                            "total_action_count"
                        ],
                        "total_action_cost": result[
                            "total_action_cost"
                        ],
                        "reliability_mae": reliability_mae,
                        "selected_specialist": result[
                            "selected_specialist"
                        ],
                        "failure_causes": causes,
                    }
                )
        factor_accuracy = sum(row["factor_correct"] for row in rows) / len(rows)
        relevant_factor_accuracy = sum(
            row["relevant_factor_correct"] for row in rows
        ) / len(rows)
        goal_success = sum(row["goal_success"] for row in rows) / len(rows)
        average_confidence = sum(row["confidence"] for row in rows) / len(rows)
        calibration_error = abs(
            average_confidence - relevant_factor_accuracy
        )
        average_experiments = sum(
            row["experiment_count"] for row in rows
        ) / len(rows)
        average_goal_attempts = sum(
            row["goal_attempts"] for row in rows
        ) / len(rows)
        average_total_actions = sum(
            row["total_action_count"] for row in rows
        ) / len(rows)
        average_total_action_cost = sum(
            row["total_action_cost"] for row in rows
        ) / len(rows)
        mean_reliability_mae = sum(
            row["reliability_mae"] for row in rows
        ) / len(rows)
        by_family: Dict[str, List[Dict[str, Any]]] = {}
        for row in rows:
            by_family.setdefault(row["family"], []).append(row)
        families = {
            name: {
                "episodes": len(group),
                "factor_accuracy": (
                    sum(row["factor_correct"] for row in group)
                    / len(group)
                ),
                "goal_success": (
                    sum(row["goal_success"] for row in group)
                    / len(group)
                ),
                "average_experiments": (
                    sum(row["experiment_count"] for row in group)
                    / len(group)
                ),
                "average_total_action_cost": (
                    sum(row["total_action_cost"] for row in group)
                    / len(group)
                ),
            }
            for name, group in by_family.items()
        }
        failure_counts: Dict[str, int] = {}
        specialist_counts: Dict[str, int] = {}
        for row in rows:
            specialist = row["selected_specialist"]
            specialist_counts[specialist] = (
                specialist_counts.get(specialist, 0) + 1
            )
            for cause in row["failure_causes"]:
                if cause != "success":
                    failure_counts[cause] = (
                        failure_counts.get(cause, 0) + 1
                    )
        score = (
            goal_success
            + 0.20 * factor_accuracy
            - 0.02 * average_experiments
            - 0.20 * calibration_error
        )
        return {
            "policy": policy.to_dict(),
            "worlds": len(worlds),
            "episodes": len(rows),
            "mean_factor_accuracy": factor_accuracy,
            "mean_relevant_factor_accuracy": relevant_factor_accuracy,
            "mean_goal_success": goal_success,
            "average_confidence": average_confidence,
            "calibration_error": calibration_error,
            "average_experiments": average_experiments,
            "average_goal_attempts": average_goal_attempts,
            "average_total_actions": average_total_actions,
            "average_total_action_cost": average_total_action_cost,
            "mean_reliability_mae": mean_reliability_mae,
            "worst_family_factor_accuracy": min(
                row["factor_accuracy"] for row in families.values()
            ),
            "worst_family_goal_success": min(
                row["goal_success"] for row in families.values()
            ),
            "families": families,
            "failure_counts": failure_counts,
            "specialist_counts": specialist_counts,
            "score": score,
            "rows": rows,
        }

    def mutate_from_outcomes(
        self,
        champion_result: Mapping[str, Any],
    ) -> List[InvestigationPolicy]:
        failures = champion_result["failure_counts"]
        belief_pressure = (
            failures.get("belief_error", 0)
            + failures.get("calibration_error", 0)
        )
        cost_pressure = failures.get("experiment_budget_exhausted", 0)
        mutations = []
        if belief_pressure > 0:
            mutations.extend(
                [
                    InvestigationPolicy(
                        policy_id="challenger_high_confidence",
                        confidence_gate=0.98,
                        maximum_experiments=10,
                        cost_weight=0.05,
                        mutation=(
                            "raise_confidence_and_budget_after_belief_failures"
                        ),
                        parent_policy_id=self.CHAMPION.policy_id,
                    ),
                    InvestigationPolicy(
                        policy_id="challenger_balanced_robust",
                        confidence_gate=0.97,
                        maximum_experiments=8,
                        cost_weight=0.05,
                        mutation=(
                            "moderate_confidence_with_two_extra_probes"
                        ),
                        parent_policy_id=self.CHAMPION.policy_id,
                    ),
                ]
            )
        if cost_pressure > 0:
            mutations.append(
                InvestigationPolicy(
                    policy_id="challenger_cost_aware",
                    confidence_gate=0.97,
                    maximum_experiments=9,
                    cost_weight=0.20,
                    mutation=(
                        "increase_cost_penalty_while_extending_budget"
                    ),
                    parent_policy_id=self.CHAMPION.policy_id,
                )
            )
        mutations.append(
            InvestigationPolicy(
                policy_id="challenger_efficient",
                confidence_gate=0.90,
                maximum_experiments=5,
                cost_weight=0.08,
                mutation="lower_budget_efficiency_control",
                parent_policy_id=self.CHAMPION.policy_id,
            )
        )
        return mutations

    def persist_development_outcomes(
        self,
        *,
        champion: Mapping[str, Any],
        challengers: Sequence[Mapping[str, Any]],
        selected_policy: InvestigationPolicy,
    ) -> Dict[str, Any]:
        before = self.runtime.store.prepare_mutation()
        try:
            for result in [champion, *challengers]:
                policy_id = result["policy"]["policy_id"]
                for row in result["rows"]:
                    for cause in row["failure_causes"]:
                        if cause == "success":
                            continue
                        self.runtime.store.state[
                            "failure_queues"
                        ].setdefault(cause, []).append(
                            {
                                "schema_version": (
                                    "aion.hexcore.procedure_failure.v1"
                                ),
                                "policy_id": policy_id,
                                "world_id": row["world_id"],
                                "family": row["family"],
                                "cause": cause,
                                "confidence": row["confidence"],
                                "experiment_count": (
                                    row["experiment_count"]
                                ),
                            }
                        )
            cycle = {
                "schema_version": (
                    "aion.hexcore.procedure_mutation_cycle.v1"
                ),
                "cycle_id": f"mutation_{uuid.uuid4().hex[:16]}",
                "parent_policy": champion["policy"],
                "parent_failure_counts": champion["failure_counts"],
                "challengers": [
                    {
                        "policy": row["policy"],
                        "score": row["score"],
                        "mean_goal_success": row[
                            "mean_goal_success"
                        ],
                        "worst_family_goal_success": row[
                            "worst_family_goal_success"
                        ],
                    }
                    for row in challengers
                ],
                "selected_development_policy": (
                    selected_policy.to_dict()
                ),
                "timestamp": _utc_timestamp(),
            }
            self.runtime.store.state[
                "procedure_mutation_cycles"
            ].append(cycle)
            commit = self.runtime.store.commit(
                reason=f"procedure_mutation_cycle:{cycle['cycle_id']}"
            )
        except Exception:
            self.runtime.store.rollback(before)
            raise
        return {"cycle": cycle, "commit": commit}

    @staticmethod
    def promotion_gate(
        *,
        champion: Mapping[str, Any],
        challenger: Mapping[str, Any],
    ) -> Dict[str, Any]:
        errors = []
        goal_gain = (
            challenger["mean_goal_success"]
            - champion["mean_goal_success"]
        )
        worst_goal_gain = (
            challenger["worst_family_goal_success"]
            - champion["worst_family_goal_success"]
        )
        factor_gain = (
            challenger["mean_factor_accuracy"]
            - champion["mean_factor_accuracy"]
        )
        if goal_gain < 0.03:
            errors.append("MEAN_GOAL_GAIN_BELOW_3_POINTS")
        if worst_goal_gain < 0.0:
            errors.append("WORST_FAMILY_GOAL_REGRESSION")
        if factor_gain < 0.0:
            errors.append("MEAN_FACTOR_ACCURACY_REGRESSION")
        if (
            challenger["calibration_error"]
            > champion["calibration_error"] + 0.02
        ):
            errors.append("CALIBRATION_REGRESSION")
        if challenger["policy"]["complexity"] > 8:
            errors.append("PROCEDURE_COMPLEXITY_GROWTH")
        if challenger["policy"]["maximum_experiments"] > 10:
            errors.append("EXPERIMENT_BUDGET_CAP_EXCEEDED")
        return {
            "accepted": not errors,
            "errors": errors,
            "mean_goal_gain": goal_gain,
            "worst_family_goal_gain": worst_goal_gain,
            "mean_factor_accuracy_gain": factor_gain,
            "calibration_change": (
                challenger["calibration_error"]
                - champion["calibration_error"]
            ),
        }

    def promote(
        self,
        *,
        champion_result: Mapping[str, Any],
        challenger_result: Mapping[str, Any],
        gate: Mapping[str, Any],
    ) -> Dict[str, Any]:
        goal = "causal_investigation_policy"
        baseline = ProcedureCandidate(
            procedure_id="procedure_phase7_policy_control",
            goal=goal,
            steps=[
                "probe_by_information_gain",
                "stop_at_0.95_or_6",
                "intervene_to_goal_pattern",
                "execute_and_verify",
            ],
            score=float(champion_result["score"]),
            success=True,
            evidence={
                "evaluation": "sealed_generated_worlds",
                "mean_goal_success": champion_result[
                    "mean_goal_success"
                ],
                "worst_family_goal_success": champion_result[
                    "worst_family_goal_success"
                ],
            },
        )
        baseline_promotion = self.runtime.skills.promote(baseline)
        challenger_policy = challenger_result["policy"]
        challenger = ProcedureCandidate(
            procedure_id=(
                "procedure_evolved_causal_"
                f"{_canonical_hash(challenger_policy)[:12]}"
            ),
            goal=goal,
            steps=[
                "probe_by_information_gain",
                (
                    f"stop_at_{challenger_policy['confidence_gate']}"
                    f"_or_{challenger_policy['maximum_experiments']}"
                ),
                (
                    "cost_weight_"
                    f"{challenger_policy['cost_weight']}"
                ),
                "intervene_to_goal_pattern",
                "execute_and_verify",
            ],
            score=float(challenger_result["score"]),
            success=bool(gate["accepted"]),
            evidence={
                "evaluation": "sealed_generated_worlds",
                "gate": dict(gate),
                "mean_goal_success": challenger_result[
                    "mean_goal_success"
                ],
                "worst_family_goal_success": challenger_result[
                    "worst_family_goal_success"
                ],
                "failure_counts": challenger_result[
                    "failure_counts"
                ],
            },
        )
        challenger_promotion = self.runtime.skills.promote(challenger)
        self.runtime.skills.record_outcome(
            procedure_id=challenger.procedure_id,
            success=challenger.success,
            score=challenger.score,
            evidence=challenger.evidence,
        )
        return {
            "baseline": baseline.to_dict(),
            "baseline_promotion": baseline_promotion,
            "challenger": challenger.to_dict(),
            "challenger_promotion": challenger_promotion,
        }
