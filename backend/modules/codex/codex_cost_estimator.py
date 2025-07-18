# 📁 codex_cost_estimator.py

class CostEstimate:
    def __init__(self, energy=0, ethics_risk=0, delay=0, opportunity_loss=0):
        self.energy = energy
        self.ethics_risk = ethics_risk
        self.delay = delay
        self.opportunity_loss = opportunity_loss

    def total(self, weights=None):
        w = weights or {"energy": 1, "ethics_risk": 5, "delay": 1, "opportunity_loss": 2}
        return (
            self.energy * w["energy"] +
            self.ethics_risk * w["ethics_risk"] +
            self.delay * w["delay"] +
            self.opportunity_loss * w["opportunity_loss"]
        )


class CodexCostEstimator:
    def estimate_glyph_cost(self, glyph, context):
        # TODO: smarter heuristics or train a predictor
        est = CostEstimate()

        if "⚛" in glyph or "⬁" in glyph:
            est.energy += 3
            est.ethics_risk += 2  # deep mutation
        if "💭" in glyph:
            est.delay += 1  # slow reflection
        if "🧬" in glyph:
            est.opportunity_loss += 2  # may limit other futures

        # Example from context
        if context.get("source") == "dream":
            est.delay += 2

        return est