#!/usr/bin/env python3
import json
from pathlib import Path
from statistics import mean
"""[LEGACY] Simulation-only dashboard aggregator (superseded by update_dashboard_summary.py)."""
LOG = Path("data/analysis/aion_live_dashboard.jsonl")
OUT = Path("data/analysis/aion_live_dashboard.json")

def main():
    if not LOG.exists():
        print("No dashboard log yet.")
        return
    rows = []
    with open(LOG, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line: continue
            try:
                rows.append(json.loads(line))
            except Exception:
                pass

    # basic aggregates
    sqi_vals  = [r.get("SQI") for r in rows if isinstance(r.get("SQI"), (int, float))]
    rho_vals  = [r.get("Φ_coherence") for r in rows if isinstance(r.get("Φ_coherence"), (int, float))]
    ent_vals  = [r.get("Φ_entropy")   for r in rows if isinstance(r.get("Φ_entropy"), (int, float))]
    dphi_vals = [r.get("ΔΦ")          for r in rows if isinstance(r.get("ΔΦ"), (int, float))]

    summary = {
        "events": len(rows),
        "avg_SQI": round(mean(sqi_vals), 3) if sqi_vals else None,
        "avg_ρ":   round(mean(rho_vals), 3) if rho_vals else None,
        "avg_Ī":   round(mean(ent_vals), 3) if ent_vals else None,
        "avg_ΔΦ":  round(mean(dphi_vals), 3) if dphi_vals else None,
        "last": rows[-1] if rows else None,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(summary, indent=2))
    print(f"Wrote dashboard summary -> {OUT}")

if __name__ == "__main__":
    main()