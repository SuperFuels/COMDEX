from __future__ import annotations

import itertools
import uuid
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Mapping, Sequence, Tuple

from backend.modules.hexcore.persistent_learning import (
    HexCorePersistentLearningStore,
    _canonical_hash,
    _json_safe,
    _utc_timestamp,
)


EpisodeRunnerFactory = Callable[[int], Callable[[str], Mapping[str, Any]]]


@dataclass(frozen=True)
class LatentStateGraph:
    """An inspectable one-bit hidden-state transition model."""

    graph_id: str
    latent_name: str
    latent_initial: int
    latent_toggle_action: str
    visible_target: str
    readout_action: str
    source: str = "bounded_latent_state_construction"
    revision: int = 1

    @property
    def complexity(self) -> int:
        # One hidden node, one hidden transition, one action-gated readout,
        # and one visible persistence path.
        return 4

    @property
    def edges(self) -> List[Dict[str, str]]:
        return [
            {
                "source": self.latent_name,
                "target": self.latent_name,
                "edge_type": "latent_persistence",
            },
            {
                "source": f"action:{self.latent_toggle_action}",
                "target": self.latent_name,
                "edge_type": "latent_intervention",
            },
            {
                "source": self.latent_name,
                "target": self.visible_target,
                "edge_type": "latent_readout",
            },
            {
                "source": f"action:{self.readout_action}",
                "target": self.visible_target,
                "edge_type": "readout_intervention",
            },
            {
                "source": self.visible_target,
                "target": self.visible_target,
                "edge_type": "state",
            },
        ]

    def step(
        self,
        visible_state: Mapping[str, int],
        latent_state: int,
        action: str,
    ) -> Tuple[Dict[str, int], int]:
        next_visible = {
            key: int(bool(value)) for key, value in visible_state.items()
        }
        if action == self.readout_action:
            next_visible[self.visible_target] = (
                int(bool(visible_state[self.visible_target]))
                ^ int(bool(latent_state))
            )
        next_latent = int(bool(latent_state)) ^ int(
            action == self.latent_toggle_action
        )
        return next_visible, next_latent

    def to_dict(self) -> Dict[str, Any]:
        return _json_safe(
            {
                "schema_version": "aion.hexcore.latent_state_graph.v1",
                "graph_id": self.graph_id,
                "latent_name": self.latent_name,
                "latent_initial": self.latent_initial,
                "latent_cardinality": 2,
                "latent_toggle_action": self.latent_toggle_action,
                "visible_target": self.visible_target,
                "readout_action": self.readout_action,
                "source": self.source,
                "revision": self.revision,
                "complexity": self.complexity,
                "edges": self.edges,
            }
        )


def _group_episodes(
    rows: Sequence[Mapping[str, Any]],
) -> List[List[Mapping[str, Any]]]:
    grouped: Dict[str, List[Mapping[str, Any]]] = {}
    for row in rows:
        grouped.setdefault(str(row["episode_id"]), []).append(row)
    return [
        sorted(episode, key=lambda row: int(row["step"]))
        for _, episode in sorted(grouped.items())
    ]


def _latent_accuracy(
    graph: LatentStateGraph,
    rows: Sequence[Mapping[str, Any]],
) -> float:
    correct = 0
    total = 0
    for episode in _group_episodes(rows):
        latent = graph.latent_initial
        for row in episode:
            predicted, latent = graph.step(
                row["state"], latent, str(row["action"])
            )
            for field, expected in row["next_state"].items():
                total += 1
                correct += int(int(predicted[field]) == int(expected))
    return correct / max(1, total)


class GovernedLatentStateLearner:
    """Adds hidden state only after visible Markov explanations fail."""

    def __init__(self, store: HexCorePersistentLearningStore) -> None:
        self.store = store

    @staticmethod
    def design_diagnostic_sequences(
        *,
        actions: Sequence[str],
        episode_count: int,
        steps_per_episode: int,
    ) -> List[List[str]]:
        """Select experiments by balanced ordered-pair coverage.

        This is an active design policy rather than a supplied probe set. It
        maximises untested action-history coverage, which is precisely the
        evidence required to distinguish hidden state from visible Markov state.
        """

        pairs = list(itertools.product(sorted(actions), repeat=2))
        pair_counts = {pair: 0 for pair in pairs}
        sequences: List[List[str]] = []
        for episode_index in range(episode_count):
            sequence: List[str] = []
            while len(sequence) < steps_per_episode:
                ranked = sorted(
                    pairs,
                    key=lambda pair: (
                        pair_counts[pair],
                        _canonical_hash([episode_index, len(sequence), pair]),
                    ),
                )
                selected = ranked[0]
                pair_counts[selected] += 1
                sequence.extend(selected)
            sequences.append(sequence[:steps_per_episode])
        return sequences

    @staticmethod
    def collect(
        *,
        experiment_runner_factory: EpisodeRunnerFactory,
        sequences: Sequence[Sequence[str]],
        phase: str,
    ) -> List[Dict[str, Any]]:
        rows: List[Dict[str, Any]] = []
        for episode_index, actions in enumerate(sequences):
            runner = experiment_runner_factory(episode_index)
            for step, action in enumerate(actions):
                observation = dict(runner(str(action)) or {})
                state = {
                    key: int(value)
                    for key, value in dict(observation["state"]).items()
                }
                next_state = {
                    key: int(value)
                    for key, value in dict(
                        observation["next_state"]
                    ).items()
                }
                rows.append(
                    {
                        "episode_id": f"{phase}_{episode_index:04d}",
                        "phase": phase,
                        "step": step,
                        "state": state,
                        "action": str(action),
                        "next_state": next_state,
                        "evidence": _json_safe(
                            observation.get("evidence") or {}
                        ),
                    }
                )
        return rows

    @staticmethod
    def visible_alias_conflicts(
        rows: Sequence[Mapping[str, Any]],
    ) -> Dict[str, Any]:
        outcomes: Dict[str, set[Tuple[Tuple[str, int], ...]]] = {}
        for row in rows:
            key = _canonical_hash(
                {
                    "state": row["state"],
                    "action": row["action"],
                }
            )
            outcome = tuple(
                sorted(
                    (str(field), int(value))
                    for field, value in row["next_state"].items()
                )
            )
            outcomes.setdefault(key, set()).add(outcome)
        conflicting = [
            key for key, values in outcomes.items() if len(values) > 1
        ]
        return {
            "identical_visible_contexts": len(outcomes),
            "conflicting_contexts": len(conflicting),
            "conflict_detected": bool(conflicting),
            "conflicting_context_hashes": conflicting,
        }

    @staticmethod
    def visible_markov_accuracy(
        *,
        development_rows: Sequence[Mapping[str, Any]],
        held_out_rows: Sequence[Mapping[str, Any]],
    ) -> float:
        lookup: Dict[str, Dict[Tuple[Tuple[str, int], ...], int]] = {}
        for row in development_rows:
            key = _canonical_hash(
                {"state": row["state"], "action": row["action"]}
            )
            outcome = tuple(
                sorted(
                    (str(field), int(value))
                    for field, value in row["next_state"].items()
                )
            )
            lookup.setdefault(key, {})
            lookup[key][outcome] = lookup[key].get(outcome, 0) + 1
        majority = {
            key: max(counts, key=counts.get)
            for key, counts in lookup.items()
        }
        correct = 0
        total = 0
        for row in held_out_rows:
            key = _canonical_hash(
                {"state": row["state"], "action": row["action"]}
            )
            prediction = majority.get(key)
            if prediction is None:
                prediction = tuple(
                    sorted(
                        (str(field), int(value))
                        for field, value in row["state"].items()
                    )
                )
            for field, expected in row["next_state"].items():
                total += 1
                predicted = dict(prediction).get(field)
                correct += int(predicted == int(expected))
        return correct / max(1, total)

    @staticmethod
    def split_by_episode(
        rows: Sequence[Mapping[str, Any]],
        held_out_modulus: int = 4,
    ) -> Tuple[List[Mapping[str, Any]], List[Mapping[str, Any]]]:
        development, held_out = [], []
        for row in rows:
            episode_number = int(str(row["episode_id"]).rsplit("_", 1)[-1])
            destination = (
                held_out
                if episode_number % held_out_modulus == 0
                else development
            )
            destination.append(row)
        return development, held_out

    def construct_latent_graph(
        self,
        *,
        world_id: str,
        visible_variables: Sequence[str],
        actions: Sequence[str],
        development_rows: Sequence[Mapping[str, Any]],
        revision: int,
        complexity_penalty: float = 0.002,
    ) -> Tuple[LatentStateGraph, List[Dict[str, Any]]]:
        candidates = []
        for latent_initial in (0, 1):
            for toggle_action in actions:
                for visible_target in visible_variables:
                    for readout_action in actions:
                        signature = [
                            world_id,
                            latent_initial,
                            toggle_action,
                            visible_target,
                            readout_action,
                            revision,
                        ]
                        graph = LatentStateGraph(
                            graph_id=(
                                f"latent_graph_"
                                f"{_canonical_hash(signature)[:16]}"
                            ),
                            latent_name=f"latent_context_{revision}",
                            latent_initial=latent_initial,
                            latent_toggle_action=str(toggle_action),
                            visible_target=str(visible_target),
                            readout_action=str(readout_action),
                            revision=revision,
                        )
                        accuracy = _latent_accuracy(
                            graph, development_rows
                        )
                        candidates.append(
                            {
                                "graph": graph,
                                "development_accuracy": accuracy,
                                "objective": (
                                    accuracy
                                    - complexity_penalty * graph.complexity
                                ),
                            }
                        )
        candidates.sort(
            key=lambda row: (
                row["objective"],
                row["development_accuracy"],
                -row["graph"].complexity,
                row["graph"].graph_id,
            ),
            reverse=True,
        )
        return candidates[0]["graph"], [
            {
                "graph": row["graph"].to_dict(),
                "development_accuracy": round(
                    row["development_accuracy"], 8
                ),
                "objective": round(row["objective"], 8),
            }
            for row in candidates[:8]
        ]

    @staticmethod
    def graph_from_record(record: Mapping[str, Any]) -> LatentStateGraph:
        return LatentStateGraph(
            graph_id=str(record["graph_id"]),
            latent_name=str(record["latent_name"]),
            latent_initial=int(record["latent_initial"]),
            latent_toggle_action=str(record["latent_toggle_action"]),
            visible_target=str(record["visible_target"]),
            readout_action=str(record["readout_action"]),
            source=str(record.get("source") or "retained"),
            revision=int(record.get("revision") or 1),
        )

    def discover_or_revise(
        self,
        *,
        world_id: str,
        visible_variables: Sequence[str],
        actions: Sequence[str],
        rows: Sequence[Mapping[str, Any]],
        adequacy_gate: float = 0.90,
        minimum_held_out_gain: float = 0.10,
        maximum_latent_variables: int = 1,
        maximum_graph_complexity: int = 6,
        persist: bool = True,
    ) -> Dict[str, Any]:
        development, held_out = self.split_by_episode(rows)
        alias_diagnostic = self.visible_alias_conflicts(development)
        visible_accuracy = self.visible_markov_accuracy(
            development_rows=development,
            held_out_rows=held_out,
        )
        retained_record = self.store.state["causal_graphs"].get(world_id)
        retained_graph = (
            self.graph_from_record(retained_record)
            if retained_record
            and retained_record.get("schema_version")
            == "aion.hexcore.latent_state_graph.v1"
            else None
        )
        retained_accuracy = (
            _latent_accuracy(retained_graph, held_out)
            if retained_graph
            else None
        )
        current_accuracy = (
            retained_accuracy
            if retained_accuracy is not None
            else visible_accuracy
        )
        current_adequate = current_accuracy >= adequacy_gate
        revision = (retained_graph.revision + 1) if retained_graph else 1
        proposed_graph = None
        contenders: List[Dict[str, Any]] = []
        proposed_accuracy = current_accuracy
        if not current_adequate and alias_diagnostic["conflict_detected"]:
            proposed_graph, contenders = self.construct_latent_graph(
                world_id=world_id,
                visible_variables=visible_variables,
                actions=actions,
                development_rows=development,
                revision=revision,
            )
            proposed_accuracy = _latent_accuracy(
                proposed_graph, held_out
            )
        gain = proposed_accuracy - current_accuracy
        errors = []
        if current_adequate:
            errors.append("CURRENT_MODEL_ADEQUATE")
        if not alias_diagnostic["conflict_detected"]:
            errors.append("NO_VISIBLE_ALIAS_CONFLICT")
        if proposed_graph is None:
            errors.append("NO_LATENT_GRAPH_PROPOSED")
        elif proposed_graph.complexity > maximum_graph_complexity:
            errors.append("COMPLEXITY_CAP_EXCEEDED")
        if maximum_latent_variables < 1:
            errors.append("LATENT_VARIABLE_CAP_EXCEEDED")
        if proposed_accuracy < adequacy_gate:
            errors.append("PROPOSED_GRAPH_INADEQUATE")
        if gain < minimum_held_out_gain:
            errors.append("INSUFFICIENT_HELD_OUT_GAIN")
        accepted = not errors
        criticism = {
            "criticism_id": f"criticism_{uuid.uuid4().hex[:16]}",
            "world_id": world_id,
            "visible_markov_accuracy": round(visible_accuracy, 8),
            "retained_graph_accuracy": (
                round(retained_accuracy, 8)
                if retained_accuracy is not None
                else None
            ),
            "current_accuracy": round(current_accuracy, 8),
            "adequacy_gate": adequacy_gate,
            "decision": (
                "MODEL_ADEQUATE"
                if current_adequate
                else "NONE_ADEQUATE"
            ),
            "alias_diagnostic": alias_diagnostic,
            "timestamp": _utc_timestamp(),
        }
        session = {
            "schema_version": (
                "aion.hexcore.latent_state_discovery_session.v1"
            ),
            "session_id": f"latent_session_{uuid.uuid4().hex[:16]}",
            "world_id": world_id,
            "model_criticism": criticism,
            "retained_graph_before": (
                retained_graph.to_dict() if retained_graph else None
            ),
            "proposed_graph": (
                proposed_graph.to_dict() if proposed_graph else None
            ),
            "held_out_accuracy": round(proposed_accuracy, 8),
            "held_out_gain": round(gain, 8),
            "development_episodes": len(_group_episodes(development)),
            "held_out_episodes": len(_group_episodes(held_out)),
            "contenders": contenders,
            "accepted": accepted,
            "errors": errors,
            "revision": revision,
            "timestamp": _utc_timestamp(),
        }
        if persist:
            before = self.store.prepare_mutation()
            try:
                self.store.state["model_criticisms"].append(criticism)
                expansion = {
                    "schema_version": (
                        "aion.hexcore.latent_hypothesis_expansion.v1"
                    ),
                    "session_id": session["session_id"],
                    "world_id": world_id,
                    "accepted": accepted,
                    "revision": revision,
                    "held_out_gain": round(gain, 8),
                    "errors": errors,
                    "timestamp": _utc_timestamp(),
                }
                self.store.state["hypothesis_expansions"].append(expansion)
                if accepted and proposed_graph is not None:
                    record = {
                        **proposed_graph.to_dict(),
                        "status": "active",
                        "source_session_id": session["session_id"],
                        "held_out_transition_accuracy": round(
                            proposed_accuracy, 8
                        ),
                        "supersedes_graph_id": (
                            retained_graph.graph_id
                            if retained_graph
                            else None
                        ),
                    }
                    self.store.state["causal_graphs"][world_id] = record
                    self.store.state["latent_variables"][
                        proposed_graph.latent_name
                    ] = {
                        "schema_version": (
                            "aion.hexcore.latent_variable.v1"
                        ),
                        "latent_name": proposed_graph.latent_name,
                        "world_id": world_id,
                        "cardinality": 2,
                        "status": "active",
                        "source_graph_id": proposed_graph.graph_id,
                        "created_at": _utc_timestamp(),
                    }
                    if retained_graph:
                        old = self.store.state["latent_variables"].get(
                            retained_graph.latent_name
                        )
                        if old:
                            old["status"] = "superseded"
                            old["superseded_by"] = (
                                proposed_graph.latent_name
                            )
                self.store.state["discovery_sessions"].append(session)
                self.store.commit(
                    reason=f"latent_state_discovery:{session['session_id']}"
                )
            except Exception:
                self.store.rollback(before)
                raise
        return session


class HiddenModeLampEnvironment:
    """A non-Markov visible process controlled by an unobserved mode bit."""

    def __init__(
        self,
        *,
        toggle_action: str,
        initial_lamp: int = 0,
        initial_mode: int = 0,
    ) -> None:
        self.toggle_action = toggle_action
        self.lamp = int(bool(initial_lamp))
        self._mode = int(bool(initial_mode))

    def step(self, action: str) -> Dict[str, Any]:
        before = {"lamp": self.lamp}
        if action == "pulse":
            self.lamp ^= self._mode
        if action == self.toggle_action:
            self._mode ^= 1
        return {
            "state": before,
            "next_state": {"lamp": self.lamp},
            "evidence": {
                "visible_state_before": before,
                "action": action,
                "visible_state_after": {"lamp": self.lamp},
                "hidden_mode_visible": False,
            },
        }

