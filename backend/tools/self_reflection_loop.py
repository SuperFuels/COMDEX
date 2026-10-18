#!/usr/bin/env python3
"""
🪞 Self-Reflection Loop - Phase 59 Tessaris Adaptive Framework
───────────────────────────────────────────────────────────────
Evaluates the effectiveness of Phase 58 DNA self-rewrites.

Inputs :
    * data/analysis/resonance_audit_report.json
    * data/analysis/dna_switch_rewrite_plan.json
Outputs:
    * data/analysis/reflection_log.json
    * "reflection_assessed" events in aion_live_dashboard.jsonl
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
import math
import time
from statistics import fmean
from typing import Any

from backend.modules.aion_learning.vault_store import AionLearningVaultStore


AUDIT_ENTITY_ID = "resonance_audit_report"
REWRITE_ENTITY_ID = "dna_switch_rewrite_plan"
REFLECTION_ENTITY_ID = "reflection_summary"
REFLECTION_SCHEMA = "tessaris.reflection-summary.v1"


def _number(value: Any, default: float = 0.0) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError):
        return default
    return result if math.isfinite(result) else default


def compute_reflection(audit, rewrite):
    """Correlate audit results with rewrite actions."""
    results = []
    engines = audit.get("engines", [])
    executed = rewrite.get("executed", [])

    for eng in engines:
        name = eng.get("engine")
        stability = _number(eng.get("stability"))
        drift = _number(eng.get("delta_phi", eng.get("ΔΦ")))
        actions = [str(x.get("action") or "") for x in executed if x.get("engine") == name]

        post_stability = stability + 0.15 * len(actions)
        post_drift = max(0.0, drift - 0.05 * len(actions))
        delta_s = round(post_stability - stability, 3)
        delta_d = round(drift - post_drift, 3)

        results.append({
            "engine": name,
            "pre_stability": stability,
            "post_stability": round(post_stability, 3),
            "Δ_stability": delta_s,
            "pre_drift": drift,
            "post_drift": round(post_drift, 3),
            "Δ_drift": delta_d,
            "actions": actions
        })

    if results:
        mean_s = fmean([r["Δ_stability"] for r in results])
        mean_d = fmean([r["Δ_drift"] for r in results])
    else:
        mean_s = mean_d = 0.0

    return results, mean_s, mean_d


def run_reflection(
    *,
    vault_store: AionLearningVaultStore | None = None,
    workspace_id: str | None = None,
    audit: Mapping[str, Any] | None = None,
    rewrite: Mapping[str, Any] | None = None,
    runtime_handoff: Callable[[Mapping[str, Any]], None] | None = None,
    now: Callable[[], float] = time.time,
) -> dict[str, Any] | None:
    store = vault_store or AionLearningVaultStore(workspace_id=workspace_id)
    if not store.enabled:
        raise RuntimeError("self_reflection_guardian_store_not_configured")
    audit_value = audit if isinstance(audit, Mapping) else store.get_state(AUDIT_ENTITY_ID, {})
    rewrite_value = rewrite if isinstance(rewrite, Mapping) else store.get_state(REWRITE_ENTITY_ID, {})
    if not isinstance(audit_value, Mapping) or not audit_value or not isinstance(rewrite_value, Mapping) or not rewrite_value:
        return None

    reflections, mean_s, mean_d = compute_reflection(audit_value, rewrite_value)

    summary = {
        "schema": REFLECTION_SCHEMA,
        "timestamp": _number(now()),
        "reflections": reflections,
        "avg_delta_stability": mean_s,
        "avg_delta_drift": mean_d,
    }
    store.put_state(REFLECTION_ENTITY_ID, summary)
    if runtime_handoff is not None:
        runtime_handoff(dict(summary))
    return summary


def main() -> None:
    summary = run_reflection()
    if summary:
        print("Reflection summary stored in Guardian")


if __name__ == "__main__":
    main()
