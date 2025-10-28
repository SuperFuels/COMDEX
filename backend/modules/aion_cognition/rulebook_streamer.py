#!/usr/bin/env python3
# ================================================================
# 📜 RuleBookStreamer — Reflex Micro-Rule Evaluation Layer (R5)
# ================================================================
# Streams rule atoms for a given action/context pair and tags
# potential violations based on simple symbolic heuristics.
# ================================================================

import logging, random, time
from typing import Dict, Any, List

log = logging.getLogger(__name__)

class RuleBookStreamer:
    def __init__(self):
        self.active_rules = ["entropy_balance", "resonance_stability", "ethical_alignment"]
        log.info("[RuleBookStreamer] Initialized with 3 default rule atoms.")

    def stream(self, action: str, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Generate a stream of rule atoms and simulate minor violations
        based on random entropy thresholds.
        """
        atoms = []
        base_entropy = context.get("intensity", random.uniform(0.1, 0.5))
        for rule in self.active_rules:
            violation_prob = min(0.5, base_entropy * random.uniform(0.5, 1.5))
            violated = random.random() < violation_prob
            atom = {
                "rule": rule,
                "timestamp": time.time(),
                "violated": violated,
                "entropy": round(base_entropy, 3),
                "context": action,
            }
            atoms.append(atom)

        log.info(f"[RuleBookStreamer] Streamed {len(atoms)} rule atoms for action '{action}'.")
        return atoms