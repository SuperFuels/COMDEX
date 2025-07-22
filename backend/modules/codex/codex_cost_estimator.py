# 📁 codex_cost_estimator.py

class CostEstimate:
    def __init__(self, energy=0, ethics_risk=0, delay=0, opportunity_loss=0):
        self.energy = energy
        self.ethics_risk = ethics_risk
        self.delay = delay
        self.opportunity_loss = opportunity_loss

    def total(self, weights=None):
        w = weights or {
            "energy": 1,
            "ethics_risk": 5,
            "delay": 1,
            "opportunity_loss": 2
        }
        return (
            self.energy * w["energy"] +
            self.ethics_risk * w["ethics_risk"] +
            self.delay * w["delay"] +
            self.opportunity_loss * w["opportunity_loss"]
        )


class CodexCostEstimator:
    def estimate_glyph_cost(self, glyph, context):
        """
        Heuristically estimate the symbolic cost of executing a glyph,
        based on glyph operators and context.
        """
        est = CostEstimate()

        if "⚛" in glyph or "⬁" in glyph:
            est.energy += 3
            est.ethics_risk += 2  # core mutation / self-rewrite
        if "💭" in glyph:
            est.delay += 1  # slow cognitive task
        if "🧬" in glyph:
            est.opportunity_loss += 2  # child AI limits current path
        if "🧭" in glyph:
            est.energy += 1  # exploration
            est.delay += 1
        if "⧖" in glyph:
            est.delay += 2  # async or time-sensitive
        if "↔" in glyph:
            est.ethics_risk += 1  # entanglement has risk

        # Context-specific cost modifiers
        source = context.get("source", "")
        tags = context.get("tags", [])

        if source == "dream":
            est.delay += 2
        if "symbolic-thought" in tags:
            est.energy += 1
        if "memory-loop" in tags:
            est.opportunity_loss += 1

        return est