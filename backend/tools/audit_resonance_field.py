#!/usr/bin/env python3
"""
🧠 AION Resonance Field Audit - Phase 57b Cognitive Self-Tuning
───────────────────────────────────────────────────────────────
Scans all resonance heartbeat logs, computes coherence / entropy / SQI stability,
and issues auto-tuning advisories for underperforming modules.

Output -> data/analysis/resonance_audit_report.json
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from statistics import fmean
from typing import Any

from backend.modules.aion_learning.vault_store import AionLearningVaultStore


HEARTBEATS_ENTITY_ID = "resonance_heartbeat_snapshots"
DRIFT_ENTITY_ID = "resonance_drift_history"
AUDIT_ENTITY_ID = "resonance_audit_report"
AUDIT_SCHEMA = "tessaris.resonance-audit-report.v1"

def safe_mean(vals):
    vals = [v for v in vals if isinstance(v, (int, float))]
    return round(fmean(vals), 3) if vals else None

def audit_engine(js: Mapping[str, Any]):
    name = str(js.get("namespace") or js.get("engine") or "unknown")
    rho = js.get("Φ_coherence")
    ent = js.get("Φ_entropy")
    sqi = js.get("sqi")
    delta = js.get("resonance_delta", 0.0)

    stability = None
    if isinstance(rho, (int, float)) and isinstance(ent, (int, float)):
        stability = round(max(0.0, rho - ent), 3)

    flags = []
    if stability is not None and stability < 0.25:
        flags.append("⚠ Low stability (<0.25)")
    if abs(delta) > 0.1:
        flags.append(f"⚠ Excessive ΔΦ drift ({delta:.3f})")

    advisory = None
    if flags:
        advisory = "Recommend resonance recalibration via Θ.sync_all() and monitor_drift()"

    return {
        "engine": name,
        "Φ_coherence": rho,
        "Φ_entropy": ent,
        "SQI": sqi,
        "ΔΦ": delta,
        "stability": stability,
        "flags": flags,
        "advisory": advisory,
    }

def run_resonance_audit(
    *,
    vault_store: AionLearningVaultStore | None = None,
    workspace_id: str | None = None,
    heartbeats: Sequence[Mapping[str, Any]] | None = None,
    drift_rows: Sequence[Mapping[str, Any]] | None = None,
) -> dict[str, Any] | None:
    store = vault_store or AionLearningVaultStore(workspace_id=workspace_id)
    if not store.enabled:
        raise RuntimeError("resonance_audit_guardian_store_not_configured")
    if heartbeats is None:
        payload = store.get_state(HEARTBEATS_ENTITY_ID, {"snapshots": []})
        heartbeat_values = payload.get("snapshots", []) if isinstance(payload, Mapping) else []
    else:
        heartbeat_values = heartbeats
    if drift_rows is None:
        payload = store.get_state(DRIFT_ENTITY_ID, {"events": []})
        drift_values = payload.get("events", []) if isinstance(payload, Mapping) else []
    else:
        drift_values = drift_rows
    heartbeat_values = [row for row in heartbeat_values if isinstance(row, Mapping)]
    drift_values = [row for row in drift_values if isinstance(row, Mapping)]
    if not heartbeat_values:
        return None

    audits = [audit_engine(row) for row in heartbeat_values]

    global_stats = {
        "engines_audited": len(audits),
        "avg_stability": safe_mean([a["stability"] for a in audits if a["stability"] is not None]),
        "avg_drift": safe_mean([a["ΔΦ"] for a in audits]),
        "total_drift_corrections": len(drift_values),
    }

    report = {"schema": AUDIT_SCHEMA, "summary": global_stats, "engines": audits}
    store.put_state(AUDIT_ENTITY_ID, report)
    return report


def main() -> None:
    report = run_resonance_audit()
    if report:
        print(f"Resonance audit stored in Guardian ({len(report['engines'])})")

if __name__ == "__main__":
    main()
