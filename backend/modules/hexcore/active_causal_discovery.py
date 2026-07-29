from __future__ import annotations

import json
import math
import random
import uuid
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Mapping, Optional, Sequence

from backend.modules.hexcore.persistent_learning import (
    HexCorePersistentLearningStore,
    ProcedureCandidate,
    _canonical_hash,
    _json_safe,
    _utc_timestamp,
)


ExperimentRunner = Callable[[str], Mapping[str, Any]]


def _entropy(distribution: Mapping[str, float]) -> float:
    value = 0.0
    for probability in distribution.values():
        p = float(probability)
        if p > 0:
            value -= p * math.log2(p)
    return value


def _normalize(distribution: Mapping[str, float]) -> Dict[str, float]:
    total = sum(max(0.0, float(v)) for v in distribution.values())
    if total <= 0:
        count = max(1, len(distribution))
        return {str(k): 1.0 / count for k in distribution}
    return {str(k): max(0.0, float(v)) / total for k, v in distribution.items()}


@dataclass(frozen=True)
class CausalHypothesis:
    hypothesis_id: str
    action_outcomes: Dict[str, str]
    action_deltas: Dict[str, float]
    reliability: float = 0.9

    def to_dict(self) -> Dict[str, Any]:
        return _json_safe(
            {
                "hypothesis_id": self.hypothesis_id,
                "action_outcomes": self.action_outcomes,
                "action_deltas": self.action_deltas,
                "reliability": self.reliability,
            }
        )


class GovernedActiveCausalLearner:
    """Bayesian hidden-mode learner with cost-aware active experimentation."""

    def __init__(self, store: HexCorePersistentLearningStore) -> None:
        self.store = store

    @staticmethod
    def _hypothesis_map(
        hypotheses: Sequence[CausalHypothesis],
    ) -> Dict[str, CausalHypothesis]:
        return {hypothesis.hypothesis_id: hypothesis for hypothesis in hypotheses}

    @staticmethod
    def _uniform(hypotheses: Sequence[CausalHypothesis]) -> Dict[str, float]:
        if not hypotheses:
            raise ValueError("at least one causal hypothesis is required")
        p = 1.0 / len(hypotheses)
        return {hypothesis.hypothesis_id: p for hypothesis in hypotheses}

    @staticmethod
    def _likelihood(
        hypothesis: CausalHypothesis,
        *,
        action: str,
        outcome: str,
        outcome_count: int,
    ) -> float:
        predicted = hypothesis.action_outcomes[action]
        reliability = min(0.999999, max(0.000001, float(hypothesis.reliability)))
        if outcome == predicted:
            return reliability
        return (1.0 - reliability) / max(1, outcome_count - 1)

    def update_belief(
        self,
        *,
        belief: Mapping[str, float],
        hypotheses: Sequence[CausalHypothesis],
        action: str,
        outcome: str,
    ) -> Dict[str, float]:
        hypothesis_map = self._hypothesis_map(hypotheses)
        outcomes = {
            hypothesis.action_outcomes[action] for hypothesis in hypotheses
        }
        posterior = {
            hypothesis_id: float(prior)
            * self._likelihood(
                hypothesis_map[hypothesis_id],
                action=action,
                outcome=outcome,
                outcome_count=len(outcomes),
            )
            for hypothesis_id, prior in belief.items()
        }
        return _normalize(posterior)

    def expected_information_gain(
        self,
        *,
        belief: Mapping[str, float],
        hypotheses: Sequence[CausalHypothesis],
        action: str,
    ) -> float:
        prior_entropy = _entropy(belief)
        outcomes = sorted(
            {hypothesis.action_outcomes[action] for hypothesis in hypotheses}
        )
        hypothesis_map = self._hypothesis_map(hypotheses)
        expected_posterior_entropy = 0.0
        for outcome in outcomes:
            predictive = sum(
                float(belief[hypothesis_id])
                * self._likelihood(
                    hypothesis_map[hypothesis_id],
                    action=action,
                    outcome=outcome,
                    outcome_count=len(outcomes),
                )
                for hypothesis_id in belief
            )
            if predictive <= 0:
                continue
            posterior = self.update_belief(
                belief=belief,
                hypotheses=hypotheses,
                action=action,
                outcome=outcome,
            )
            expected_posterior_entropy += predictive * _entropy(posterior)
        return max(0.0, prior_entropy - expected_posterior_entropy)

    def select_experiment(
        self,
        *,
        belief: Mapping[str, float],
        hypotheses: Sequence[CausalHypothesis],
        actions: Sequence[str],
        action_costs: Mapping[str, float],
        cost_weight: float = 0.1,
    ) -> Dict[str, Any]:
        candidates = []
        for action in actions:
            information_gain = self.expected_information_gain(
                belief=belief,
                hypotheses=hypotheses,
                action=action,
            )
            cost = float(action_costs.get(action, 0.0))
            utility = information_gain - cost_weight * cost
            candidates.append(
                {
                    "action": action,
                    "expected_information_gain": round(information_gain, 8),
                    "cost": cost,
                    "utility": round(utility, 8),
                }
            )
        candidates.sort(
            key=lambda row: (row["utility"], row["expected_information_gain"], -row["cost"]),
            reverse=True,
        )
        return {"selected": candidates[0], "candidates": candidates}

    def predictive_probability(
        self,
        *,
        belief: Mapping[str, float],
        hypotheses: Sequence[CausalHypothesis],
        action: str,
        outcome: str,
    ) -> float:
        hypothesis_map = self._hypothesis_map(hypotheses)
        outcomes = {
            hypothesis.action_outcomes[action] for hypothesis in hypotheses
        }
        return sum(
            float(probability)
            * self._likelihood(
                hypothesis_map[hypothesis_id],
                action=action,
                outcome=outcome,
                outcome_count=len(outcomes),
            )
            for hypothesis_id, probability in belief.items()
        )

    def discover(
        self,
        *,
        world_id: str,
        hypotheses: Sequence[CausalHypothesis],
        actions: Sequence[str],
        action_costs: Mapping[str, float],
        experiment_runner: ExperimentRunner,
        confidence_gate: float = 0.95,
        maximum_experiments: int = 8,
        minimum_information_gain: float = 0.01,
        reset_belief: bool = False,
        persist: bool = True,
    ) -> Dict[str, Any]:
        stored = self.store.state["causal_beliefs"].get(world_id)
        hypothesis_ids = {hypothesis.hypothesis_id for hypothesis in hypotheses}
        if (
            not reset_belief
            and isinstance(stored, dict)
            and set((stored.get("posterior") or {}).keys()) == hypothesis_ids
        ):
            belief = _normalize(stored["posterior"])
        else:
            belief = self._uniform(hypotheses)

        trace: List[Dict[str, Any]] = []
        total_cost = 0.0
        stop_reason = "MAXIMUM_EXPERIMENTS"
        for _ in range(maximum_experiments):
            confidence = max(belief.values())
            if confidence >= confidence_gate:
                stop_reason = "CONFIDENCE_GATE_REACHED"
                break
            selection = self.select_experiment(
                belief=belief,
                hypotheses=hypotheses,
                actions=actions,
                action_costs=action_costs,
            )
            selected = selection["selected"]
            if selected["expected_information_gain"] < minimum_information_gain:
                stop_reason = "INSUFFICIENT_INFORMATION_GAIN"
                break
            action = selected["action"]
            observation = dict(experiment_runner(action) or {})
            outcome = str(observation.get("outcome") or "")
            if not outcome:
                raise ValueError("experiment_runner must return an outcome")
            prior = dict(belief)
            belief = self.update_belief(
                belief=belief,
                hypotheses=hypotheses,
                action=action,
                outcome=outcome,
            )
            total_cost += float(selected["cost"])
            trace.append(
                {
                    "experiment_index": len(trace) + 1,
                    "action": action,
                    "outcome": outcome,
                    "prior": prior,
                    "posterior": dict(belief),
                    "expected_information_gain": selected["expected_information_gain"],
                    "cost": selected["cost"],
                    "evidence": _json_safe(observation.get("evidence") or {}),
                }
            )
        else:
            stop_reason = "MAXIMUM_EXPERIMENTS"

        winner, confidence = max(belief.items(), key=lambda item: item[1])
        session = {
            "schema_version": "aion.hexcore.causal_discovery_session.v1",
            "session_id": f"discovery_{uuid.uuid4().hex[:16]}",
            "world_id": world_id,
            "hypotheses": [hypothesis.to_dict() for hypothesis in hypotheses],
            "posterior": dict(belief),
            "winner": winner,
            "confidence": round(float(confidence), 8),
            "calibrated": bool(confidence >= confidence_gate),
            "experiment_count": len(trace),
            "total_experiment_cost": round(total_cost, 8),
            "stop_reason": stop_reason,
            "trace": trace,
            "timestamp": _utc_timestamp(),
        }
        if persist:
            before = self.store.prepare_mutation()
            try:
                self.store.state["causal_beliefs"][world_id] = {
                    "schema_version": "aion.hexcore.causal_belief.v1",
                    "world_id": world_id,
                    "posterior": dict(belief),
                    "winner": winner,
                    "confidence": round(float(confidence), 8),
                    "updated_at": _utc_timestamp(),
                    "source_session_id": session["session_id"],
                }
                self.store.state["discovery_sessions"].append(session)
                winner_hypothesis = self._hypothesis_map(hypotheses)[winner]
                for action in actions:
                    rule_id = f"rule_{_canonical_hash([world_id, winner, action])[:16]}"
                    self.store.state["world_rules"][rule_id] = {
                        "schema_version": "aion.hexcore.world_rule.v1",
                        "rule_id": rule_id,
                        "world_id": world_id,
                        "rule_type": "probabilistic_action_effect",
                        "hidden_mode": winner,
                        "action": action,
                        "predicted_outcome": winner_hypothesis.action_outcomes[action],
                        "expected_delta": winner_hypothesis.action_deltas[action],
                        "reliability": winner_hypothesis.reliability,
                        "confidence": round(float(confidence), 8),
                        "status": "active" if confidence >= confidence_gate else "hypothesis",
                        "source_session_id": session["session_id"],
                    }
                self.store.commit(reason=f"active_causal_discovery:{session['session_id']}")
            except Exception:
                self.store.rollback(before)
                raise
        return session

    def detect_change(
        self,
        *,
        world_id: str,
        hypotheses: Sequence[CausalHypothesis],
        action: str,
        outcome: str,
        surprise_threshold: float = 0.2,
    ) -> Dict[str, Any]:
        stored = self.store.state["causal_beliefs"].get(world_id)
        if not stored:
            return {"change_detected": False, "reason": "NO_RETAINED_BELIEF"}
        belief = _normalize(stored["posterior"])
        probability = self.predictive_probability(
            belief=belief,
            hypotheses=hypotheses,
            action=action,
            outcome=outcome,
        )
        detected = probability < surprise_threshold
        event = {
            "schema_version": "aion.hexcore.causal_change_event.v1",
            "event_id": f"change_{uuid.uuid4().hex[:16]}",
            "world_id": world_id,
            "action": action,
            "outcome": outcome,
            "predictive_probability": round(probability, 8),
            "surprise_threshold": surprise_threshold,
            "change_detected": detected,
            "timestamp": _utc_timestamp(),
        }
        if detected:
            before = self.store.prepare_mutation()
            try:
                self.store.state["change_events"].append(event)
                self.store.state["causal_beliefs"][world_id] = {
                    "schema_version": "aion.hexcore.causal_belief.v1",
                    "world_id": world_id,
                    "posterior": self._uniform(hypotheses),
                    "winner": None,
                    "confidence": 1.0 / len(hypotheses),
                    "updated_at": _utc_timestamp(),
                    "reset_by_change_event": event["event_id"],
                }
                self.store.commit(reason=f"causal_change_detected:{event['event_id']}")
            except Exception:
                self.store.rollback(before)
                raise
        return event

    @staticmethod
    def robust_action_count(
        *,
        positive_delta: float,
        negative_delta: float,
        threshold: float,
        reliability: float,
        target_success_probability: float = 0.95,
        maximum_actions: int = 20,
    ) -> int:
        for action_count in range(1, maximum_actions + 1):
            success_probability = 0.0
            for successes in range(action_count + 1):
                final_value = (
                    successes * positive_delta
                    + (action_count - successes) * negative_delta
                )
                if final_value < threshold:
                    continue
                combinations = math.comb(action_count, successes)
                success_probability += (
                    combinations
                    * reliability**successes
                    * (1.0 - reliability) ** (action_count - successes)
                )
            if success_probability >= target_success_probability:
                return action_count
        raise ValueError("target success probability not reachable within maximum_actions")

    def build_robust_procedure(
        self,
        *,
        world_id: str,
        hypotheses: Sequence[CausalHypothesis],
        terminal_action: str,
        threshold: float,
        target_success_probability: float = 0.95,
    ) -> ProcedureCandidate:
        stored = self.store.state["causal_beliefs"].get(world_id)
        if not stored or not stored.get("winner"):
            raise ValueError("no retained causal winner")
        winner = str(stored["winner"])
        hypothesis = self._hypothesis_map(hypotheses)[winner]
        positive_actions = [
            action
            for action, outcome in hypothesis.action_outcomes.items()
            if outcome == "positive" and hypothesis.action_deltas[action] > 0
        ]
        if not positive_actions:
            raise ValueError("winning hypothesis has no positive action")
        action = max(positive_actions, key=lambda name: hypothesis.action_deltas[name])
        negative_deltas = [
            delta for delta in hypothesis.action_deltas.values() if delta < 0
        ]
        negative_delta = min(negative_deltas) if negative_deltas else -1.0
        count = self.robust_action_count(
            positive_delta=float(hypothesis.action_deltas[action]),
            negative_delta=float(negative_delta),
            threshold=float(threshold),
            reliability=float(hypothesis.reliability),
            target_success_probability=target_success_probability,
        )
        source_rules = [
            rule["rule_id"]
            for rule in self.store.state["world_rules"].values()
            if rule.get("world_id") == world_id
            and rule.get("hidden_mode") == winner
            and rule.get("action") == action
        ]
        return ProcedureCandidate(
            procedure_id=f"procedure_{_canonical_hash([world_id, winner, action, count])[:16]}",
            goal=f"opened=True:mode={winner}",
            steps=[action] * count + [terminal_action],
            score=0.0,
            success=False,
            evidence={
                "planning_method": "bayesian_hidden_mode_robust_threshold",
                "posterior_confidence": stored["confidence"],
                "target_success_probability": target_success_probability,
                "action_count": count,
            },
            source_rules=source_rules,
        )


class StochasticHiddenModeEnvironment:
    """Partially observable environment; the mode is never returned to AION."""

    def __init__(
        self,
        *,
        mode: str,
        hypotheses: Sequence[CausalHypothesis],
        threshold: float = 4.0,
        seed: int = 0,
    ) -> None:
        self.mode = mode
        self.hypotheses = {
            hypothesis.hypothesis_id: hypothesis for hypothesis in hypotheses
        }
        self.threshold = threshold
        self.random = random.Random(seed)
        self.value = 0.0

    def probe(self, action: str) -> Dict[str, Any]:
        hypothesis = self.hypotheses[self.mode]
        expected_outcome = hypothesis.action_outcomes[action]
        expected_delta = float(hypothesis.action_deltas[action])
        follows_model = self.random.random() < hypothesis.reliability
        if follows_model:
            outcome = expected_outcome
            delta = expected_delta
        else:
            outcome = "negative" if expected_outcome == "positive" else "positive"
            positive_deltas = [v for v in hypothesis.action_deltas.values() if v > 0]
            negative_deltas = [v for v in hypothesis.action_deltas.values() if v < 0]
            delta = (
                max(positive_deltas)
                if outcome == "positive" and positive_deltas
                else min(negative_deltas)
                if negative_deltas
                else -1.0
            )
        before = self.value
        self.value = max(0.0, self.value + delta)
        return {
            "outcome": outcome,
            "evidence": {
                "observed_before": before,
                "observed_after": self.value,
                "observed_delta": self.value - before,
                "mode_visible": False,
            },
        }

    def run(self, steps: Sequence[str]) -> Dict[str, Any]:
        self.value = 0.0
        trace: List[Dict[str, Any]] = []
        opened = False
        for action in steps:
            if action == "open":
                opened = self.value >= self.threshold
                trace.append(
                    {
                        "action": action,
                        "observed_value": self.value,
                        "opened": opened,
                    }
                )
                break
            result = self.probe(action)
            trace.append({"action": action, **result})
        return {
            "success": opened,
            "score": round(max(0.0, (1.0 if opened else 0.0) - 0.02 * len(trace)), 6),
            "final_value": self.value,
            "trace": trace,
        }
