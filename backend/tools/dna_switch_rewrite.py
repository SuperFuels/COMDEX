#!/usr/bin/env python3
"""
🧬 DNA Switch Self-Rewrite — Phase 58 Adaptive Integration (v2)
───────────────────────────────────────────────────────────────
Integrates with dna_writer to auto-generate symbolic rewrite proposals
for unstable or drifted modules detected by the resonance audit.

Input : data/analysis/resonance_audit_report.json
Output: data/analysis/dna_switch_rewrite_plan.json
"""

import json
import time
from pathlib import Path
from backend.modules.dna_chain.switchboard import DNA_SWITCH
from backend.modules.aion_resonance.resonance_heartbeat import ResonanceHeartbeat
from backend.modules.dna_chain import dna_writer

AUDIT_PATH = Path("data/analysis/resonance_audit_report.json")
OUT = Path("data/analysis/dna_switch_rewrite_plan.json")

# Global Θ controller
Theta = ResonanceHeartbeat(namespace="global_theta")


def load_audit():
    try:
        return json.loads(AUDIT_PATH.read_text())
    except Exception as e:
        print(f"⚠️ Failed to load audit: {e}")
        return {}


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


def execute_rewrites(plan):
    executed = []
    for item in plan:
        name = item["engine"]
        actions = item["actions"]

        for act in actions:
            try:
                DNA_SWITCH.register(f"auto_rewrite::{name}::{act}")

                if act == "recalibrate_resonance":
                    Theta.sync_all(emit_pulse=True)
                    # Generate a DNA mutation proposal for the module
                    dna_writer.propose_dna_mutation(
                        reason=f"Auto-resonance recalibration for {name}",
                        source="Phase58_AuditRepair",
                        code_context="# 🔧 resonance placeholder",
                        new_logic="# Adjusted resonance stability constants"
                    )

                elif act == "synchronize_phase":
                    Theta.tick()
                    dna_writer.propose_dna_mutation(
                        reason=f"Phase alignment for {name}",
                        source="Phase58_AuditRepair",
                        code_context="# 🔄 phase placeholder",
                        new_logic="# Updated Θ-phase correction"
                    )

                # Log to dashboard
                log_payload = {
                    "namespace": "global_theta",
                    "event": "dna_rewrite_initiated",
                    "timestamp": time.time(),
                    "engine": name,
                    "action": act,
                }
                log_path = Path("data/analysis/aion_live_dashboard.jsonl")
                with open(log_path, "a") as f:
                    f.write(json.dumps(log_payload) + "\n")

                executed.append(log_payload)
                print(f"🧬 Executed {act} for {name}")

            except Exception as e:
                print(f"❌ Rewrite failed for {name}:{act} → {e}")

    return executed


def main():
    audit = load_audit()
    if not audit:
        print("No audit data available.")
        return

    plan = plan_rewrites(audit)
    executed = execute_rewrites(plan)

    report = {"plan": plan, "executed": executed}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, indent=2))

    print(f"📄 DNA Switch rewrite plan → {OUT}")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()