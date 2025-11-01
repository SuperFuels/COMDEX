#!/usr/bin/env python3
# ================================================================
# 🌐 Genomic Dashboard & Evolutionary Telemetry - Phase R15
# ================================================================
# Aggregates metrics from all symbolic-biology layers (DNA, RNA,
# Ribosome, Replay, Stability Monitor) into a unified telemetry view.
# ================================================================

import json, time, logging, statistics
from pathlib import Path
from backend.modules.aion_resonance.resonance_heartbeat import ResonanceHeartbeat

logger = logging.getLogger(__name__)

# input sources
SOURCES = {
    "dna": Path("data/exports/dna_replay_containers.json"),
    "rna": Path("data/analysis/symbolic_rna_traces.json"),
    "ribosome": Path("data/analysis/ribosome_synthesis_traces.json"),
    "stability": Path("data/analysis/genomic_stability_report.json"),
}

OUT = Path("data/analysis/genomic_dashboard.json")
Theta = ResonanceHeartbeat(namespace="genomic_dashboard")


def _extract_values(data, key, default=0.5):
    vals = [d.get(key, default) for d in data if isinstance(d, dict)]
    return vals if vals else [default]


def aggregate_genomic_metrics():
    all_entries = []
    stability_data = {}

    for name, path in SOURCES.items():
        if not path.exists():
            continue
        try:
            js = json.loads(path.read_text())
            if isinstance(js, dict) and name == "stability":
                stability_data = js
            elif isinstance(js, list):
                all_entries.extend(js)
        except Exception as e:
            logger.warning(f"[R15] Failed to parse {name}: {e}")

    if not all_entries and not stability_data:
        logger.info("[R15] No genomic data available.")
        return None

    entropies = _extract_values(all_entries, "entropy")
    coherences = _extract_values(all_entries, "coherence")
    sqis = _extract_values(all_entries, "SQI")

    avg_entropy = round(statistics.fmean(entropies), 3)
    avg_coherence = round(statistics.fmean(coherences), 3)
    avg_sqi = round(statistics.fmean(sqis), 3)
    drift = round(abs(avg_coherence - (1 - avg_entropy)), 3)
    harmony = round(max(0.0, min(1.0, 1 - drift)), 3)

    unethical = stability_data.get("unethical_entries", 0)
    entries_scanned = stability_data.get("entries_scanned", len(all_entries))
    ethics_ratio = round(1 - (unethical / max(1, entries_scanned)), 3)

    dashboard = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "entries_scanned": entries_scanned,
        "avg_entropy": avg_entropy,
        "avg_coherence": avg_coherence,
        "avg_SQI": avg_sqi,
        "drift": drift,
        "harmony_score": harmony,
        "ethics_ratio": ethics_ratio,
        "unethical": unethical,
    }

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(dashboard, indent=2))

    # send Θ telemetry pulse
    Theta.push_sample(rho=avg_coherence, entropy=avg_entropy, sqi=avg_sqi, delta=drift)
    Theta.event("genomic_dashboard_update", harmony=harmony, ethics_ratio=ethics_ratio)

    logger.info(f"[R15] Updated Genomic Dashboard -> {OUT}")
    print(json.dumps(dashboard, indent=2))
    return dashboard


if __name__ == "__main__":
    aggregate_genomic_metrics()