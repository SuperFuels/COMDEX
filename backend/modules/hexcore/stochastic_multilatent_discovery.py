from __future__ import annotations

import itertools
import math
import random
import uuid
from dataclasses import dataclass, replace
from typing import Any, Callable, Dict, List, Mapping, Sequence, Tuple

from backend.modules.hexcore.persistent_learning import (
    HexCorePersistentLearningStore,
    _canonical_hash,
    _json_safe,
    _utc_timestamp,
)


StateTuple = Tuple[int, ...]
Runner = Callable[[str], Mapping[str, Any]]


def _entropy(distribution: Mapping[StateTuple, float]) -> float:
    return -sum(
        probability * math.log2(probability)
        for probability in distribution.values()
        if probability > 0
    )


def _normalize(
    distribution: Mapping[StateTuple, float],
) -> Dict[StateTuple, float]:
    total = sum(max(0.0, value) for value in distribution.values())
    if total <= 0:
        probability = 1.0 / max(1, len(distribution))
        return {state: probability for state in distribution}
    return {
        state: max(0.0, value) / total
        for state, value in distribution.items()
    }


@dataclass(frozen=True)
class StochasticLatentGraph:
    graph_id: str
    factor_count: int
    toggle_actions: Tuple[str, ...]
    signal_targets: Tuple[str, ...]
    signal_factor_assignments: Tuple[int, ...]
    probe_actions: Tuple[str, ...]
    goal_action: str
    goal_pattern: Tuple[int, ...] = ()
    probe_reliability: float = 0.9
    probe_reliabilities: Tuple[float, ...] = ()
    goal_reliability: float = 0.98
    revision: int = 1

    @property
    def complexity(self) -> int:
        return (
            self.factor_count
            + len(self.toggle_actions)
            + 2 * len(self.signal_targets)
            + 2
        )

    @property
    def latent_states(self) -> List[StateTuple]:
        return list(itertools.product((0, 1), repeat=self.factor_count))

    def reliability_for_probe(self, index: int) -> float:
        if self.probe_reliabilities:
            return float(self.probe_reliabilities[index])
        return float(self.probe_reliability)

    def transition_latent(
        self, latent: StateTuple, action: str
    ) -> StateTuple:
        return tuple(
            value ^ int(action == self.toggle_actions[index])
            for index, value in enumerate(latent)
        )

    def expected_visible(
        self,
        visible: Mapping[str, int],
        latent: StateTuple,
        action: str,
    ) -> Dict[str, int]:
        expected = {
            key: int(bool(value)) for key, value in visible.items()
        }
        for target, factor, probe in zip(
            self.signal_targets,
            self.signal_factor_assignments,
            self.probe_actions,
        ):
            if action == probe:
                expected[target] = int(latent[factor])
        if action == self.goal_action:
            target = (
                self.goal_pattern
                if self.goal_pattern
                else tuple(1 for _ in range(self.factor_count))
            )
            expected["opened"] = int(
                all(
                    required == -1 or latent[index] == required
                    for index, required in enumerate(target)
                )
            )
        return expected

    def observation_likelihood(
        self,
        *,
        visible: Mapping[str, int],
        latent: StateTuple,
        action: str,
        next_visible: Mapping[str, int],
    ) -> float:
        expected = self.expected_visible(visible, latent, action)
        likelihood = 1.0
        for field, observed in next_visible.items():
            reliability = 0.999
            if action in self.probe_actions and field in self.signal_targets:
                probe_index = self.probe_actions.index(action)
                reliability = (
                    self.reliability_for_probe(probe_index)
                    if self.signal_targets[probe_index] == field
                    else 0.999
                )
            elif action == self.goal_action and field == "opened":
                reliability = self.goal_reliability
            likelihood *= (
                reliability
                if int(observed) == int(expected[field])
                else 1.0 - reliability
            )
        return max(likelihood, 1e-12)

    def to_dict(self) -> Dict[str, Any]:
        edges = []
        for index, action in enumerate(self.toggle_actions):
            latent = f"latent_factor_{index + 1}"
            edges.extend(
                [
                    {
                        "source": latent,
                        "target": latent,
                        "edge_type": "latent_persistence",
                    },
                    {
                        "source": f"action:{action}",
                        "target": latent,
                        "edge_type": "latent_intervention",
                    },
                ]
            )
        for target, factor, action in zip(
            self.signal_targets,
            self.signal_factor_assignments,
            self.probe_actions,
        ):
            edges.extend(
                [
                    {
                        "source": f"latent_factor_{factor + 1}",
                        "target": target,
                        "edge_type": "noisy_readout",
                    },
                    {
                        "source": f"action:{action}",
                        "target": target,
                        "edge_type": "probe",
                    },
                ]
            )
        target = (
            self.goal_pattern
            if self.goal_pattern
            else tuple(1 for _ in range(self.factor_count))
        )
        for index, required in enumerate(target):
            if required != -1:
                edges.append(
                    {
                        "source": f"latent_factor_{index + 1}",
                        "target": "opened",
                        "edge_type": "joint_goal_condition",
                    }
                )
        edges.append(
            {
                "source": f"action:{self.goal_action}",
                "target": "opened",
                "edge_type": "goal_intervention",
            }
        )
        return _json_safe(
            {
                "schema_version": (
                    "aion.hexcore.stochastic_latent_graph.v1"
                ),
                "graph_id": self.graph_id,
                "factor_count": self.factor_count,
                "toggle_actions": self.toggle_actions,
                "signal_targets": self.signal_targets,
                "signal_factor_assignments": (
                    self.signal_factor_assignments
                ),
                "probe_actions": self.probe_actions,
                "goal_action": self.goal_action,
                "goal_pattern": (
                    self.goal_pattern
                    if self.goal_pattern
                    else tuple(1 for _ in range(self.factor_count))
                ),
                "probe_reliability": self.probe_reliability,
                "probe_reliabilities": self.probe_reliabilities,
                "goal_reliability": self.goal_reliability,
                "complexity": self.complexity,
                "revision": self.revision,
                "edges": edges,
            }
        )


def _episode_rows(
    rows: Sequence[Mapping[str, Any]],
) -> List[List[Mapping[str, Any]]]:
    grouped: Dict[str, List[Mapping[str, Any]]] = {}
    for row in rows:
        grouped.setdefault(str(row["episode_id"]), []).append(row)
    return [
        sorted(episode, key=lambda row: int(row["step"]))
        for _, episode in sorted(grouped.items())
    ]


class GovernedStochasticMultiLatentLearner:
    """Discovers compact stochastic latent graphs and plans with belief state."""

    def __init__(self, store: HexCorePersistentLearningStore) -> None:
        self.store = store

    @staticmethod
    def diagnostic_sequences(
        *,
        actions: Sequence[str],
        episodes: int,
        steps: int,
    ) -> List[List[str]]:
        pairs = list(itertools.permutations(sorted(actions), 2))
        counts = {pair: 0 for pair in pairs}
        output = []
        for episode in range(episodes):
            sequence = []
            while len(sequence) < steps:
                selected = min(
                    pairs,
                    key=lambda pair: (
                        counts[pair],
                        _canonical_hash([episode, len(sequence), pair]),
                    ),
                )
                counts[selected] += 1
                sequence.extend(selected)
            output.append(sequence[:steps])
        return output

    @staticmethod
    def collect(
        *,
        runner_factory: Callable[[int], Runner],
        sequences: Sequence[Sequence[str]],
        phase: str,
    ) -> List[Dict[str, Any]]:
        rows = []
        for episode_index, sequence in enumerate(sequences):
            runner = runner_factory(episode_index)
            for step, action in enumerate(sequence):
                observation = dict(runner(action) or {})
                rows.append(
                    {
                        "episode_id": f"{phase}_{episode_index:04d}",
                        "step": step,
                        "state": {
                            key: int(value)
                            for key, value in observation["state"].items()
                        },
                        "action": action,
                        "next_state": {
                            key: int(value)
                            for key, value in observation[
                                "next_state"
                            ].items()
                        },
                        "evidence": _json_safe(
                            observation.get("evidence") or {}
                        ),
                    }
                )
        return rows

    @staticmethod
    def split_episodes(
        rows: Sequence[Mapping[str, Any]],
        modulus: int = 5,
    ) -> Tuple[List[Mapping[str, Any]], List[Mapping[str, Any]]]:
        development, held_out = [], []
        for row in rows:
            episode = int(str(row["episode_id"]).rsplit("_", 1)[-1])
            (held_out if episode % modulus == 0 else development).append(
                row
            )
        return development, held_out

    @staticmethod
    def _episode_log_likelihood(
        graph: StochasticLatentGraph,
        episode: Sequence[Mapping[str, Any]],
    ) -> float:
        likelihoods = []
        for initial in graph.latent_states:
            latent = initial
            likelihood = 1.0 / len(graph.latent_states)
            for row in episode:
                likelihood *= graph.observation_likelihood(
                    visible=row["state"],
                    latent=latent,
                    action=str(row["action"]),
                    next_visible=row["next_state"],
                )
                latent = graph.transition_latent(
                    latent, str(row["action"])
                )
            likelihoods.append(likelihood)
        return math.log(max(sum(likelihoods), 1e-300))

    def graph_score(
        self,
        graph: StochasticLatentGraph,
        rows: Sequence[Mapping[str, Any]],
        complexity_penalty: float = 0.01,
    ) -> Dict[str, float]:
        episodes = _episode_rows(rows)
        average_log_likelihood = sum(
            self._episode_log_likelihood(graph, episode)
            for episode in episodes
        ) / max(1, len(episodes))
        fields = sum(len(row["next_state"]) for row in rows)
        normalized = average_log_likelihood / max(
            1.0, fields / max(1, len(episodes))
        )
        return {
            "average_log_likelihood": average_log_likelihood,
            "normalized_log_likelihood": normalized,
            "objective": (
                normalized - complexity_penalty * graph.complexity
            ),
        }

    def construct_graph(
        self,
        *,
        world_id: str,
        actions: Sequence[str],
        signal_targets: Sequence[str],
        development_rows: Sequence[Mapping[str, Any]],
        minimum_factors: int = 1,
        maximum_factors: int = 2,
        toggle_action_candidates: Sequence[str] | None = None,
        probe_action_candidates: Sequence[str] | None = None,
        goal_action_candidates: Sequence[str] | None = None,
    ) -> Tuple[StochasticLatentGraph, List[Dict[str, Any]]]:
        candidates = []
        action_set = tuple(sorted(actions))
        for factor_count in range(minimum_factors, maximum_factors + 1):
            assignments = (
                [(0,) * len(signal_targets)]
                if factor_count == 1
                else list(
                    itertools.product(
                        range(factor_count),
                        repeat=len(signal_targets),
                    )
                )
            )
            assignments = [
                row for row in assignments
                if set(row) == set(range(factor_count))
            ]
            if (
                toggle_action_candidates is not None
                and probe_action_candidates is not None
                and goal_action_candidates is not None
            ):
                role_rows = (
                    tuple(toggles) + tuple(probes) + (goal,)
                    for toggles in itertools.permutations(
                        tuple(toggle_action_candidates), factor_count
                    )
                    for probes in itertools.permutations(
                        tuple(probe_action_candidates),
                        len(signal_targets),
                    )
                    for goal in tuple(goal_action_candidates)
                    if len(set(toggles + probes + (goal,)))
                    == factor_count + len(signal_targets) + 1
                )
            else:
                role_rows = itertools.permutations(
                    action_set,
                    factor_count + len(signal_targets) + 1,
                )
            for roles in role_rows:
                toggles = roles[:factor_count]
                probes = roles[
                    factor_count : factor_count + len(signal_targets)
                ]
                goal = roles[-1]
                for assignment in assignments:
                    for goal_pattern in itertools.product(
                        (0, 1), repeat=factor_count
                    ):
                        signature = [
                            world_id,
                            factor_count,
                            toggles,
                            signal_targets,
                            assignment,
                            probes,
                            goal,
                            goal_pattern,
                        ]
                        graph = StochasticLatentGraph(
                            graph_id=(
                                f"stochastic_graph_"
                                f"{_canonical_hash(signature)[:16]}"
                            ),
                            factor_count=factor_count,
                            toggle_actions=tuple(toggles),
                            signal_targets=tuple(signal_targets),
                            signal_factor_assignments=tuple(assignment),
                            probe_actions=tuple(probes),
                            goal_action=goal,
                            goal_pattern=tuple(goal_pattern),
                        )
                        score = self.graph_score(
                            graph, development_rows
                        )
                        candidates.append(
                            {"graph": graph, **score}
                        )
        candidates.sort(
            key=lambda row: (
                row["objective"],
                row["normalized_log_likelihood"],
                -row["graph"].complexity,
                row["graph"].graph_id,
            ),
            reverse=True,
        )
        return candidates[0]["graph"], [
            {
                "graph": row["graph"].to_dict(),
                "average_log_likelihood": round(
                    row["average_log_likelihood"], 8
                ),
                "normalized_log_likelihood": round(
                    row["normalized_log_likelihood"], 8
                ),
                "objective": round(row["objective"], 8),
            }
            for row in candidates[:12]
        ]

    @staticmethod
    def uniform_belief(
        graph: StochasticLatentGraph,
    ) -> Dict[StateTuple, float]:
        probability = 1.0 / len(graph.latent_states)
        return {state: probability for state in graph.latent_states}

    def update_belief(
        self,
        *,
        graph: StochasticLatentGraph,
        belief: Mapping[StateTuple, float],
        visible: Mapping[str, int],
        action: str,
        next_visible: Mapping[str, int],
    ) -> Dict[StateTuple, float]:
        posterior: Dict[StateTuple, float] = {}
        for latent, prior in belief.items():
            likelihood = graph.observation_likelihood(
                visible=visible,
                latent=latent,
                action=action,
                next_visible=next_visible,
            )
            next_latent = graph.transition_latent(latent, action)
            posterior[next_latent] = (
                posterior.get(next_latent, 0.0)
                + float(prior) * likelihood
            )
        return _normalize(posterior)

    def expected_information_gain(
        self,
        *,
        graph: StochasticLatentGraph,
        belief: Mapping[StateTuple, float],
        visible: Mapping[str, int],
        action: str,
    ) -> float:
        prior_after_transition: Dict[StateTuple, float] = {}
        for latent, probability in belief.items():
            next_latent = graph.transition_latent(latent, action)
            prior_after_transition[next_latent] = (
                prior_after_transition.get(next_latent, 0.0)
                + probability
            )
        expected_entropy = 0.0
        fields = sorted(visible)
        for values in itertools.product((0, 1), repeat=len(fields)):
            next_visible = dict(zip(fields, values))
            probability = sum(
                prior
                * graph.observation_likelihood(
                    visible=visible,
                    latent=latent,
                    action=action,
                    next_visible=next_visible,
                )
                for latent, prior in belief.items()
            )
            if probability <= 0:
                continue
            posterior = self.update_belief(
                graph=graph,
                belief=belief,
                visible=visible,
                action=action,
                next_visible=next_visible,
            )
            expected_entropy += probability * _entropy(posterior)
        return max(
            0.0, _entropy(prior_after_transition) - expected_entropy
        )

    def select_experiment(
        self,
        *,
        graph: StochasticLatentGraph,
        belief: Mapping[StateTuple, float],
        visible: Mapping[str, int],
        action_costs: Mapping[str, float],
        cost_weight: float = 0.1,
        candidate_actions: Sequence[str] | None = None,
        value_of_information_ratio: bool = False,
    ) -> Dict[str, Any]:
        rows = []
        for action in candidate_actions or graph.probe_actions:
            gain = self.expected_information_gain(
                graph=graph,
                belief=belief,
                visible=visible,
                action=action,
            )
            cost = float(action_costs.get(action, 0.0))
            rows.append(
                {
                    "action": action,
                    "expected_information_gain": round(gain, 8),
                    "cost": cost,
                    "utility": round(
                        (
                            gain / max(0.05, cost)
                            if value_of_information_ratio
                            else gain - cost_weight * cost
                        ),
                        8,
                    ),
                }
            )
        rows.sort(
            key=lambda row: (
                row["utility"],
                row["expected_information_gain"],
                -row["cost"],
                row["action"],
            ),
            reverse=True,
        )
        return {"selected": rows[0], "candidates": rows}

    @staticmethod
    def marginal_confidence(
        belief: Mapping[StateTuple, float],
        factor: int,
    ) -> Tuple[int, float]:
        one = sum(
            probability
            for state, probability in belief.items()
            if state[factor] == 1
        )
        if one >= 0.5:
            return 1, one
        return 0, 1.0 - one

    def investigate_and_plan(
        self,
        *,
        graph: StochasticLatentGraph,
        runner: Runner,
        initial_visible: Mapping[str, int],
        action_costs: Mapping[str, float],
        confidence_gate: float = 0.95,
        maximum_experiments: int = 6,
        cost_weight: float = 0.1,
        goal_relevance_only: bool = False,
        uncertain_factor_only: bool = False,
        goal_retries: int = 0,
        adaptive_confidence: bool = False,
        reliability_slope: float = 0.0,
        adaptive_experiment_budget: bool = False,
        low_reliability_budget: int = 10,
        high_reliability_budget: int = 5,
        online_reliability_learning: bool = False,
        reliability_prior: float = 0.80,
        value_of_information_ratio: bool = False,
        three_factor_reserve: bool = False,
        minimum_voi_per_cost: float = 0.0,
        policy_bank_enabled: bool = False,
        router_low_reliability_threshold: float = 0.75,
        router_high_reliability_threshold: float = 0.85,
        toggle_action_cost: float = 0.25,
        goal_action_cost: float = 0.50,
    ) -> Dict[str, Any]:
        visible = dict(initial_visible)
        belief = self.uniform_belief(graph)
        trace = []
        goal_pattern = (
            graph.goal_pattern
            if graph.goal_pattern
            else tuple(1 for _ in range(graph.factor_count))
        )
        relevant_factors = [
            factor for factor, required in enumerate(goal_pattern)
            if required != -1
        ]
        confidence_factors = (
            relevant_factors
            if goal_relevance_only and relevant_factors
            else list(range(graph.factor_count))
        )
        factor_confidence_gates = [
            min(
                0.995,
                max(
                    0.50,
                    confidence_gate
                    + (
                        reliability_slope
                        * (0.90 - graph.probe_reliability)
                        if adaptive_confidence
                        else 0.0
                    ),
                ),
            )
            for _ in range(graph.factor_count)
        ]
        reliability_estimates = [
            reliability_prior
            if online_reliability_learning
            else graph.reliability_for_probe(index)
            for index in range(len(graph.probe_actions))
        ]
        probe_observations: Dict[str, List[int]] = {
            action: [] for action in graph.probe_actions
        }
        reliability_grid = (0.55, 0.65, 0.75, 0.85, 0.95)
        reliability_posteriors = [
            _normalize(
                {
                    (index,): math.exp(
                        -abs(value - reliability_prior) / 0.12
                    )
                    for index, value in enumerate(reliability_grid)
                }
            )
            for _ in graph.probe_actions
        ]
        effective_maximum_experiments = maximum_experiments
        if adaptive_experiment_budget:
            if graph.probe_reliability <= 0.80:
                effective_maximum_experiments = low_reliability_budget
            elif graph.probe_reliability >= 0.90:
                effective_maximum_experiments = high_reliability_budget
        if three_factor_reserve and graph.factor_count == 3:
            effective_maximum_experiments = max(
                effective_maximum_experiments,
                maximum_experiments + 1,
            )
        if policy_bank_enabled:
            effective_maximum_experiments = max(
                effective_maximum_experiments, 10
            )
        active_specialist = "single_policy"
        route_history = []
        for _ in range(effective_maximum_experiments):
            marginals = [
                self.marginal_confidence(belief, factor)
                for factor in range(graph.factor_count)
            ]
            current_confidence_gates = list(factor_confidence_gates)
            current_budget = effective_maximum_experiments
            current_minimum_voi = minimum_voi_per_cost
            if policy_bank_enabled:
                relevant_probe_indexes = [
                    index
                    for index, factor in enumerate(
                        graph.signal_factor_assignments
                    )
                    if factor in confidence_factors
                ]
                observed_relevant = sum(
                    len(probe_observations[graph.probe_actions[index]])
                    for index in relevant_probe_indexes
                )
                minimum_estimated_reliability = min(
                    reliability_estimates[index]
                    for index in relevant_probe_indexes
                )
                maximum_relevant_entropy = max(
                    1.0 - marginals[factor][1]
                    for factor in confidence_factors
                )
                if observed_relevant < len(relevant_probe_indexes):
                    active_specialist = "phase9_fallback"
                    current_budget = 7
                    current_minimum_voi = 0.0
                    current_confidence_gates = [
                        0.97 for _ in current_confidence_gates
                    ]
                elif (
                    graph.factor_count >= 3
                    or minimum_estimated_reliability
                    <= router_low_reliability_threshold
                    or maximum_relevant_entropy >= 0.20
                ):
                    active_specialist = "conservative_evidence"
                    current_budget = 10
                    current_minimum_voi = 0.15
                    current_confidence_gates = [
                        0.97 for _ in current_confidence_gates
                    ]
                elif (
                    minimum_estimated_reliability
                    >= router_high_reliability_threshold
                    and maximum_relevant_entropy <= 0.12
                ):
                    active_specialist = "efficient_evidence"
                    current_budget = 8
                    current_minimum_voi = 0.30
                    current_confidence_gates = [
                        0.93 for _ in current_confidence_gates
                    ]
                else:
                    active_specialist = "phase9_fallback"
                    current_budget = 7
                    current_minimum_voi = 0.0
                    current_confidence_gates = [
                        0.97 for _ in current_confidence_gates
                    ]
                route_history.append(
                    {
                        "step": len(trace),
                        "specialist": active_specialist,
                        "minimum_estimated_reliability": round(
                            minimum_estimated_reliability, 8
                        ),
                        "maximum_relevant_entropy": round(
                            maximum_relevant_entropy, 8
                        ),
                        "budget": current_budget,
                        "minimum_voi_per_cost": current_minimum_voi,
                    }
                )
                if len(trace) >= current_budget:
                    break
            if all(
                marginals[factor][1]
                >= current_confidence_gates[factor]
                for factor in confidence_factors
            ):
                break
            candidate_actions = []
            for signal_index, action in enumerate(graph.probe_actions):
                factor = graph.signal_factor_assignments[signal_index]
                if goal_relevance_only and factor not in confidence_factors:
                    continue
                if (
                    uncertain_factor_only
                    and marginals[factor][1]
                    >= current_confidence_gates[factor]
                ):
                    continue
                candidate_actions.append(action)
            if not candidate_actions:
                break
            working_graph = (
                replace(
                    graph,
                    probe_reliability=sum(reliability_estimates)
                    / len(reliability_estimates),
                    probe_reliabilities=tuple(reliability_estimates),
                )
                if (
                    online_reliability_learning
                    and active_specialist != "phase9_fallback"
                )
                else graph
            )
            selection = self.select_experiment(
                graph=working_graph,
                belief=belief,
                visible=visible,
                action_costs=action_costs,
                cost_weight=cost_weight,
                candidate_actions=candidate_actions,
                value_of_information_ratio=value_of_information_ratio,
            )
            if (
                value_of_information_ratio
                and selection["selected"]["utility"]
                < current_minimum_voi
            ):
                break
            action = selection["selected"]["action"]
            observation = dict(runner(action) or {})
            next_visible = dict(observation["next_state"])
            prior = dict(belief)
            if online_reliability_learning:
                probe_index = graph.probe_actions.index(action)
                signal = graph.signal_targets[probe_index]
                observations = probe_observations[action]
                observed_value = int(next_visible[signal])
                observations.append(observed_value)
                factor = graph.signal_factor_assignments[probe_index]
                prior_match = sum(
                    probability
                    for state, probability in prior.items()
                    if state[factor] == observed_value
                )
                posterior = reliability_posteriors[probe_index]
                posterior = _normalize(
                    {
                        key: weight
                        * (
                            prior_match * reliability_grid[key[0]]
                            + (1.0 - prior_match)
                            * (1.0 - reliability_grid[key[0]])
                        )
                        for key, weight in posterior.items()
                    }
                )
                reliability_posteriors[probe_index] = posterior
                reliability_estimates[probe_index] = sum(
                    reliability_grid[key[0]] * weight
                    for key, weight in posterior.items()
                )
                if active_specialist != "phase9_fallback":
                    working_graph = replace(
                        graph,
                        probe_reliability=sum(reliability_estimates)
                        / len(reliability_estimates),
                        probe_reliabilities=tuple(
                            reliability_estimates
                        ),
                    )
            belief = self.update_belief(
                graph=working_graph,
                belief=belief,
                visible=visible,
                action=action,
                next_visible=next_visible,
            )
            trace.append(
                {
                    "action": action,
                    "expected_information_gain": selection[
                        "selected"
                    ]["expected_information_gain"],
                    "action_cost": selection["selected"]["cost"],
                    "selection_utility": selection["selected"]["utility"],
                    "visible_before": dict(visible),
                    "visible_after": dict(next_visible),
                    "prior": {
                        str(state): probability
                        for state, probability in prior.items()
                    },
                    "posterior": {
                        str(state): probability
                        for state, probability in belief.items()
                    },
                }
            )
            visible = next_visible

        plan = []
        for factor in range(graph.factor_count):
            value, _ = self.marginal_confidence(belief, factor)
            if (
                goal_pattern[factor] != -1
                and value != goal_pattern[factor]
            ):
                action = graph.toggle_actions[factor]
                plan.append(action)
                observation = dict(runner(action) or {})
                next_visible = dict(observation["next_state"])
                belief = self.update_belief(
                    graph=graph,
                    belief=belief,
                    visible=visible,
                    action=action,
                    next_visible=next_visible,
                )
                visible = next_visible
        plan.append(graph.goal_action)
        final_observation = dict(runner(graph.goal_action) or {})
        visible = dict(final_observation["next_state"])
        goal_attempts = 1
        while not bool(visible.get("opened")) and goal_attempts <= goal_retries:
            final_observation = dict(runner(graph.goal_action) or {})
            visible = dict(final_observation["next_state"])
            goal_attempts += 1
        marginals = [
            self.marginal_confidence(belief, factor)
            for factor in range(graph.factor_count)
        ]
        relevant_confidences = [
            marginals[factor][1] for factor in confidence_factors
        ]
        probe_cost = sum(
            float(row.get("action_cost", 0.0)) for row in trace
        )
        toggle_count = len(plan) - 1
        total_action_count = (
            len(trace) + toggle_count + goal_attempts
        )
        total_action_cost = (
            probe_cost
            + toggle_action_cost * toggle_count
            + goal_action_cost * goal_attempts
        )
        return {
            "experiment_count": len(trace),
            "effective_maximum_experiments": (
                effective_maximum_experiments
            ),
            "trace": trace,
            "belief": {
                str(state): round(probability, 8)
                for state, probability in belief.items()
            },
            "marginals": [
                {"value": value, "confidence": round(confidence, 8)}
                for value, confidence in marginals
            ],
            "minimum_marginal_confidence": round(
                min(confidence for _, confidence in marginals), 8
            ),
            "minimum_relevant_confidence": round(
                min(relevant_confidences), 8
            ),
            "factor_confidence_gates": [
                round(value, 8) for value in factor_confidence_gates
            ],
            "estimated_probe_reliabilities": {
                action: round(reliability_estimates[index], 8)
                for index, action in enumerate(graph.probe_actions)
            },
            "probe_reliability_posteriors": {
                action: {
                    str(reliability_grid[key[0]]): round(weight, 8)
                    for key, weight in reliability_posteriors[index].items()
                }
                for index, action in enumerate(graph.probe_actions)
            },
            "probe_observation_counts": {
                action: len(rows)
                for action, rows in probe_observations.items()
            },
            "selected_specialist": active_specialist,
            "route_history": route_history,
            "plan": plan,
            "goal_success": bool(visible.get("opened")),
            "goal_attempts": goal_attempts,
            "toggle_count": toggle_count,
            "total_action_count": total_action_count,
            "total_action_cost": round(total_action_cost, 8),
            "final_visible": visible,
        }

    def discover(
        self,
        *,
        world_id: str,
        actions: Sequence[str],
        signal_targets: Sequence[str],
        rows: Sequence[Mapping[str, Any]],
        minimum_factors: int = 1,
        maximum_factors: int = 2,
        maximum_complexity: int = 12,
        minimum_factor_gain: float = 0.05,
        persist: bool = True,
        toggle_action_candidates: Sequence[str] | None = None,
        probe_action_candidates: Sequence[str] | None = None,
        goal_action_candidates: Sequence[str] | None = None,
    ) -> Dict[str, Any]:
        development, held_out = self.split_episodes(rows)
        graph, contenders = self.construct_graph(
            world_id=world_id,
            actions=actions,
            signal_targets=signal_targets,
            development_rows=development,
            minimum_factors=minimum_factors,
            maximum_factors=maximum_factors,
            toggle_action_candidates=toggle_action_candidates,
            probe_action_candidates=probe_action_candidates,
            goal_action_candidates=goal_action_candidates,
        )
        held_out_score = self.graph_score(graph, held_out)
        one_factor, _ = self.construct_graph(
            world_id=f"{world_id}:one_factor_control",
            actions=actions,
            signal_targets=signal_targets,
            development_rows=development,
            minimum_factors=1,
            maximum_factors=1,
            toggle_action_candidates=toggle_action_candidates,
            probe_action_candidates=probe_action_candidates,
            goal_action_candidates=goal_action_candidates,
        )
        one_factor_score = self.graph_score(one_factor, held_out)
        improvement = (
            held_out_score["normalized_log_likelihood"]
            - one_factor_score["normalized_log_likelihood"]
        )
        errors = []
        if (
            graph.factor_count > 1
            and improvement < minimum_factor_gain
        ):
            errors.append("INSUFFICIENT_HELD_OUT_LIKELIHOOD_GAIN")
        if graph.complexity > maximum_complexity:
            errors.append("COMPLEXITY_CAP_EXCEEDED")
        accepted = not errors
        session = {
            "schema_version": (
                "aion.hexcore.stochastic_multilatent_session.v1"
            ),
            "session_id": f"multilatent_{uuid.uuid4().hex[:16]}",
            "world_id": world_id,
            "graph": graph.to_dict(),
            "held_out_score": held_out_score,
            "one_factor_control": {
                "graph": one_factor.to_dict(),
                "held_out_score": one_factor_score,
            },
            "held_out_normalized_log_likelihood_gain": improvement,
            "contenders": contenders,
            "accepted": accepted,
            "errors": errors,
            "timestamp": _utc_timestamp(),
        }
        if persist:
            before = self.store.prepare_mutation()
            try:
                self.store.state["hypothesis_expansions"].append(
                    {
                        "schema_version": (
                            "aion.hexcore.stochastic_multilatent_expansion.v1"
                        ),
                        "session_id": session["session_id"],
                        "world_id": world_id,
                        "factor_count": graph.factor_count,
                        "accepted": accepted,
                        "held_out_gain": improvement,
                        "complexity": graph.complexity,
                        "errors": errors,
                        "timestamp": _utc_timestamp(),
                    }
                )
                if accepted:
                    self.store.state["causal_graphs"][world_id] = {
                        **graph.to_dict(),
                        "status": "active",
                        "source_session_id": session["session_id"],
                    }
                    for index in range(graph.factor_count):
                        name = f"{world_id}:latent_factor_{index + 1}"
                        self.store.state["latent_variables"][name] = {
                            "schema_version": (
                                "aion.hexcore.latent_variable.v1"
                            ),
                            "latent_name": name,
                            "world_id": world_id,
                            "cardinality": 2,
                            "status": "active",
                            "source_graph_id": graph.graph_id,
                            "created_at": _utc_timestamp(),
                        }
                self.store.state["discovery_sessions"].append(session)
                self.store.commit(
                    reason=f"stochastic_multilatent:{session['session_id']}"
                )
            except Exception:
                self.store.rollback(before)
                raise
        return session

    @staticmethod
    def graph_from_record(
        record: Mapping[str, Any],
    ) -> StochasticLatentGraph:
        return StochasticLatentGraph(
            graph_id=str(record["graph_id"]),
            factor_count=int(record["factor_count"]),
            toggle_actions=tuple(record["toggle_actions"]),
            signal_targets=tuple(record["signal_targets"]),
            signal_factor_assignments=tuple(
                int(value)
                for value in record["signal_factor_assignments"]
            ),
            probe_actions=tuple(record["probe_actions"]),
            goal_action=str(record["goal_action"]),
            goal_pattern=tuple(
                int(value)
                for value in record.get("goal_pattern")
                or [1] * int(record["factor_count"])
            ),
            probe_reliability=float(record["probe_reliability"]),
            probe_reliabilities=tuple(
                float(value)
                for value in record.get("probe_reliabilities") or ()
            ),
            goal_reliability=float(record["goal_reliability"]),
            revision=int(record.get("revision") or 1),
        )


class StochasticTwoFactorVault:
    """Two hidden bits, noisy probes, and a jointly conditioned goal."""

    def __init__(
        self,
        *,
        seed: int,
        initial_factors: Tuple[int, int] | None = None,
        probe_reliability: float = 0.9,
        goal_reliability: float = 0.98,
    ) -> None:
        self.random = random.Random(seed)
        self.factors = (
            tuple(initial_factors)
            if initial_factors is not None
            else (
                self.random.randint(0, 1),
                self.random.randint(0, 1),
            )
        )
        self.probe_reliability = probe_reliability
        self.goal_reliability = goal_reliability
        self.visible = {"left_signal": 0, "right_signal": 0, "opened": 0}

    def step(self, action: str) -> Dict[str, Any]:
        before = dict(self.visible)
        factors = list(self.factors)
        if action == "flip_left":
            factors[0] ^= 1
        elif action == "flip_right":
            factors[1] ^= 1
        elif action == "inspect_left":
            correct = self.random.random() < self.probe_reliability
            self.visible["left_signal"] = (
                factors[0] if correct else 1 - factors[0]
            )
        elif action == "inspect_right":
            correct = self.random.random() < self.probe_reliability
            self.visible["right_signal"] = (
                factors[1] if correct else 1 - factors[1]
            )
        elif action == "open":
            should_open = bool(factors[0] and factors[1])
            follows = self.random.random() < self.goal_reliability
            self.visible["opened"] = int(
                should_open if follows else not should_open
            )
        self.factors = tuple(factors)
        return {
            "state": before,
            "next_state": dict(self.visible),
            "evidence": {
                "state_before": before,
                "action": action,
                "state_after": dict(self.visible),
                "hidden_factors_visible": False,
            },
        }

    def audit_hidden_factors(self) -> Tuple[int, int]:
        return tuple(self.factors)
