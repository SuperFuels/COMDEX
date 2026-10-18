#!/usr/bin/env python3
"""
🧬 DNA Switch Self-Rewrite - Phase 58 Adaptive Integration (v2)
───────────────────────────────────────────────────────────────
Integrates with dna_writer to auto-generate symbolic rewrite proposals
for unstable or drifted modules detected by the resonance audit.

Input : data/analysis/resonance_audit_report.json
Output: data/analysis/dna_switch_rewrite_plan.json
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
import time
from typing import Any

from backend.modules.aion_learning.vault_store import AionLearningVaultStore


AUDIT_ENTITY_ID = "resonance_audit_report"
REWRITE_ENTITY_ID = "dna_switch_rewrite_plan"
REWRITE_SCHEMA = "tessaris.dna-switch-rewrite-plan.v1"


def plan_rewrites(audit):
    engines = audit.get("engines", [])
    plan = []

    for eng in engines:
        name = eng.get("engine")
        flags = eng.get("flags", [])
        stability = eng.get("stability")
        delta = eng.get("ΔΦ", 0.0)
        advisory = eng.get("advisory")

        if not flags:
            continue

        action = {"engine": name, "actions": [], "reason": flags}
        if stability is not None and stability < 0.25:
            action["actions"].append("recalibrate_resonance")
        if abs(delta) > 0.1:
            action["actions"].append("synchronize_phase")
        action["advisory"] = advisory
        plan.append(action)

    return plan


def execute_rewrites(
    plan: Sequence[Mapping[str, Any]],
    *,
    action_handler: Callable[[Mapping[str, Any]], None] | None = None,
    proposal_handler: Callable[[Mapping[str, Any]], None] | None = None,
    now: Callable[[], float] = time.time,
):
    executed = []
    for item in plan:
        name = item["engine"]
        actions = item["actions"]

        for act in actions:
            action = {
                "event": "dna_rewrite_requested",
                "timestamp": float(now()),
                "engine": name,
                "action": act,
            }
            if action_handler is not None:
                action_handler(dict(action))
            if proposal_handler is not None:
                proposal_handler(
                    {
                        "engine": name,
                        "action": act,
                        "reason": list(item.get("reason") or []),
                        "source": "Phase58_AuditRepair",
                    }
                )
            executed.append(action)

    return executed


def run_rewrite_planning(
    *,
    vault_store: AionLearningVaultStore | None = None,
    workspace_id: str | None = None,
    audit: Mapping[str, Any] | None = None,
    action_handler: Callable[[Mapping[str, Any]], None] | None = None,
    proposal_handler: Callable[[Mapping[str, Any]], None] | None = None,
    now: Callable[[], float] = time.time,
) -> dict[str, Any] | None:
    store = vault_store or AionLearningVaultStore(workspace_id=workspace_id)
    if not store.enabled:
        raise RuntimeError("dna_rewrite_guardian_store_not_configured")
    audit_value = audit if isinstance(audit, Mapping) else store.get_state(AUDIT_ENTITY_ID, {})
    if not isinstance(audit_value, Mapping) or not audit_value:
        return None

    plan = plan_rewrites(audit_value)
    executed = execute_rewrites(
        plan,
        action_handler=action_handler,
        proposal_handler=proposal_handler,
        now=now,
    )

    report = {"schema": REWRITE_SCHEMA, "plan": plan, "executed": executed}
    store.put_state(REWRITE_ENTITY_ID, report)
    return report


def main() -> None:
    report = run_rewrite_planning()
    if report:
        print(f"DNA rewrite requests stored in Guardian ({len(report['executed'])})")


if __name__ == "__main__":
    main()
