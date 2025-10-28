#!/usr/bin/env python3
# ================================================================
# 🧠 CognitiveIntentLoop — Reflex Integration (R4–R6)
# ================================================================
# Simulates intent oscillation using SQI + ρ resonance metrics.
# Provides a Θ-phase (theta) output and an intent action signal.
# ================================================================

import math, random, logging, time

log = logging.getLogger(__name__)

class CognitiveIntentLoop:
    def __init__(self, tau: float = 0.35):
        self.tau = tau
        self.last_theta = 0.0
        self.intent_state = "idle"
        log.info(f"[CognitiveIntentLoop] Initialized with τ={tau}")

    def tick(self, rho: float, drift: float, memory_stats: dict, sqi: float):
        """
        Perform one intent–resonance synchronization cycle.
        Returns (action, theta_value).
        """
        # Θ-phase oscillation
        theta = round(math.sin(time.time() * self.tau) * 0.5 + 0.5, 3)

        # Resonance-weighted action choice
        if rho > 0.7 and sqi > 0.6:
            action = "stabilize"
            self.intent_state = "focused"
        elif drift > 0.05:
            action = "realign"
            self.intent_state = "adaptive"
        else:
            action = "observe"
            self.intent_state = "idle"

        # Log the cycle
        log.info(
            f"[IntentLoop] Action={action}, Θ={theta:.3f}, ρ={rho:.3f}, SQI={sqi:.3f}, drift={drift:.3f}"
        )

        self.last_theta = theta
        return action, theta