from __future__ import annotations

import math
import uuid
from dataclasses import dataclass
from typing import Any, Callable, Dict, Iterable, List, Mapping, Sequence, Tuple

from backend.modules.hexcore.persistent_learning import (
    HexCorePersistentLearningStore,
    _canonical_hash,
    _json_safe,
    _utc_timestamp,
)


State = Mapping[str, int]
TransitionRunner = Callable[[str], Mapping[str, Any]]


@dataclass(frozen=True)
class BooleanRule:
    """A bounded, inspectable transition rule built by the learner."""

    kind: str
    arguments: Tuple[str, ...]
    complexity: int

    def evaluate(self, state: State, action: str) -> int:
        args = self.arguments
        if self.kind == "constant":
            return int(args[0])
        if self.kind == "copy":
            return int(bool(state[args[0]]))
        if self.kind == "not":
            return 1 - int(bool(state[args[0]]))
        if self.kind == "action":
            return int(action == args[0])
        if self.kind == "xor_action":
            return int(bool(state[args[0]])) ^ int(action == args[1])
        if self.kind in {"and", "or", "xor"}:
            left = int(bool(state[args[0]]))
            right = int(bool(state[args[1]]))
            if self.kind == "and":
                return left & right
            if self.kind == "or":
                return left | right
            return left ^ right
        if self.kind == "if_action_and":
            trigger, left, right, fallback = args
            if action == trigger:
                return int(bool(state[left])) & int(bool(state[right]))
            return int(bool(state[fallback]))
        raise ValueError(f"unknown rule kind: {self.kind}")

    @property
    def parents(self) -> List[str]:
        if self.kind in {"constant", "action"}:
            return []
        if self.kind in {"copy", "not", "xor_action"}:
            return [self.arguments[0]]
        if self.kind in {"and", "or", "xor"}:
            return sorted(set(self.arguments[:2]))
        if self.kind == "if_action_and":
            return sorted(set(self.arguments[1:]))
        return []

    @property
    def action_conditions(self) -> List[str]:
        if self.kind == "action":
            return [self.arguments[0]]
        if self.kind == "xor_action":
            return [self.arguments[1]]
        if self.kind == "if_action_and":
            return [self.arguments[0]]
        return []

    def to_dict(self) -> Dict[str, Any]:
        return {
            "kind": self.kind,
            "arguments": list(self.arguments),
            "complexity": self.complexity,
            "parents": self.parents,
            "action_conditions": self.action_conditions,
        }


@dataclass(frozen=True)
class CausalGraph:
    graph_id: str
    rules: Dict[str, BooleanRule]
    source: str

    @property
    def complexity(self) -> int:
        return sum(rule.complexity for rule in self.rules.values())

    @property
    def edges(self) -> List[Dict[str, str]]:
        edges: List[Dict[str, str]] = []
        for target, rule in sorted(self.rules.items()):
            edges.extend(
                {"source": source, "target": target, "edge_type": "state"}
                for source in rule.parents
            )
            edges.extend(
                {"source": f"action:{action}", "target": target, "edge_type": "intervention"}
                for action in rule.action_conditions
            )
        return edges

    def predict(self, state: State, action: str) -> Dict[str, int]:
        return {
            target: rule.evaluate(state, action)
            for target, rule in self.rules.items()
        }

    def to_dict(self) -> Dict[str, Any]:
        return _json_safe(
            {
                "graph_id": self.graph_id,
                "source": self.source,
                "complexity": self.complexity,
                "edges": self.edges,
                "rules": {
                    target: rule.to_dict()
                    for target, rule in sorted(self.rules.items())
                },
            }
        )


def _transition_accuracy(graph: CausalGraph, rows: Sequence[Mapping[str, Any]]) -> float:
    if not rows:
        return 0.0
    correct = 0
    total = 0
    for row in rows:
        prediction = graph.predict(row["state"], str(row["action"]))
        for target, value in row["next_state"].items():
            total += 1
            correct += int(int(prediction[target]) == int(value))
    return correct / max(1, total)


class GovernedOpenCausalGraphLearner:
    """Constructs bounded causal graphs when retained explanations are inadequate.

    The learner receives variable and action vocabularies, but not a list of
    possible graphs. It expands an inspectable rule grammar, scores rules on
    development observations, and permits persistence only after held-out gain,
    complexity, and CAU gates pass.
    """

    def __init__(self, store: HexCorePersistentLearningStore) -> None:
        self.store = store

    @staticmethod
    def persistence_graph(world_id: str, variables: Sequence[str]) -> CausalGraph:
        return CausalGraph(
            graph_id=f"graph_{_canonical_hash([world_id, 'persistence'])[:16]}",
            rules={
                variable: BooleanRule("copy", (variable,), 1)
                for variable in variables
            },
            source="initial_persistence_assumption",
        )

    @staticmethod
    def _grammar(
        *,
        variables: Sequence[str],
        actions: Sequence[str],
        maximum_rule_complexity: int,
    ) -> List[BooleanRule]:
        rules = [
            BooleanRule("constant", ("0",), 1),
            BooleanRule("constant", ("1",), 1),
        ]
        rules.extend(BooleanRule("copy", (name,), 1) for name in variables)
        rules.extend(BooleanRule("not", (name,), 2) for name in variables)
        rules.extend(BooleanRule("action", (action,), 1) for action in actions)
        rules.extend(
            BooleanRule("xor_action", (name, action), 2)
            for name in variables
            for action in actions
        )
        for left_index, left in enumerate(variables):
            for right in variables[left_index + 1 :]:
                for kind in ("and", "or", "xor"):
                    rules.append(BooleanRule(kind, (left, right), 2))
        rules.extend(
            BooleanRule("if_action_and", (action, left, right, fallback), 4)
            for action in actions
            for left_index, left in enumerate(variables)
            for right in variables[left_index + 1 :]
            for fallback in variables
        )
        unique = {
            (rule.kind, rule.arguments): rule
            for rule in rules
            if rule.complexity <= maximum_rule_complexity
        }
        return sorted(
            unique.values(),
            key=lambda rule: (rule.complexity, rule.kind, rule.arguments),
        )

    @staticmethod
    def _rule_accuracy(
        rule: BooleanRule,
        target: str,
        rows: Sequence[Mapping[str, Any]],
    ) -> float:
        if not rows:
            return 0.0
        correct = sum(
            int(
                rule.evaluate(row["state"], str(row["action"]))
                == int(row["next_state"][target])
            )
            for row in rows
        )
        return correct / len(rows)

    def construct_graph(
        self,
        *,
        world_id: str,
        variables: Sequence[str],
        actions: Sequence[str],
        development_rows: Sequence[Mapping[str, Any]],
        maximum_rule_complexity: int = 4,
        complexity_penalty: float = 0.002,
    ) -> Tuple[CausalGraph, Dict[str, List[Dict[str, Any]]]]:
        grammar = self._grammar(
            variables=variables,
            actions=actions,
            maximum_rule_complexity=maximum_rule_complexity,
        )
        selected: Dict[str, BooleanRule] = {}
        contenders: Dict[str, List[Dict[str, Any]]] = {}
        for target in variables:
            ranked = []
            for rule in grammar:
                accuracy = self._rule_accuracy(rule, target, development_rows)
                ranked.append(
                    {
                        "rule": rule,
                        "accuracy": accuracy,
                        "objective": accuracy - complexity_penalty * rule.complexity,
                    }
                )
            ranked.sort(
                key=lambda row: (
                    row["objective"],
                    row["accuracy"],
                    -row["rule"].complexity,
                ),
                reverse=True,
            )
            selected[target] = ranked[0]["rule"]
            contenders[target] = [
                {
                    "rule": row["rule"].to_dict(),
                    "development_accuracy": round(row["accuracy"], 8),
                    "objective": round(row["objective"], 8),
                }
                for row in ranked[:8]
            ]
        signature = {
            target: rule.to_dict() for target, rule in sorted(selected.items())
        }
        graph = CausalGraph(
            graph_id=f"graph_{_canonical_hash([world_id, signature])[:16]}",
            rules=selected,
            source="bounded_symbolic_graph_construction",
        )
        return graph, contenders

    def criticise(
        self,
        *,
        graph: CausalGraph,
        held_out_rows: Sequence[Mapping[str, Any]],
        adequacy_gate: float = 0.95,
    ) -> Dict[str, Any]:
        accuracy = _transition_accuracy(graph, held_out_rows)
        return {
            "criticism_id": f"criticism_{uuid.uuid4().hex[:16]}",
            "graph_id": graph.graph_id,
            "held_out_transition_accuracy": round(accuracy, 8),
            "adequacy_gate": adequacy_gate,
            "adequate": accuracy >= adequacy_gate,
            "decision": "MODEL_ADEQUATE" if accuracy >= adequacy_gate else "NONE_ADEQUATE",
            "timestamp": _utc_timestamp(),
        }

    @staticmethod
    def _top_rule_predictions(
        contenders: Mapping[str, Sequence[Mapping[str, Any]]],
        state: State,
        action: str,
    ) -> List[Tuple[int, ...]]:
        targets = sorted(contenders)
        alternatives: List[List[int]] = []
        for target in targets:
            values = []
            for row in contenders[target][:4]:
                payload = row["rule"]
                rule = BooleanRule(
                    str(payload["kind"]),
                    tuple(payload["arguments"]),
                    int(payload["complexity"]),
                )
                values.append(rule.evaluate(state, action))
            alternatives.append(sorted(set(values)))
        predictions: List[Tuple[int, ...]] = [()]
        for values in alternatives:
            predictions = [prefix + (value,) for prefix in predictions for value in values]
        return predictions

    def select_experiment(
        self,
        *,
        current_state: State,
        actions: Sequence[str],
        action_costs: Mapping[str, float],
        contenders: Mapping[str, Sequence[Mapping[str, Any]]] | None = None,
        action_counts: Mapping[str, int] | None = None,
        cost_weight: float = 0.1,
    ) -> Dict[str, Any]:
        action_counts = action_counts or {}
        candidates = []
        for action in actions:
            if contenders:
                predictions = self._top_rule_predictions(
                    contenders, current_state, action
                )
                counts: Dict[Tuple[int, ...], int] = {}
                for prediction in predictions:
                    counts[prediction] = counts.get(prediction, 0) + 1
                total = max(1, sum(counts.values()))
                entropy = -sum(
                    (count / total) * math.log2(count / total)
                    for count in counts.values()
                )
            else:
                entropy = 1.0 / (1.0 + int(action_counts.get(action, 0)))
            exploration_bonus = 0.25 / (1.0 + int(action_counts.get(action, 0)))
            cost = float(action_costs.get(action, 0.0))
            utility = entropy + exploration_bonus - cost_weight * cost
            candidates.append(
                {
                    "action": action,
                    "expected_information_gain_proxy": round(entropy, 8),
                    "exploration_bonus": round(exploration_bonus, 8),
                    "cost": cost,
                    "utility": round(utility, 8),
                }
            )
        candidates.sort(
            key=lambda row: (
                row["utility"],
                row["expected_information_gain_proxy"],
                -row["cost"],
                row["action"],
            ),
            reverse=True,
        )
        return {"selected": candidates[0], "candidates": candidates}

    def discover(
        self,
        *,
        world_id: str,
        variables: Sequence[str],
        actions: Sequence[str],
        action_costs: Mapping[str, float],
        experiment_runner: TransitionRunner,
        initial_state: Mapping[str, int],
        initial_graph: CausalGraph | None = None,
        experiments: int = 48,
        held_out_stride: int = 4,
        adequacy_gate: float = 0.95,
        minimum_held_out_gain: float = 0.05,
        maximum_graph_complexity: int = 12,
        maximum_rule_complexity: int = 4,
        persist: bool = True,
    ) -> Dict[str, Any]:
        if experiments < 12:
            raise ValueError("open discovery requires at least 12 experiments")
        initial_graph = initial_graph or self.persistence_graph(world_id, variables)
        observations: List[Dict[str, Any]] = []
        action_counts: Dict[str, int] = {}
        state = {key: int(value) for key, value in initial_state.items()}
        contenders = None
        trace = []
        for index in range(experiments):
            selection = self.select_experiment(
                current_state=state,
                actions=actions,
                action_costs=action_costs,
                contenders=contenders,
                action_counts=action_counts,
            )
            action = str(selection["selected"]["action"])
            observed = dict(experiment_runner(action) or {})
            next_state = {
                key: int(value)
                for key, value in dict(observed.get("next_state") or {}).items()
            }
            if set(next_state) != set(variables):
                raise ValueError("experiment_runner returned incomplete next_state")
            row = {
                "index": index,
                "state": dict(state),
                "action": action,
                "next_state": next_state,
                "evidence": _json_safe(observed.get("evidence") or {}),
            }
            observations.append(row)
            action_counts[action] = action_counts.get(action, 0) + 1
            state = next_state
            if len(observations) >= 8 and (index + 1) % 4 == 0:
                development = [
                    item for item in observations
                    if item["index"] % held_out_stride != 0
                ]
                _, contenders = self.construct_graph(
                    world_id=world_id,
                    variables=variables,
                    actions=actions,
                    development_rows=development,
                    maximum_rule_complexity=maximum_rule_complexity,
                )
            trace.append(
                {
                    "index": index,
                    "selection": selection["selected"],
                    "action": action,
                    "next_state": next_state,
                }
            )

        development = [
            row for row in observations if row["index"] % held_out_stride != 0
        ]
        held_out = [
            row for row in observations if row["index"] % held_out_stride == 0
        ]
        initial_criticism = self.criticise(
            graph=initial_graph,
            held_out_rows=held_out,
            adequacy_gate=adequacy_gate,
        )
        graph, contenders = self.construct_graph(
            world_id=world_id,
            variables=variables,
            actions=actions,
            development_rows=development,
            maximum_rule_complexity=maximum_rule_complexity,
        )
        constructed_criticism = self.criticise(
            graph=graph,
            held_out_rows=held_out,
            adequacy_gate=adequacy_gate,
        )
        held_out_gain = (
            constructed_criticism["held_out_transition_accuracy"]
            - initial_criticism["held_out_transition_accuracy"]
        )
        novel_edges = [
            edge for edge in graph.edges if edge not in initial_graph.edges
        ]
        errors = []
        if initial_criticism["adequate"]:
            errors.append("INITIAL_MODEL_NOT_REJECTED")
        if not constructed_criticism["adequate"]:
            errors.append("CONSTRUCTED_MODEL_INADEQUATE")
        if held_out_gain < minimum_held_out_gain:
            errors.append("INSUFFICIENT_HELD_OUT_GAIN")
        if graph.complexity > maximum_graph_complexity:
            errors.append("COMPLEXITY_CAP_EXCEEDED")
        if not novel_edges:
            errors.append("NO_NOVEL_STRUCTURE")
        accepted = not errors
        session = {
            "schema_version": "aion.hexcore.open_causal_graph_session.v1",
            "session_id": f"open_graph_{uuid.uuid4().hex[:16]}",
            "world_id": world_id,
            "initial_graph": initial_graph.to_dict(),
            "initial_model_criticism": initial_criticism,
            "constructed_graph": graph.to_dict(),
            "constructed_model_criticism": constructed_criticism,
            "held_out_gain": round(held_out_gain, 8),
            "novel_edges": novel_edges,
            "accepted": accepted,
            "errors": errors,
            "observations": observations,
            "active_experiment_trace": trace,
            "action_counts": action_counts,
            "development_observations": len(development),
            "held_out_observations": len(held_out),
            "complexity_cap": maximum_graph_complexity,
            "timestamp": _utc_timestamp(),
        }
        if persist:
            before = self.store.prepare_mutation()
            try:
                self.store.state["model_criticisms"].extend(
                    [initial_criticism, constructed_criticism]
                )
                expansion = {
                    "schema_version": "aion.hexcore.hypothesis_expansion.v1",
                    "session_id": session["session_id"],
                    "world_id": world_id,
                    "accepted": accepted,
                    "held_out_gain": round(held_out_gain, 8),
                    "novel_edges": novel_edges,
                    "complexity": graph.complexity,
                    "complexity_cap": maximum_graph_complexity,
                    "errors": errors,
                    "timestamp": _utc_timestamp(),
                }
                self.store.state["hypothesis_expansions"].append(expansion)
                if accepted:
                    self.store.state["causal_graphs"][world_id] = {
                        **graph.to_dict(),
                        "status": "active",
                        "source_session_id": session["session_id"],
                        "held_out_transition_accuracy": (
                            constructed_criticism["held_out_transition_accuracy"]
                        ),
                    }
                self.store.state["discovery_sessions"].append(session)
                self.store.commit(
                    reason=f"open_causal_graph_discovery:{session['session_id']}"
                )
            except Exception:
                self.store.rollback(before)
                raise
        return session


class MultiVariableBooleanEnvironment:
    """Unknown transition system used to audit open graph construction."""

    def __init__(self, *, initial_state: Mapping[str, int] | None = None) -> None:
        self.state = {
            "signal": 0,
            "gate": 0,
            "output": 0,
            **dict(initial_state or {}),
        }

    def step(self, action: str) -> Dict[str, Any]:
        before = dict(self.state)
        signal = int(bool(before["signal"])) ^ int(action == "flip_signal")
        gate = int(bool(before["gate"])) ^ int(action == "flip_gate")
        output = (
            int(bool(before["signal"])) & int(bool(before["gate"]))
            if action == "pulse"
            else int(bool(before["output"]))
        )
        self.state = {"signal": signal, "gate": gate, "output": output}
        return {
            "next_state": dict(self.state),
            "evidence": {
                "state_before": before,
                "action_observed": action,
                "state_after": dict(self.state),
                "hidden_rule_visible": False,
            },
        }

