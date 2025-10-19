# ===============================
# 📁 backend/quant/qlearn/qlearn_engine.py
# ===============================
"""
🧠  QLearnEngine — Adaptive Resonance Learning Core
----------------------------------------------------
Implements reinforcement-style adaptation for Q-Series metrics.
Learns from QCoreMetrics history and adjusts resonance weighting
(Φ, ψ, κ, coherence, SQI) to improve stability and harmony.

Intended for continuous feedback into QQC runtime or AION cognitive
feedback loops.
"""

from __future__ import annotations
from typing import Dict, Any, List, Optional
import json
import math
import os
from datetime import datetime


class QLearnEngine:
    """
    🌱 Adaptive learner operating on aggregated QCoreMetrics.
    Stores per-run feedback, computes moving targets, and outputs
    updated learning weights for resonance modulation.
    """

    def __init__(self, base_dir: str = "backend/qlearn/state"):
        self.base_dir = base_dir
        os.makedirs(base_dir, exist_ok=True)
        self.state_path = os.path.join(base_dir, "qlearn_state.json")
        self.learning_rate = 0.15
        self.decay = 0.98
        self.state: Dict[str, float] = self._load_state()

    # ------------------------------------------------------------------
    def _load_state(self) -> Dict[str, float]:
        if os.path.exists(self.state_path):
            try:
                with open(self.state_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {
            "w_phi": 1.0,
            "w_psi": 1.0,
            "w_coherence": 1.0,
            "w_sqi": 1.0,
            "baseline_coherence": 1.0,
        }

    # ------------------------------------------------------------------
    def _save_state(self) -> None:
        try:
            with open(self.state_path, "w", encoding="utf-8") as f:
                json.dump(self.state, f, indent=2)
        except Exception:
            pass

    # ------------------------------------------------------------------
    def learn_from_summary(self, summary: Dict[str, Any]) -> Dict[str, float]:
        """
        Update weights from a single QCoreMetrics summary.
        """
        if not summary:
            return self.state

        Φ = summary.get("Φ_mean", 1.0)
        ψ = summary.get("ψ_mean", 1.0)
        coh = summary.get("coherence_mean", 1.0)
        sqi = summary.get("sqi_mean", 1.0)
        harmony = summary.get("harmony_mean", 1.0)

        target = (Φ * ψ * coh * harmony)
        baseline = self.state.get("baseline_coherence", 1.0)
        error = target - baseline

        # Simple gradient-like update
        self.state["w_phi"] += self.learning_rate * error * Φ
        self.state["w_psi"] += self.learning_rate * error * ψ
        self.state["w_coherence"] += self.learning_rate * error * coh
        self.state["w_sqi"] += self.learning_rate * error * sqi

        # Decay + normalize
        for k in ["w_phi", "w_psi", "w_coherence", "w_sqi"]:
            self.state[k] = max(0.1, min(5.0, self.state[k] * self.decay))

        # Adjust baseline
        self.state["baseline_coherence"] = 0.9 * baseline + 0.1 * target
        self.state["last_update"] = datetime.utcnow().isoformat() + "Z"

        self._save_state()
        return self.state

    # ------------------------------------------------------------------
    def batch_learn(self, history: List[Dict[str, Any]]) -> Dict[str, float]:
        """
        Train on a batch of QCoreMetrics summaries.
        """
        for s in history:
            self.learn_from_summary(s)
        return self.state

    # ------------------------------------------------------------------
    def predict_resonance_adjustment(self, summary: Dict[str, Any]) -> float:
        """
        Estimate expected resonance improvement for the next run.
        """
        Φ = summary.get("Φ_mean", 1.0)
        ψ = summary.get("ψ_mean", 1.0)
        coh = summary.get("coherence_mean", 1.0)
        wΦ, wψ, wC = self.state["w_phi"], self.state["w_psi"], self.state["w_coherence"]
        adj = (Φ * wΦ + ψ * wψ + coh * wC) / 3.0
        return float(round(adj, 6))

    # ------------------------------------------------------------------
    def export_state_packet(self) -> Dict[str, Any]:
        """
        Package current learning state for telemetry or checkpoints.
        """
        return {
            "packet_id": f"qlearn_state_{datetime.utcnow().strftime('%H%M%S')}",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "weights": self.state,
        }

    # ------------------------------------------------------------------
    def __repr__(self) -> str:
        w = self.state
        return (
            f"QLearnEngine(Φ={w.get('w_phi', 0):.3f}, ψ={w.get('w_psi', 0):.3f}, "
            f"C={w.get('w_coherence', 0):.3f}, SQI={w.get('w_sqi', 0):.3f})"
        )