"""Governed task-level selection across verified routes, Qwen, and Granite."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
import re
from typing import Any, Mapping

from .adaptive_runtime import AdaptiveRuntimeResult


_LONG_FORM = re.compile(
    r"\b(detailed|in detail|at least (?:eight|ten|8|10)|comprehensive|safeguards|"
    r"trade-offs?|diagnostic guide|risk assessment)\b",
    re.I,
)


@dataclass(frozen=True)
class TaskModelRoute:
    route: str
    model: str | None
    reason: str
    glyph_address: str
    model_input_sha256: str | None
    decision_sha256: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _seal(payload: Mapping[str, Any]) -> str:
    return hashlib.sha256(
        json.dumps(dict(payload), sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def select_task_model(result: AdaptiveRuntimeResult, public_request: str) -> TaskModelRoute:
    """Select the least costly route that satisfies the declared capability gate."""
    if not result.model_call_required:
        route = result.route
        model = None
        reason = "verified_non_neural_route"
        model_input_sha256 = None
    else:
        prediction = result.proof_receipt["model_route_prediction"]
        route_class = str(prediction["route_class"])
        constraint_count = len(result.proof_receipt.get("meaning_capsule", {}).get("constraints", ()))
        requires_depth = bool(_LONG_FORM.search(public_request))
        if constraint_count or route_class == "policy_reasoning" or requires_depth:
            route = "granite_storage_first"
            model = "granite-3.1-3b-a800m-instruct"
            reason = (
                "constraint_or_policy_requires_strong_route"
                if constraint_count or route_class == "policy_reasoning"
                else "declared_long_form_depth_requires_strong_route"
            )
        elif route_class in {"general", "planning", "coding"}:
            route = "qwen_low_cost"
            model = "qwen3:1.7b"
            reason = "bounded_low_cost_language_route"
        else:
            route = "granite_storage_first"
            model = "granite-3.1-3b-a800m-instruct"
            reason = "unsupported_small_model_class_fails_to_strong_route"
        model_input_sha256 = hashlib.sha256((result.fallback_prompt or "").encode()).hexdigest()

    payload = {
        "route": route,
        "model": model,
        "reason": reason,
        "glyph_address": result.glyph_address,
        "model_input_sha256": model_input_sha256,
    }
    return TaskModelRoute(**payload, decision_sha256=_seal(payload))


def verify_task_model_route(decision: TaskModelRoute | Mapping[str, Any]) -> bool:
    payload = decision.to_dict() if isinstance(decision, TaskModelRoute) else dict(decision)
    digest = payload.pop("decision_sha256", None)
    return digest == _seal(payload)
