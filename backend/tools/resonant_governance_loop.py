#!/usr/bin/env python3
"""Guardian-backed resonant governance policy derivation."""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
import math
import time
from typing import Any

from backend.modules.aion_learning.vault_store import AionLearningVaultStore


PREDICTIONS_ENTITY_ID = "trajectory_predictions"
POLICY_ENTITY_ID = "resonance_governance_policy"
POLICY_SCHEMA = "tessaris.resonance-governance-policy.v1"


def _number(value: Any, default: float = 0.0) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError):
        return default
    return result if math.isfinite(result) else default


def load_predictions(store: AionLearningVaultStore) -> list[Mapping[str, Any]]:
    payload = store.get_state(PREDICTIONS_ENTITY_ID, {})
    values = payload.get("predictions", []) if isinstance(payload, Mapping) else []
    if not isinstance(values, list):
        return []
    return [row for row in values if isinstance(row, Mapping)]


def derive_policy(
    predictions: Sequence[Mapping[str, Any]],
    *,
    now: Callable[[], float] = time.time,
) -> dict[str, Any]:
    """Compute new governance thresholds."""
    risks = [
        max(0.0, min(1.0, _number(row.get("predicted_risk"))))
        for row in predictions
    ]
    if not risks:
        risks = [0.0]

    avg_risk = sum(risks) / len(risks)
    max_risk = max(risks)

    # Dynamic thresholds
    rewrite_rate = min(1.0, avg_risk * 1.2)
    ethics_confidence = max(0.3, 1.0 - avg_risk)
    gain_mod = max(0.5, 1.2 - (max_risk * 0.5))

    return {
        "schema": POLICY_SCHEMA,
        "timestamp": _number(now()),
        "avg_risk": round(avg_risk, 3),
        "max_risk": round(max_risk, 3),
        "rewrite_rate": round(rewrite_rate, 3),
        "ethics_confidence": round(ethics_confidence, 3),
        "gain_mod": round(gain_mod, 3),
    }

def apply_policy(
    policy: Mapping[str, Any],
    *,
    runtime_handoff: Callable[[Mapping[str, Any]], None] | None = None,
    ethics_evaluator: Callable[[str], Any] | None = None,
) -> dict[str, Any]:
    """Evaluate and explicitly hand an authorised policy to the live runtime."""

    applied = dict(policy)
    if ethics_evaluator is None:
        applied["ethics_score"] = None
        applied["ethics_evaluation"] = "not_run"
    else:
        applied["ethics_score"] = _number(
            ethics_evaluator("auto governance modulation")
        )
        applied["ethics_evaluation"] = "completed"
    if runtime_handoff is not None:
        runtime_handoff(dict(applied))
    return applied


def run_governance(
    *,
    vault_store: AionLearningVaultStore | None = None,
    workspace_id: str | None = None,
    predictions: Sequence[Mapping[str, Any]] | None = None,
    runtime_handoff: Callable[[Mapping[str, Any]], None] | None = None,
    ethics_evaluator: Callable[[str], Any] | None = None,
    now: Callable[[], float] = time.time,
) -> dict[str, Any]:
    store = vault_store or AionLearningVaultStore(workspace_id=workspace_id)
    if not store.enabled:
        raise RuntimeError("resonant_governance_guardian_store_not_configured")
    source = list(predictions) if predictions is not None else load_predictions(store)
    applied = apply_policy(
        derive_policy(source, now=now),
        runtime_handoff=runtime_handoff,
        ethics_evaluator=ethics_evaluator,
    )
    store.put_state(POLICY_ENTITY_ID, applied)
    return applied


def main() -> None:
    policy = run_governance()
    print(
        "Governance policy applied "
        f"risk={policy['avg_risk']:.2f}, gain={policy['gain_mod']:.2f}"
    )

if __name__ == "__main__":
    main()
