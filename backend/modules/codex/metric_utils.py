# backend/modules/codex/metric_utils.py

def estimate_glyph_cost(glyph: dict) -> float:
    """
    Estimate the symbolic cost of a glyph.
    Factors may include depth, complexity, entropy, etc.
    """
    if not glyph:
        return 0.0

    ops = glyph.get("ops", [])
    depth = glyph.get("depth", 1)
    entropy = glyph.get("entropy", 0.0)

    cost = len(ops) * 1.2 + depth * 0.8 + entropy * 1.5
    return round(cost, 3)