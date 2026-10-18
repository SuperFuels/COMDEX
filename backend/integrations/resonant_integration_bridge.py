#!/usr/bin/env python3
"""Guardian-backed resonance integration state.

The original Phase 63 bridge wrote customer-derived state beneath the
application tree and constructed a background heartbeat at import time. This
module is deliberately inert until ``fuse_resonant_state`` is called. Durable
inputs and output live in the active business Guardian; an authorised runtime
handoff can be supplied explicitly by the caller.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
import math
import time
from typing import Any

from backend.modules.aion_learning.vault_store import AionLearningVaultStore


STATE_ENTITY_ID = "resonant_integration_state"
HARMONIC_MEMORY_ENTITY_ID = "harmonic_memory"
RESONANCE_AUDIT_ENTITY_ID = "resonance_audit_report"
STATE_SCHEMA = "tessaris.resonant-integration-state.v1"


def _finite_number(value: Any, default: float) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError):
        return default
    return result if math.isfinite(result) else default


def _stored_mapping(
    store: AionLearningVaultStore,
    entity_id: str,
) -> Mapping[str, Any]:
    value = store.get_state(entity_id, {})
    return value if isinstance(value, Mapping) else {}


def fuse_resonant_state(
    *,
    vault_store: AionLearningVaultStore | None = None,
    workspace_id: str | None = None,
    harmonic_memory: Mapping[str, Any] | None = None,
    resonance_audit: Mapping[str, Any] | None = None,
    theta_frequency: float = 1.0,
    runtime_handoff: Callable[[Mapping[str, Any]], None] | None = None,
    now: Callable[[], float] = time.time,
) -> dict[str, Any]:
    """Fuse current resonance values and retain them in Guardian.

    Inputs may be supplied by an authorised in-memory pipeline. When omitted,
    the corresponding Guardian learning records are used. There is
    intentionally no implicit fallback to the legacy ``data/`` files.
    """

    store = vault_store or AionLearningVaultStore(workspace_id=workspace_id)
    if not store.enabled:
        raise RuntimeError("resonant_bridge_guardian_store_not_configured")

    hm = (
        harmonic_memory
        if isinstance(harmonic_memory, Mapping)
        else _stored_mapping(store, HARMONIC_MEMORY_ENTITY_ID)
    )
    audit = (
        resonance_audit
        if isinstance(resonance_audit, Mapping)
        else _stored_mapping(store, RESONANCE_AUDIT_ENTITY_ID)
    )

    stability = _finite_number(hm.get("avg_reflective_stability"), 0.5)
    drift = _finite_number(hm.get("avg_reflective_drift"), 0.0)
    risk = _finite_number(hm.get("avg_governance_risk"), 0.0)
    harmony = _finite_number(hm.get("harmony_integral"), 0.5)
    frequency = _finite_number(theta_frequency, 1.0)

    entropy_bias = 1.0 - harmony
    coherence_boost = stability * (1.0 - risk)
    state: dict[str, Any] = {
        "schema": STATE_SCHEMA,
        "timestamp": _finite_number(now(), 0.0),
        "coherence_boost": coherence_boost,
        "entropy_bias": entropy_bias,
        "harmony_integral": harmony,
        "theta_frequency": frequency,
        "reflective_drift": drift,
        "audit_present": bool(audit),
    }

    store.put_state(STATE_ENTITY_ID, state)
    if runtime_handoff is not None:
        runtime_handoff(dict(state))
    return state


def main() -> None:
    # This command is expected to run only inside a configured business Node.
    # It fails closed rather than recreating repository-relative state.
    state = fuse_resonant_state()
    print(
        "Resonant Bridge update "
        f"H={state['harmony_integral']:.3f}, "
        f"rho={state['coherence_boost']:.3f}"
    )


if __name__ == "__main__":
    main()
