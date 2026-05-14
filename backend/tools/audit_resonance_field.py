#!/usr/bin/env python3
"""
🧠 AION Resonance Field Audit - Phase 57b Cognitive Self-Tuning
───────────────────────────────────────────────────────────────
Scans all resonance heartbeat logs, computes coherence / entropy / SQI stability,
and issues auto-tuning advisories for underperforming modules.

Output -> data/analysis/resonance_audit_report.json
"""

import json
import math
from pathlib import Path
from statistics import mean, fmean, pstdev

HEARTBEAT_DIR = Path("data/aion_field")
DRIFT_LOG = Path("data/aion_field/resonant_drift_log.jsonl")
OUT = Path("data/analysis/resonance_audit_report.json")

def safe_mean(vals):
    vals = [v for v in vals if isinstance(v, (int, float))]
    return round(fmean(vals), 3) if vals else None

def load_heartbeat(fpath):
    try:
        return json.loads(Path(fpath).read_text())
    except Exception:
        return {}

def audit_engine(fpath):
    js = load_heartbeat(fpath)
    name = Path(fpath).stem.replace("_heartbeat_live", "")
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

def main():
    hb_files = list(HEARTBEAT_DIR.glob("*heartbeat_live.json"))
    if not hb_files:
        print("No heartbeat logs found.")
        return

    audits = [audit_engine(f) for f in hb_files]
    drift_rows = []
    if DRIFT_LOG.exists():
        with open(DRIFT_LOG, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    drift_rows.append(json.loads(line))
                except Exception:
                    pass

    global_stats = {
        "engines_audited": len(audits),
        "avg_stability": safe_mean([a["stability"] for a in audits if a["stability"] is not None]),
        "avg_drift": safe_mean([a["ΔΦ"] for a in audits]),
        "total_drift_corrections": len(drift_rows),
    }

    report = {"summary": global_stats, "engines": audits}

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, indent=2))
    print(f"📘 Wrote resonance audit -> {OUT}")
    print(json.dumps(report, indent=2))

if __name__ == "__main__":
    main()