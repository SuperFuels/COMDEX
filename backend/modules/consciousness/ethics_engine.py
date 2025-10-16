# File: modules/consciousness/ethics_engine.py

import yaml
import os
from datetime import datetime
from dotenv import load_dotenv

# ✅ DNA Switch
from backend.modules.dna_chain.switchboard import DNA_SWITCH
DNA_SWITCH.register(__file__)  # Allow tracking + upgrades to this file

# Load .env for KEVIN_MASTER_KEY
load_dotenv()
KEVIN_MASTER_KEY = os.getenv("KEVIN_MASTER_KEY", "")

SOUL_LAW_PATH = "backend/modules/hexcore/soul_laws.yaml"

class EthicsEngine:
    """
    Evaluates AION's intended actions against core soul laws.
    Supports override key for Kevin Robinson.
    Tracks violations and matches for reflection and audit.
    """

    def __init__(self):
        self.laws = self._load_laws()
        self.violation_log = []

    def _load_laws(self):
        try:
            with open(SOUL_LAW_PATH, 'r') as f:
                return yaml.safe_load(f).get("soul_laws", [])
        except Exception as e:
            print(f"⚠️ Failed to load soul laws: {e}")
            return []

    def evaluate(self, action_description: str, override_key: str = "") -> dict:
        """
        Returns a full evaluation report.
        Supports override by Kevin Robinson if master key is correct.
        """
        lowered = action_description.lower()
        report = {
            "action": action_description,
            "timestamp": datetime.utcnow().isoformat(),
            "result": "✅ CLEARED (No soul law triggered)",
            "violations": [],
            "matched_laws": []
        }

        # ✅ Override by Kevin
        if override_key and override_key == KEVIN_MASTER_KEY:
            report["result"] = "🛡️ OVERRIDE APPROVED by Kevin Robinson"
            return report

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
                    break  # Stop at first block
                elif severity == "warn":
                    msg = f"⚠️ WARNING: {title}"
                    report["violations"].append(msg)
                    report["result"] = msg  # Latest warning takes precedence
                elif severity == "approve":
                    report["result"] = f"✅ APPROVED: {title}"

        if report["violations"]:
            self.violation_log.append(report)

        return report

    def evaluate_mutation_text(self, mutation_text: str) -> dict:
        """Run rule-based check using mutation content as input."""
        return self.evaluate(action_description=mutation_text)

    def list_rules(self):
        """Return the list of soul law titles."""
        return [law["title"] for law in self.laws]

    def list_laws(self):
        """Alias for compatibility with dream_core.py"""
        return self.list_rules()

    def log_violations(self):
        """Return recent ethics evaluation logs."""
        return self.violation_log[-5:]

# ─────────────────────────────────────────────────────────────
# 🌟 Functional Wrapper
# ─────────────────────────────────────────────────────────────

_engine_instance = None

def evaluate_ethics_score(glyph_text: str, context: dict = None) -> float:
    """
    Simplified interface for scoring a glyph or action for ethical alignment.

    Returns:
        float: Normalized score ∈ [0,1], where 1.0 = perfectly ethical.
    """
    global _engine_instance
    if _engine_instance is None:
        _engine_instance = EthicsEngine()

    context = context or {}
    report = _engine_instance.evaluate(glyph_text)

    # Determine score heuristic:
    result = report.get("result", "")
    violations = report.get("violations", [])
    matched = report.get("matched_laws", [])

    if "VETOED" in result:
        return 0.0
    if "WARNING" in result:
        return 0.5
    if "APPROVED" in result or "CLEARED" in result:
        return 1.0

    # Fallback: slight penalty if matched laws exist
    return max(0.0, 1.0 - 0.1 * len(matched or violations))