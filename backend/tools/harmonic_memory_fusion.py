#!/usr/bin/env python3
"""Fuse customer resonance memory inside the encrypted Guardian."""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
import math
import time
from typing import Any

from backend.modules.aion_learning.vault_store import AionLearningVaultStore


REFLECTION_ENTITY_ID = "reflection_summary"
GOVERNANCE_ENTITY_ID = "resonance_governance_policy"
HARMONIC_MEMORY_ENTITY_ID = "harmonic_memory"
HARMONIC_MEMORY_SCHEMA = "tessaris.harmonic-memory.v1"


def _number(value: Any, default: float = 0.0) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError):
        return default
    return result if math.isfinite(result) else default


def fuse_memories(
    *,
    vault_store: AionLearningVaultStore | None = None,
    workspace_id: str | None = None,
    reflection: Mapping[str, Any] | None = None,
    governance: Sequence[Mapping[str, Any]] | None = None,
    runtime_handoff: Callable[[Mapping[str, Any]], None] | None = None,
    now: Callable[[], float] = time.time,
) -> dict[str, Any] | None:
    store = vault_store or AionLearningVaultStore(workspace_id=workspace_id)
    if not store.enabled:
        raise RuntimeError("harmonic_memory_guardian_store_not_configured")

    reflection_value = (
        reflection
        if isinstance(reflection, Mapping)
        else store.get_state(REFLECTION_ENTITY_ID, {})
    )
    if governance is None:
        policy = store.get_state(GOVERNANCE_ENTITY_ID, {})
        governance_values = [policy] if isinstance(policy, Mapping) and policy else []
    else:
        governance_values = [row for row in governance if isinstance(row, Mapping)]

    if not isinstance(reflection_value, Mapping) or not reflection_value or not governance_values:
        return None

    avg_stability = _number(reflection_value.get("avg_delta_stability", reflection_value.get("avg_Δ_stability")))
    avg_drift = _number(reflection_value.get("avg_delta_drift", reflection_value.get("avg_Δ_drift")))
    risks = [_number(row.get("avg_risk")) for row in governance_values]
    gains = [_number(row.get("gain_mod"), 1.0) for row in governance_values]
    avg_risk = sum(risks) / len(risks)
    avg_gain = sum(gains) / len(gains)

    harmony_memory = {
        "schema": HARMONIC_MEMORY_SCHEMA,
        "timestamp": _number(now()),
        "avg_reflective_stability": round(avg_stability, 3),
        "avg_reflective_drift": round(avg_drift, 3),
        "avg_governance_risk": round(avg_risk, 3),
        "avg_gain_mod": round(avg_gain, 3),
        "harmony_integral": round(1 - (abs(avg_drift) + avg_risk) / 2, 3)
    }

    store.put_state(HARMONIC_MEMORY_ENTITY_ID, harmony_memory)
    if runtime_handoff is not None:
        runtime_handoff(dict(harmony_memory))
    return harmony_memory

def main() -> None:
    fused = fuse_memories()
    if fused:
        print(
            "Harmonic memory fused "
            f"harmony={fused['harmony_integral']:.3f}"
        )

if __name__ == "__main__":
    main()
