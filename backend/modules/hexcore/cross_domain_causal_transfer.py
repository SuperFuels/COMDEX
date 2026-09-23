from __future__ import annotations

import itertools
import random
from dataclasses import dataclass
from typing import Any, Dict, List, Mapping, Sequence, Tuple

from backend.modules.hexcore.persistent_learning import (
    HexCorePersistentLearningRuntime,
    ProcedureCandidate,
    _canonical_hash,
)
from backend.modules.hexcore.stochastic_multilatent_discovery import (
    GovernedStochasticMultiLatentLearner,
    StochasticLatentGraph,
)


@dataclass(frozen=True)
class CausalDomainSpec:
    domain_id: str
    signal_targets: Tuple[str, ...]
    toggle_actions: Tuple[str, ...]
    probe_actions: Tuple[str, ...]
    goal_action: str
    goal_pattern_by_signal: Tuple[int, ...]
    probe_reliability: float = 0.9
    probe_reliabilities: Tuple[float, ...] = ()
    goal_reliability: float = 0.98

    @property
    def factor_count(self) -> int:
        return len(self.signal_targets)

    @property
    def actions(self) -> Tuple[str, ...]:
        return (
            self.toggle_actions
            + self.probe_actions
            + (self.goal_action,)
        )

    def reliability_for_probe(self, index: int) -> float:
        if self.probe_reliabilities:
            return float(self.probe_reliabilities[index])
        return float(self.probe_reliability)


class NamedStochasticLatentDomain:
    """Same generic causal operators behind entirely new domain symbols."""

    def __init__(
        self,
        *,
        spec: CausalDomainSpec,
        seed: int,
        initial_factors: Tuple[int, ...] | None = None,
    ) -> None:
        self.spec = spec
        self.random = random.Random(seed)
        self.factors = (
            tuple(initial_factors)
            if initial_factors is not None
            else tuple(
                self.random.randint(0, 1)
                for _ in range(spec.factor_count)
            )
        )
        self.visible = {
            **{target: 0 for target in spec.signal_targets},
            "opened": 0,
        }

    def step(self, action: str) -> Dict[str, Any]:
        before = dict(self.visible)
        factors = list(self.factors)
        if action in self.spec.toggle_actions:
            index = self.spec.toggle_actions.index(action)
            factors[index] ^= 1
        elif action in self.spec.probe_actions:
            index = self.spec.probe_actions.index(action)
            correct = self.random.random() < (
                self.spec.reliability_for_probe(index)
            )
            value = factors[index] if correct else 1 - factors[index]
            self.visible[self.spec.signal_targets[index]] = value
        elif action == self.spec.goal_action:
            should_open = all(
                required == -1 or factors[index] == required
                for index, required in enumerate(
                    self.spec.goal_pattern_by_signal
                )
            )
            follows = (
                self.random.random() < self.spec.goal_reliability
            )
            self.visible["opened"] = int(
                should_open if follows else not should_open
            )
        self.factors = tuple(factors)
        return {
            "state": before,
            "next_state": dict(self.visible),
            "evidence": {
                "domain_id": self.spec.domain_id,
                "action": action,
                "visible_before": before,
                "visible_after": dict(self.visible),
                "hidden_factors_visible": False,
            },
        }

    def audit_hidden_factors(self) -> Tuple[int, ...]:
        return tuple(self.factors)


class CrossDomainCausalTransferRuntime:
    """Transfers operator procedures while relearning all domain symbols."""

    ABSTRACT_STEPS = [
        "enumerate_action_history_motifs",
        "construct_minimum_latent_graph",
        "probe_by_expected_information_gain",
        "intervene_toward_learned_goal_pattern",
        "execute_and_verify_goal",
    ]

    def __init__(
        self,
        runtime: HexCorePersistentLearningRuntime,
    ) -> None:
        self.runtime = runtime
        self.learner = GovernedStochasticMultiLatentLearner(
            runtime.store
        )

    @staticmethod
    def transferred_sequences(
        *,
        actions: Sequence[str],
        episodes: int,
        steps: int,
    ) -> List[List[str]]:
        """Apply the learned intervention→readout→goal motif without names."""

        motifs = list(itertools.permutations(sorted(actions), 3))
        counts = {motif: 0 for motif in motifs}
        output = []
        for episode in range(episodes):
            sequence: List[str] = []
            while len(sequence) < steps:
                motif = min(
                    motifs,
                    key=lambda row: (
                        counts[row],
                        _canonical_hash(
                            ["transfer", episode, len(sequence), row]
                        ),
                    ),
                )
                counts[motif] += 1
                # Observe candidate B, intervene with A, observe B again,
                # then test candidate C as a possible goal action.
                sequence.extend(
                    [motif[1], motif[0], motif[1], motif[2]]
                )
            output.append(sequence[:steps])
        return output

    @staticmethod
    def graph_matches_spec(
        graph: StochasticLatentGraph,
        spec: CausalDomainSpec,
    ) -> bool:
        if graph.factor_count != spec.factor_count:
            return False
        if graph.goal_action != spec.goal_action:
            return False
        for signal_index, signal in enumerate(spec.signal_targets):
            if signal not in graph.signal_targets:
                return False
            graph_signal_index = graph.signal_targets.index(signal)
            factor = graph.signal_factor_assignments[graph_signal_index]
            if graph.probe_actions[graph_signal_index] != (
                spec.probe_actions[signal_index]
            ):
                return False
            if graph.toggle_actions[factor] != (
                spec.toggle_actions[signal_index]
            ):
                return False
            if graph.goal_pattern[factor] != (
                spec.goal_pattern_by_signal[signal_index]
            ):
                return False
        return True

    def learn_domain(
        self,
        *,
        spec: CausalDomainSpec,
        transfer_episodes: int = 16,
        transfer_steps: int = 12,
        cold_episodes: int = 48,
        cold_steps: int = 15,
    ) -> Dict[str, Any]:
        def factory(offset: int):
            def create(episode: int):
                return NamedStochasticLatentDomain(
                    spec=spec,
                    seed=offset + episode,
                ).step

            return create

        held_out_sequences = self.learner.diagnostic_sequences(
            actions=spec.actions,
            episodes=20,
            steps=15,
        )
        held_out_rows = self.learner.collect(
            runner_factory=factory(90_000),
            sequences=held_out_sequences,
            phase=f"{spec.domain_id}_held_out",
        )

        cold_sequences = self.learner.diagnostic_sequences(
            actions=spec.actions,
            episodes=cold_episodes,
            steps=cold_steps,
        )
        cold_rows = self.learner.collect(
            runner_factory=factory(30_000),
            sequences=cold_sequences,
            phase=f"{spec.domain_id}_cold",
        )
        cold_graph, _ = self.learner.construct_graph(
            world_id=f"{spec.domain_id}:cold",
            actions=spec.actions,
            signal_targets=spec.signal_targets,
            development_rows=cold_rows,
            maximum_factors=spec.factor_count,
        )
        cold_score = self.learner.graph_score(
            cold_graph, held_out_rows
        )

        transfer_sequences = self.transferred_sequences(
            actions=spec.actions,
            episodes=transfer_episodes,
            steps=transfer_steps,
        )
        transfer_rows = self.learner.collect(
            runner_factory=factory(60_000),
            sequences=transfer_sequences,
            phase=f"{spec.domain_id}_transfer",
        )
        transfer_session = self.learner.discover(
            world_id=spec.domain_id,
            actions=spec.actions,
            signal_targets=spec.signal_targets,
            rows=transfer_rows,
            maximum_factors=spec.factor_count,
            maximum_complexity=12,
            minimum_factor_gain=0.01,
            persist=True,
        )
        transfer_graph = self.learner.graph_from_record(
            self.runtime.store.state["causal_graphs"][
                spec.domain_id
            ]
        )
        transfer_score = self.learner.graph_score(
            transfer_graph, held_out_rows
        )
        return {
            "domain_id": spec.domain_id,
            "factor_count": spec.factor_count,
            "new_symbols": {
                "signals": spec.signal_targets,
                "actions": spec.actions,
            },
            "goal_pattern_by_signal": spec.goal_pattern_by_signal,
            "cold": {
                "training_experiments": len(cold_rows),
                "graph": cold_graph.to_dict(),
                "structure_correct": self.graph_matches_spec(
                    cold_graph, spec
                ),
                "held_out_score": cold_score,
            },
            "transfer": {
                "training_experiments": len(transfer_rows),
                "graph": transfer_graph.to_dict(),
                "structure_correct": self.graph_matches_spec(
                    transfer_graph, spec
                ),
                "held_out_score": transfer_score,
                "session": transfer_session,
            },
            "experiment_reduction": (
                1.0 - len(transfer_rows) / len(cold_rows)
            ),
        }

    def audit_planning(
        self,
        *,
        spec: CausalDomainSpec,
        episodes: int,
        seed_offset: int,
    ) -> Dict[str, Any]:
        graph = self.learner.graph_from_record(
            self.runtime.store.state["causal_graphs"][spec.domain_id]
        )
        rows = []
        for episode in range(episodes):
            environment = NamedStochasticLatentDomain(
                spec=spec,
                seed=seed_offset + episode,
            )
            result = self.learner.investigate_and_plan(
                graph=graph,
                runner=environment.step,
                initial_visible=dict(environment.visible),
                action_costs={
                    action: 0.1 for action in spec.probe_actions
                },
                confidence_gate=0.95,
                maximum_experiments=6,
            )
            actual = environment.audit_hidden_factors()
            predicted_by_signal = []
            for signal_index in range(spec.factor_count):
                graph_signal_index = graph.signal_targets.index(
                    spec.signal_targets[signal_index]
                )
                factor = graph.signal_factor_assignments[
                    graph_signal_index
                ]
                predicted_by_signal.append(
                    result["marginals"][factor]["value"]
                )
            rows.append(
                {
                    "episode": episode,
                    "factor_correct": (
                        tuple(predicted_by_signal) == actual
                    ),
                    **result,
                }
            )
        return {
            "episodes": episodes,
            "factor_accuracy": (
                sum(row["factor_correct"] for row in rows) / episodes
            ),
            "goal_success_rate": (
                sum(row["goal_success"] for row in rows) / episodes
            ),
            "average_experiments": (
                sum(row["experiment_count"] for row in rows) / episodes
            ),
            "rows": rows,
        }

    def promote_abstract_procedure(
        self,
        *,
        domain_results: Sequence[Mapping[str, Any]],
        audits: Sequence[Mapping[str, Any]],
    ) -> Dict[str, Any]:
        mean_success = sum(
            float(audit["goal_success_rate"]) for audit in audits
        ) / len(audits)
        all_structures = all(
            row["transfer"]["structure_correct"]
            for row in domain_results
        )
        candidate = ProcedureCandidate(
            procedure_id=(
                "procedure_cross_domain_causal_"
                f"{_canonical_hash(self.ABSTRACT_STEPS)[:12]}"
            ),
            goal="cross_domain_causal_investigation_and_planning",
            steps=list(self.ABSTRACT_STEPS),
            score=mean_success,
            success=bool(
                all_structures
                and mean_success >= 0.90
                and all(
                    row["experiment_reduction"] >= 0.50
                    for row in domain_results
                )
            ),
            evidence={
                "domain_count": len(domain_results),
                "mean_goal_success": mean_success,
                "all_structures_correct": all_structures,
                "provider_used": False,
                "verification": "held_out_simulator_execution",
            },
            source_rules=[
                row["transfer"]["graph"]["graph_id"]
                for row in domain_results
            ],
        )
        promotion = self.runtime.skills.promote(candidate)
        outcome = self.runtime.skills.record_outcome(
            procedure_id=candidate.procedure_id,
            success=candidate.success,
            score=candidate.score,
            evidence=candidate.evidence,
        )
        return {
            "candidate": candidate.to_dict(),
            "promotion": promotion,
            "outcome": outcome,
        }
