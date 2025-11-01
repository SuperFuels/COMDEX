#!/usr/bin/env python3
# ================================================================
# 🧩 Genomic Stability Monitor - Phase R14
# ================================================================
# Watches symbolic DNA (.dc) containers, RNA scrolls, and synthesis traces
# for entropy drift, SQI decay, or ethical violations.
# Emits resonance alerts via Θ-phase pulses.
# ================================================================

import json, time, logging, statistics
from pathlib import Path
from backend.modules.soul.soul_laws import validate_ethics
from backend.modules.aion_resonance.resonance_heartbeat import ResonanceHeartbeat

logger = logging.getLogger(__name__)
Theta = ResonanceHeartbeat(namespace="genomic_monitor")

DATA_PATHS = [
    Path("data/exports/dna_replay_containers.json"),
    Path("data/analysis/symbolic_rna_traces.json"),
    Path("data/analysis/ribosome_synthesis_traces.json"),
]

REPORT_PATH = Path("data/analysis/genomic_stability_report.json")


class GenomicStabilityMonitor:
    def __init__(self, drift_threshold: float = 0.15, ethics_check: bool = True):
        self.drift_threshold = drift_threshold
        self.ethics_check = ethics_check
        self.report = {}

    # ------------------------------------------------------------
    def scan(self):
        """Perform a full-system genomic stability scan."""
        entries = []
        for p in DATA_PATHS:
            if not p.exists():
                continue
            try:
                data = json.loads(p.read_text())
                if isinstance(data, list):
                    entries.extend(data)
            except Exception as e:
                logger.warning(f"[GSM] Failed to read {p}: {e}")

        if not entries:
            logger.info("[GSM] No genomic data to scan.")
            return None

        entropies = [e.get("entropy", 0.5) for e in entries]
        coherences = [e.get("coherence", 0.5) for e in entries]
        sqis = [e.get("SQI", 0.5) for e in entries if "SQI" in e]

        avg_entropy = round(statistics.fmean(entropies), 3)
        avg_coherence = round(statistics.fmean(coherences), 3)
        avg_sqi = round(statistics.fmean(sqis), 3) if sqis else 0.5
        drift = round(abs(avg_coherence - (1 - avg_entropy)), 3)

        unethical_count = 0
        if self.ethics_check:
            for e in entries:
                logic = e.get("logic") or e.get("content") or ""
                if not validate_ethics(logic):
                    unethical_count += 1

        stable = drift <= self.drift_threshold and unethical_count == 0
        harmony = round(max(0.0, min(1.0, 1 - drift)), 3)

        Theta.push_sample(rho=avg_coherence, entropy=avg_entropy, sqi=avg_sqi, delta=drift)
        Theta.event(
            "genomic_scan",
            avg_entropy=avg_entropy,
            avg_coherence=avg_coherence,
            avg_sqi=avg_sqi,
            drift=drift,
            unethical=unethical_count,
            harmony=harmony,
            stable=stable,
        )

        self.report = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "entries_scanned": len(entries),
            "avg_entropy": avg_entropy,
            "avg_coherence": avg_coherence,
            "avg_SQI": avg_sqi,
            "drift": drift,
            "unethical_entries": unethical_count,
            "harmony_score": harmony,
            "stable": stable,
        }

        REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
        REPORT_PATH.write_text(json.dumps(self.report, indent=2))
        logger.info(f"[GSM] Wrote genomic stability report -> {REPORT_PATH}")
        return self.report

    # ------------------------------------------------------------
    def monitor_loop(self, interval: float = 30.0):
        """Continuous stability watcher."""
        while True:
            self.scan()
            time.sleep(interval)


if __name__ == "__main__":
    gsm = GenomicStabilityMonitor()
    gsm.scan()