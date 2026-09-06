"""Bounded SQI route beams, workflow discovery, and model-route prediction."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
from pathlib import Path
import re
from typing import Any, Iterable, Mapping, Optional


WORKFLOW_CATALOG_PATH = Path(__file__).with_name("workflows.v1.json")


@dataclass(frozen=True)
class WorkflowMatch:
    workflow_id: str
    label: str
    score: float
    matched_keywords: tuple[str, ...]
    required_constraints: tuple[str, ...]
    executor_bound: bool


@dataclass(frozen=True)
class ModelRoutePrediction:
    route_class: str
    model_role: str
    expert_prefetch_profile: str
    confidence: float
    reason: str


@dataclass(frozen=True)
class SQICandidateBeam:
    beam_id: str
    route: str
    score: float
    eligible: bool
    reason: str
    evidence: Mapping[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class RouteCollapse:
    selected_beam_id: str
    selected_route: str
    reason: str
    rejected_beam_ids: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class WorkflowCatalog:
    """Discover governed workflows without claiming authority to execute them."""

    def __init__(self, path: Path = WORKFLOW_CATALOG_PATH) -> None:
        self.path = path
        self.raw = path.read_bytes()
        self.document = json.loads(self.raw)
        self.sha256 = hashlib.sha256(self.raw).hexdigest()

    def lookup(self, text: str) -> Optional[WorkflowMatch]:
        tokens = set(re.findall(r"[a-z0-9]+", text.casefold()))
        matches = []
        for workflow in self.document["workflows"]:
            topic = sorted(tokens & set(workflow["keywords"]))
            actions = sorted(tokens & set(workflow["action_keywords"]))
            if not topic or not actions:
                continue
            score = min(0.89, 0.55 + 0.10 * len(topic) + 0.08 * len(actions))
            matches.append((score, workflow, tuple(sorted(set(topic + actions)))))
        if not matches:
            return None
        score, workflow, keywords = max(matches, key=lambda item: (item[0], item[1]["workflow_id"]))
        return WorkflowMatch(
            workflow_id=workflow["workflow_id"],
            label=workflow["label"],
            score=score,
            matched_keywords=keywords,
            required_constraints=tuple(workflow["required_constraints"]),
            executor_bound=bool(workflow["executor_bound"]),
        )


class ModelRoutePredictor:
    """Predict a bounded fallback profile; this does not invoke a model."""

    @staticmethod
    def predict(text: str, constraints: Iterable[str]) -> ModelRoutePrediction:
        lowered = text.casefold()
        constraints = tuple(constraints)
        if constraints or re.search(r"\b(policy|approval|consent|prohibited|forbidden)\b", lowered):
            return ModelRoutePrediction("policy_reasoning", "constraint_preserving_fallback", "policy", 0.92,
                                        "explicit_policy_or_constraint")
        if re.search(r"\b(code|python|javascript|function|unit test|debug|software)\b", lowered):
            return ModelRoutePrediction("coding", "code_reasoning_fallback", "coding", 0.88,
                                        "coding_vocabulary")
        if "%" in lowered or re.search(r"\b(profit|revenue|cost|price|tax|discount|percent|calculate|times|plus)\b", lowered):
            return ModelRoutePrediction("business_arithmetic", "calculation_fallback", "arithmetic_business", 0.86,
                                        "business_or_arithmetic_vocabulary")
        if re.search(r"\b(plan|organize|organise|steps|workflow|schedule)\b", lowered):
            return ModelRoutePrediction("planning", "planning_fallback", "general", 0.78,
                                        "planning_vocabulary")
        return ModelRoutePrediction("general", "general_fallback", "general", 0.55,
                                    "no_bounded_specialist_signal")


def collapse_beams(beams: Iterable[SQICandidateBeam]) -> RouteCollapse:
    ordered = sorted(beams, key=lambda beam: (-beam.score, beam.beam_id))
    eligible = [beam for beam in ordered if beam.eligible]
    if not eligible:
        raise ValueError("at least one SQI beam must be eligible")
    selected = eligible[0]
    return RouteCollapse(
        selected_beam_id=selected.beam_id,
        selected_route=selected.route,
        reason=f"highest_scoring_eligible_beam:{selected.reason}",
        rejected_beam_ids=tuple(beam.beam_id for beam in ordered if beam.beam_id != selected.beam_id),
    )
