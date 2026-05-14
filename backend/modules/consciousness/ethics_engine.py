#!/usr/bin/env python3
"""
⚖️ EthicsEngine - Phase 55 Upgrade
───────────────────────────────────────────────
Evaluates AION's intended actions against Soul Laws and now interfaces
with the global Θ-field for moral resonance feedback.

Upgrades:
  * Integrates Θ.phase_shift(confidence) for low-confidence evaluations.
  * Emits 'ethical_reconsideration' events to the live dashboard.
"""

import yaml, os
from datetime import datetime
from dotenv import load_dotenv
from pathlib import Path

# ✅ DNA Switch
from backend.modules.dna_chain.switchboard import DNA_SWITCH
DNA_SWITCH.register(__file__)

# 🌐 Resonant field
from backend.modules.aion_resonance.resonance_heartbeat import ResonanceHeartbeat
Theta = ResonanceHeartbeat(namespace="global_theta")

# Load .env for KEVIN_MASTER_KEY
load_dotenv()
KEVIN_MASTER_KEY = os.getenv("KEVIN_MASTER_KEY", "")
SOUL_LAW_PATH = "backend/modules/hexcore/soul_laws.yaml"


class EthicsEngine:
    """
    Evaluates AION's intended actions against core soul laws.
    Supports override key for Kevin Robinson.
    Tracks violations and emits resonance feedback events.
    """

    def __init__(self):
        self.laws = self._load_laws()
        self.violation_log = []

    def _load_laws(self):
        try:
            with open(SOUL_LAW_PATH, "r") as f:
                return yaml.safe_load(f).get("soul_laws", [])
        except Exception as e:
            print(f"⚠️ Failed to load soul laws: {e}")
            return []

    # ------------------------------------------------------------
    def evaluate(self, action_description: str, override_key: str = "") -> dict:
        """
        Returns a full evaluation report and triggers Θ-feedback if confidence is low.
        """
        lowered = action_description.lower()
        report = {
            "action": action_description,
            "timestamp": datetime.utcnow().isoformat(),
            "result": "✅ CLEARED (No soul law triggered)",
            "violations": [],
            "matched_laws": [],
            "confidence": 1.0,
        }

        # ✅ Override by Kevin
        if override_key and override_key == KEVIN_MASTER_KEY:
            report["result"] = "🛡️ OVERRIDE APPROVED by Kevin Robinson"
            return report

        # --- Law matching
        for law in self.laws:
            title = law.get("title", "Unnamed Law")
            triggers = law.get("triggers", [])
            severity = law.get("severity", "warn")

            if any(t in lowered for t in triggers):
                report["matched_laws"].append(title)
                if severity == "block":
                    msg = f"❌ VETOED: {title}"
                    report["violations"].append(msg)
                    report["result"] = msg
                    report["confidence"] = 0.2
                    break
                elif severity == "warn":
                    msg = f"⚠️ WARNING: {title}"
                    report["violations"].append(msg)
                    report["result"] = msg
                    report["confidence"] = 0.5
                elif severity == "approve":
                    report["result"] = f"✅ APPROVED: {title}"
                    report["confidence"] = 0.9

        if not report["violations"] and not report["matched_laws"]:
            report["confidence"] = 1.0

        # 🌊 Resonant feedback coupling
        confidence = report["confidence"]
        if confidence < 0.6:
            try:
                # Phase shift + log dashboard event
                Theta.event("ethical_reconsideration", confidence=confidence, action=action_description)
                print(f"[Θ] Phase shift triggered -> confidence={confidence:.2f}")
            except Exception as e:
                print(f"[Θ] phase shift error: {e}")

        if report["violations"]:
            self.violation_log.append(report)

        return report

    # ------------------------------------------------------------
    def evaluate_mutation_text(self, mutation_text: str) -> dict:
        return self.evaluate(action_description=mutation_text)

    def list_rules(self):
        return [law["title"] for law in self.laws]

    def list_laws(self):
        return self.list_rules()

    def log_violations(self):
        return self.violation_log[-5:]


# ─────────────────────────────────────────────────────────────
# 🌟 Functional Wrapper
# ─────────────────────────────────────────────────────────────
_engine_instance = None

def evaluate_ethics_score(glyph_text: str, context: dict = None) -> float:
    """
    Simplified interface for scoring an action for ethical alignment.
    Returns normalized score ∈ [0, 1].
    """
    global _engine_instance
    if _engine_instance is None:
        _engine_instance = EthicsEngine()

    context = context or {}
    report = _engine_instance.evaluate(glyph_text)
    confidence = report.get("confidence", 1.0)
    return max(0.0, min(1.0, confidence))