# ──────────────────────────────────────────────
#  Tessaris * HST Field Analyzer (P5+ Diagnostic Layer)
#  Monitors coherence, ψ-κ-T evolution, and semantic drift trends.
# ──────────────────────────────────────────────

import os
import json
import time
import numpy as np
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)


class HSTFieldAnalyzer:
    """
    Diagnostic analyzer for HST-generated ψ-κ-T tensor fields.
    Tracks coherence, entropy flow, and semantic drift trends
    across time for stability visualization and research analysis.
    """

    def __init__(self, session_id: str, output_dir: str = "data/telemetry"):
        self.session_id = session_id
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)

        self.records: List[Dict[str, Any]] = []
        self.last_record_time = 0.0
        self.sample_interval = 0.5  # seconds

        self.coherence_trend: List[float] = []
        self.entropy_trend: List[float] = []
        self.psi_kappa_T_trend: List[Dict[str, float]] = []

        logger.info(f"[HSTFieldAnalyzer] Initialized for session {self.session_id}")

    # ──────────────────────────────────────────────
    #  Data Collection Entry
    # ──────────────────────────────────────────────
    def sample_field_state(self, hst_state: Dict[str, Any]):
        """
        Capture one snapshot from the HST generator.
        """
        now = time.time()
        if (now - self.last_record_time) < self.sample_interval:
            return
        self.last_record_time = now

        nodes = hst_state.get("nodes", [])
        tensor = hst_state.get("field_tensor", {})

        avg_coherence = np.mean([n.get("coherence", 0.0) for n in nodes]) if nodes else 0.0
        avg_entropy = np.mean([n.get("entropy", 0.0) for n in nodes]) if nodes else 0.0
        avg_drift = np.mean([n.get("drift", 0.0) for n in nodes]) if nodes else 0.0

        psi = tensor.get("psi", 0.0)
        kappa = tensor.get("kappa", 0.0)
        T = tensor.get("T", 0.0)

        record = {
            "timestamp": datetime.utcnow().isoformat(),
            "avg_coherence": float(avg_coherence),
            "avg_entropy": float(avg_entropy),
            "avg_drift": float(avg_drift),
            "psi": float(psi),
            "kappa": float(kappa),
            "T": float(T),
        }

        self.records.append(record)
        self.coherence_trend.append(avg_coherence)
        self.entropy_trend.append(avg_entropy)
        self.psi_kappa_T_trend.append({"psi": psi, "kappa": kappa, "T": T})

        logger.debug(
            f"[HSTFieldAnalyzer] Sampled field ψ={psi:.3f}, κ={kappa:.3f}, "
            f"T={T:.3f}, coherence={avg_coherence:.3f}"
        )

    # ──────────────────────────────────────────────
    #  Metrics Computation
    # ──────────────────────────────────────────────
    def compute_stability_index(self) -> float:
        """
        Computes a stability index (0-1) based on coherence/entropy ratio.
        """
        if not self.coherence_trend:
            return 0.0
        coherence = np.mean(self.coherence_trend[-50:])
        entropy = np.mean(self.entropy_trend[-50:]) if self.entropy_trend else 1e-6
        stability = np.clip(coherence / (entropy + 1e-6), 0.0, 1.0)
        return float(stability)

    def compute_drift_vector(self) -> float:
        """
        Estimates semantic drift as a moving standard deviation of coherence.
        """
        if len(self.coherence_trend) < 2:
            return 0.0
        return float(np.std(self.coherence_trend[-50:]))

    def summarize_recent_state(self) -> Dict[str, Any]:
        """
        Return the latest holographic stability snapshot.
        """
        if not self.records:
            return {}
        latest = self.records[-1]
        summary = {
            "session_id": self.session_id,
            "timestamp": latest["timestamp"],
            "stability_index": self.compute_stability_index(),
            "drift_vector": self.compute_drift_vector(),
            "last_psi_kappa_T": self.psi_kappa_T_trend[-1] if self.psi_kappa_T_trend else {},
        }
        return summary

    # ──────────────────────────────────────────────
    #  Persistence & Reporting
    # ──────────────────────────────────────────────
    def export_analysis(self, path: Optional[str] = None):
        """
        Export all analysis samples to JSON for offline study.
        """
        path = path or os.path.join(
            self.output_dir, f"hst_analysis_{self.session_id}.json"
        )
        report = {
            "session_id": self.session_id,
            "generated_at": datetime.utcnow().isoformat(),
            "records": self.records,
            "summary": self.summarize_recent_state(),
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2)
        logger.info(f"[HSTFieldAnalyzer] Exported analysis -> {path}")

    # ──────────────────────────────────────────────
    #  Summary Output for Field Feedback
    # ──────────────────────────────────────────────
    def summarize_field(self) -> dict:
        """
        Return a summary snapshot of the current HST field state.
        Includes stability index, drift vector, and last ψ-κ-T signature.
        """
        summary = {
            "session_id": self.session_id,
            "timestamp": datetime.utcnow().isoformat(),
            "stability_index": getattr(self, "stability_index", 1.0),
            "drift_vector": getattr(self, "drift_vector", 0.0),
            "last_psi_kappa_T": getattr(self, "last_signature", {}),
        }
        return summary

    def clear(self):
        """Reset analyzer state."""
        self.records.clear()
        self.coherence_trend.clear()
        self.entropy_trend.clear()
        self.psi_kappa_T_trend.clear()

# ──────────────────────────────────────────────
# Example Usage
# ──────────────────────────────────────────────
"""
from backend.modules.holograms.hst_generator import HSTGenerator
from backend.modules.holograms.hst_field_analyzer import HSTFieldAnalyzer

hst = HSTGenerator()
analyzer = HSTFieldAnalyzer(hst.session_id)

# Inject beams and analyze over time
for i in range(10):
    hst.inject_lightwave_beam({
        "beam_id": f"beam_{i}",
        "entropy": np.random.uniform(0, 0.5),
        "coherence": np.random.uniform(0.7, 1.0),
        "goal_match": np.random.uniform(0.5, 1.0),
        "drift": np.random.uniform(0, 0.1),
        "symbol": "🌊"
    })
    hst.broadcast_state(force=True)
    analyzer.sample_field_state({
        "nodes": list(hst.nodes.values()),
        "field_tensor": hst.field_tensor
    })
    time.sleep(0.3)

print(analyzer.summarize_recent_state())
analyzer.export_analysis()
"""