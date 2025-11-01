#!/usr/bin/env python3
# ================================================================
# 🧬 Evolutionary Memory Replay - Phase R16
# ================================================================
# Replays historical symbolic generations (DNA->RNA->Ribosome)
# to forecast drift, coherence, and ethics stability over time.
# ================================================================

import json, time, statistics, logging
from pathlib import Path
from backend.modules.aion_resonance.resonance_heartbeat import ResonanceHeartbeat
from backend.modules.soul.soul_laws import validate_ethics

logger = logging.getLogger(__name__)
Theta = ResonanceHeartbeat(namespace="evolutionary_replay")

DATASETS = [
    Path("data/exports/dna_replay_containers.json"),
    Path("data/analysis/symbolic_rna_traces.json"),
    Path("data/analysis/ribosome_synthesis_traces.json"),
]

OUT = Path("data/analysis/evolutionary_memory_forecast.json")


class EvolutionaryMemoryReplay:
    def __init__(self, horizon:int = 50):
        self.horizon = horizon

    def _load_entries(self):
        entries = []
        for path in DATASETS:
            if path.exists():
                try:
                    js = json.loads(path.read_text())
                    if isinstance(js, list):
                        entries.extend(js)
                except Exception as e:
                    logger.warning(f"[R16] Failed to read {path}: {e}")
        return entries[-self.horizon:]

    def replay(self):
        """Replay recent symbolic generations and compute forecast metrics."""
        data = self._load_entries()
        if not data:
            logger.info("[R16] No historical data to replay.")
            return None

        entropies = [d.get("entropy", 0.5) for d in data]
        coherences = [d.get("coherence", 0.5) for d in data]
        sqis = [d.get("SQI", 0.5) for d in data]

        avg_entropy = round(statistics.fmean(entropies), 3)
        avg_coherence = round(statistics.fmean(coherences), 3)
        avg_sqi = round(statistics.fmean(sqis), 3)
        drift = round(abs(avg_coherence - (1 - avg_entropy)), 3)
        harmony = round(1 - drift, 3)

        unethical = 0
        for d in data:
            logic = d.get("logic") or d.get("content") or ""
            if not validate_ethics(logic):
                unethical += 1

        ethics_ratio = round(1 - (unethical / max(1, len(data))), 3)

        # Forecast next-phase drift via trend projection
        drift_trend = statistics.fmean(
            [abs(entropies[i] - coherences[i]) for i in range(len(entropies))]
        )
        forecast_drift = round(drift + (drift_trend - drift) * 0.5, 3)
        forecast_harmony = round(max(0.0, 1 - forecast_drift), 3)

        report = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "entries_replayed": len(data),
            "avg_entropy": avg_entropy,
            "avg_coherence": avg_coherence,
            "avg_SQI": avg_sqi,
            "current_drift": drift,
            "forecast_drift": forecast_drift,
            "current_harmony": harmony,
            "forecast_harmony": forecast_harmony,
            "ethics_ratio": ethics_ratio,
            "unethical_count": unethical,
        }

        OUT.parent.mkdir(parents=True, exist_ok=True)
        OUT.write_text(json.dumps(report, indent=2))
        Theta.event("evolutionary_replay",
                    drift=drift,
                    harmony=harmony,
                    forecast_drift=forecast_drift,
                    forecast_harmony=forecast_harmony,
                    ethics_ratio=ethics_ratio)

        logger.info(f"[R16] Evolutionary forecast generated -> {OUT}")
        print(json.dumps(report, indent=2))
        return report


if __name__ == "__main__":
    emr = EvolutionaryMemoryReplay()
    emr.replay()