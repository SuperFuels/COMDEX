"""AION Phase 21N — Rule Extraction / Generalisation Engine.

Phase 21M taught AION to predict before action.
Phase 21N extracts rules from prediction memory and applies them to a new
similar game.

This is the jump from memory to generalisation:

    remembered outcome -> extracted rule -> transferred decision
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import json
from pathlib import Path
from typing import Any, Dict, List, Optional


DEFAULT_PREDICTION_MEMORY_PATH = Path("data/aion_strategy/prediction_before_action_memory.json")
DEFAULT_RULE_MEMORY_PATH = Path("data/aion_strategy/rule_extraction_memory.json")


@dataclass(frozen=True)
class ExtractedRule:
    rule_id: str
    rule_type: str
    condition: str
    action: str
    expected_reward: float
    confidence: float
    source: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class GeneralisationTrial:
    trial_id: str
    rule_id: str
    source_action: str
    transferred_action: str
    expected_reward: float
    actual_reward: float
    success: bool
    prediction_error: float
    observation: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class RuleExtractionGeneralisationResult:
    engine_version: str
    task_name: str
    rules: List[Dict[str, Any]]
    generalisation_trials: List[Dict[str, Any]]
    extracted_rule_count: int
    generalisation_score: float
    rule_memory_path: str
    prediction_memory_loaded: bool
    evidence: Dict[str, Any]
    boundary_statement: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class AionRuleExtractionGeneralisationEngine:
    def __init__(
        self,
        *,
        prediction_memory_path: Optional[Path] = None,
        rule_memory_path: Optional[Path] = None,
        reward_threshold: float = 0.75,
        penalty_threshold: float = -0.50,
    ):
        self.prediction_memory_path = Path(prediction_memory_path or DEFAULT_PREDICTION_MEMORY_PATH)
        self.rule_memory_path = Path(rule_memory_path or DEFAULT_RULE_MEMORY_PATH)
        self.reward_threshold = reward_threshold
        self.penalty_threshold = penalty_threshold
        self.prediction_memory_loaded = False

    def _load_prediction_memory(self) -> Dict[str, Any]:
        if not self.prediction_memory_path.exists():
            return {}
        try:
            data = json.loads(self.prediction_memory_path.read_text(encoding="utf-8"))
        except Exception:
            return {}
        if not isinstance(data, dict):
            return {}
        self.prediction_memory_loaded = True
        return data

    def extract_rules(self, prediction_memory: Dict[str, Any]) -> List[ExtractedRule]:
        prediction_model = prediction_memory.get("prediction_model", {})
        prediction_confidence = prediction_memory.get("prediction_confidence", {})

        if not isinstance(prediction_model, dict):
            prediction_model = {}
        if not isinstance(prediction_confidence, dict):
            prediction_confidence = {}

        rules: List[ExtractedRule] = []

        for action, reward in sorted(prediction_model.items()):
            try:
                expected_reward = float(reward)
            except Exception:
                continue

            confidence = float(prediction_confidence.get(action, 0.0))

            if expected_reward >= self.reward_threshold:
                rules.append(
                    ExtractedRule(
                        rule_id=f"reward_action_{action}",
                        rule_type="prefer_reward_action",
                        condition=f"if action {action} predicts high reward",
                        action=str(action),
                        expected_reward=round(expected_reward, 6),
                        confidence=round(confidence, 6),
                        source="phase21m_prediction_memory",
                    )
                )
            elif expected_reward <= self.penalty_threshold:
                rules.append(
                    ExtractedRule(
                        rule_id=f"avoid_penalty_action_{action}",
                        rule_type="avoid_penalty_action",
                        condition=f"if action {action} predicts penalty",
                        action=str(action),
                        expected_reward=round(expected_reward, 6),
                        confidence=round(confidence, 6),
                        source="phase21m_prediction_memory",
                    )
                )
            else:
                rules.append(
                    ExtractedRule(
                        rule_id=f"neutral_action_{action}",
                        rule_type="neutral_action",
                        condition=f"if action {action} predicts neutral reward",
                        action=str(action),
                        expected_reward=round(expected_reward, 6),
                        confidence=round(confidence, 6),
                        source="phase21m_prediction_memory",
                    )
                )

        return rules

    def _apply_rule_to_transfer_game(self, rule: ExtractedRule) -> GeneralisationTrial:
        # New game preserves structure but changes labels internally:
        # A -> left, B -> centre, C -> right. Reward remains the transferred centre.
        transfer_map = {"A": "left", "B": "centre", "C": "right"}
        transferred_action = transfer_map.get(rule.action, rule.action)

        actual_reward_map = {
            "left": 0.0,
            "centre": 1.0,
            "right": -1.0,
        }
        actual_reward = actual_reward_map.get(transferred_action, 0.0)

        success = False
        if rule.rule_type == "prefer_reward_action":
            success = actual_reward > 0
        elif rule.rule_type == "avoid_penalty_action":
            success = actual_reward < 0
        elif rule.rule_type == "neutral_action":
            success = actual_reward == 0

        prediction_error = abs(actual_reward - rule.expected_reward)

        if success:
            observation = "rule transferred successfully to structurally similar game"
        else:
            observation = "rule failed transfer and requires revision"

        return GeneralisationTrial(
            trial_id=f"transfer_{rule.rule_id}",
            rule_id=rule.rule_id,
            source_action=rule.action,
            transferred_action=transferred_action,
            expected_reward=rule.expected_reward,
            actual_reward=round(actual_reward, 6),
            success=success,
            prediction_error=round(prediction_error, 6),
            observation=observation,
        )

    def run(self, *, task_name: str = "three_door_rule_extraction_generalisation") -> RuleExtractionGeneralisationResult:
        prediction_memory = self._load_prediction_memory()
        rules = self.extract_rules(prediction_memory)

        trials = [
            self._apply_rule_to_transfer_game(rule)
            for rule in rules
            if rule.rule_type in {"prefer_reward_action", "neutral_action", "avoid_penalty_action"}
        ]

        generalisation_score = (
            sum(1.0 for t in trials if t.success) / max(1, len(trials))
        )

        evidence = {
            "uses_llm_shortcut": False,
            "uses_prediction_memory": True,
            "prediction_memory_loaded": self.prediction_memory_loaded,
            "uses_rule_extraction": True,
            "uses_transfer_generalisation": True,
            "rules_extracted": len(rules),
            "trials_run": len(trials),
            "successful_transfers": sum(1 for t in trials if t.success),
        }

        result = RuleExtractionGeneralisationResult(
            engine_version="phase21n_rule_extraction_generalisation_engine_v1",
            task_name=task_name,
            rules=[r.to_dict() for r in rules],
            generalisation_trials=[t.to_dict() for t in trials],
            extracted_rule_count=len(rules),
            generalisation_score=round(generalisation_score, 6),
            rule_memory_path=str(self.rule_memory_path),
            prediction_memory_loaded=self.prediction_memory_loaded,
            evidence=evidence,
            boundary_statement=(
                "This demonstrates operational rule extraction and transfer generalisation from prediction memory. "
                "It does not prove general intelligence or biological consciousness."
            ),
        )

        self._save_rule_memory(result)
        return result

    def _save_rule_memory(self, result: RuleExtractionGeneralisationResult) -> None:
        previous = {}
        if self.rule_memory_path.exists():
            try:
                previous = json.loads(self.rule_memory_path.read_text(encoding="utf-8"))
            except Exception:
                previous = {}
        if not isinstance(previous, dict):
            previous = {}

        payload = {
            "memory_version": "phase21n_rule_extraction_generalisation_memory_v1",
            "engine_version": result.engine_version,
            "task_name": result.task_name,
            "rules": result.rules,
            "generalisation_trials": result.generalisation_trials,
            "generalisation_score": result.generalisation_score,
            "run_count": int(previous.get("run_count", 0)) + 1,
            "uses_llm_shortcut": False,
            "boundary_statement": result.boundary_statement,
        }

        self.rule_memory_path.parent.mkdir(parents=True, exist_ok=True)
        self.rule_memory_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def run_rule_extraction_generalisation_engine(
    *,
    prediction_memory_path: Optional[Path] = None,
    rule_memory_path: Optional[Path] = None,
    task_name: str = "three_door_rule_extraction_generalisation",
) -> RuleExtractionGeneralisationResult:
    return AionRuleExtractionGeneralisationEngine(
        prediction_memory_path=prediction_memory_path,
        rule_memory_path=rule_memory_path,
    ).run(task_name=task_name)


if __name__ == "__main__":
    result = run_rule_extraction_generalisation_engine()
    print(json.dumps(result.to_dict(), indent=2))
    print(f"\n✅ Rule extraction memory saved to: {result.rule_memory_path}")
