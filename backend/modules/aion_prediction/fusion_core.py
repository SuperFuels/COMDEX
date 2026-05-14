#!/usr/bin/env python3
"""
AION Fusion Core - Predictive Bias + Resonant Reinforcement Integration
────────────────────────────────────────────────────────────────────────
Bridges PAL (Perception-Action Loop), PBL (Predictive Bias Layer),
and Temporal Coherence Memory (TCM) with Resonance Feedback (Phase 32).

Handles:
    * Δt temporal vector computation (νφA)
    * probabilistic next-symbol prediction
    * PAL reinforcement feedback
    * gradient-based resonance correction
    * RSI-driven adaptive drift repair
    * telemetry emission + dynamic ε/k feedback
"""

import math
import numpy as np
from backend.modules.aion_prediction.temporal_coherence_memory import TemporalCoherenceMemory
from backend.modules.aion_prediction.predictive_bias_layer import PredictiveBias
from backend.modules.aion_learning.gradient_correction_layer import GradientCorrectionLayer
from backend.quant.telemetry.resonance_telemetry import ResonanceTelemetry
from backend.modules.aion_feedback.stability_feedback_loop import StabilityFeedbackLoop
from backend.modules.aion_feedback.resonance_stability_index import ResonanceStabilityIndex
from backend.modules.aion_feedback.adaptive_drift_repair import AdaptiveDriftRepair


class FusionCore:
    def __init__(self):
        # Core subsystems
        self.tcm = TemporalCoherenceMemory()
        self.pb = PredictiveBias()
        self.grad = GradientCorrectionLayer()
        self.telemetry = ResonanceTelemetry()
        self.feedback = StabilityFeedbackLoop()
        self.rsi_calc = ResonanceStabilityIndex()
        self.repair = AdaptiveDriftRepair()

        # Internal state
        self.current_rsi = 0.0
        self.last_rsi = 0.0
        self.last_event = None
        self.last_event_vec = None
        self.last_prediction = None
        self.last_symbol = None

    # ─────────────────────────────────────────────
    # Temporal Δt vector computation
    # ─────────────────────────────────────────────
    def compute_temporal_vector(self, event_a, event_b):
        """Compute Δt temporal embedding vector νφA."""
        try:
            dt = max(1e-9, event_b["timestamp"] - event_a["timestamp"])
            vec = np.array([dt, math.log1p(dt), 1.0 / dt])
            return vec
        except Exception:
            return np.zeros(3)

    # ─────────────────────────────────────────────
    # Core update loop
    # ─────────────────────────────────────────────
    def update(self, event):
        """
        Main fusion update loop.

        event = {
            "symbol": "Φ",
            "vector": [float, ...],
            "timestamp": float,
            "reward": optional float
        }
        """
        symbol = event.get("symbol")
        reward = event.get("reward", 0.5)
        vec = np.array(event.get("vector", []))

        # Update sequence & predict next symbol via TCM
        self.tcm.update_sequence(symbol)
        temporal_pred = self.tcm.predict_next()

        # Predict next via PBL
        self.pb.observe_temporal(symbol)
        pbl_pred = self.pb.predict_temporal_next()
        self.last_symbol = symbol

        # Reinforce temporal accuracy
        if temporal_pred:
            score = self.tcm.evaluate_prediction(temporal_pred, symbol)
            if temporal_pred == symbol:
                self.tcm.reinforce(temporal_pred, symbol)
            self.tcm.apply_pal_feedback(reward)

        # Compute Δt vector and perform reinforcement
        if self.last_event:
            vec_dt = self.compute_temporal_vector(self.last_event, event)
            event["temporal_vector"] = vec_dt.tolist()

            if self.last_event_vec is not None and len(vec) > 0:
                # Gradient correction -> resonance reinforcement
                delta_reward = self.grad.reinforce(self.last_event_vec.tolist(), vec.tolist())

                # Apply reinforcement to Predictive Bias
                self.pb.apply_pal_feedback(delta_reward)
                self.pb.update(self.last_symbol, symbol, reward=delta_reward, vec=vec.tolist())

                # Emit telemetry packet
                self.telemetry.emit()

                # ─────────────────────────────────────────────
                # RSI computation
                # ─────────────────────────────────────────────
                try:
                    metrics = {
                        "ΔΦ": self.grad.avg_strength,
                        "Δε": getattr(self.pb, "epsilon", 0.0) or 0.0,
                        "μ": getattr(self.grad, "decay_rate", 0.0) or 0.0,
                        "κ": getattr(self.grad, "avg_strength", 0.0) or 0.0,
                    }
                    self.current_rsi = self.rsi_calc.compute(metrics)
                    self.last_rsi = self.current_rsi
                except Exception:
                    self.current_rsi = 0.0
                    self.last_rsi = 0.0

                # ─────────────────────────────────────────────
                # Stability feedback -> dynamic ε & k
                # ─────────────────────────────────────────────
                fb_state = self.feedback.step()
                self.pb.epsilon = fb_state["ε"]
                self.pb.k = fb_state["k"]

                # ─────────────────────────────────────────────
                # Adaptive Drift Repair (RSI monitoring)
                # ─────────────────────────────────────────────
                self.repair.check_and_repair(self.current_rsi, self.pb, self.grad)

        # Update memory for next iteration
        self.last_event = event
        self.last_event_vec = vec
        self.last_prediction = pbl_pred or temporal_pred

        # Return cycle diagnostics
        return {
            "predicted_temporal": temporal_pred,
            "predicted_bias": pbl_pred,
            "actual": symbol,
            "reward": reward,
            "confidence": self.pb.prediction_confidence,
            "avg_resonance_delta": self.grad.avg_strength,
            "RSI": round(self.current_rsi, 4),
            "ε": getattr(self.pb, "epsilon", None),
            "k": getattr(self.pb, "k", None),
        }

    # ─────────────────────────────────────────────
    # Diagnostics summary
    # ─────────────────────────────────────────────
    def summarize(self):
        print("📊 Fusion Summary")
        print(f"   Avg Resonance Δ: {self.grad.avg_strength:.4f}")
        print(f"   Predictive Confidence: {self.pb.prediction_confidence:.3f}")
        print(f"   RSI: {self.current_rsi:.3f}")
        print(f"   Exploration ε: {getattr(self.pb, 'epsilon', 0.0):.2f}")
        print(f"   k: {getattr(self.pb, 'k', 0)}")
        print(f"   Last Prediction: {self.last_prediction}")