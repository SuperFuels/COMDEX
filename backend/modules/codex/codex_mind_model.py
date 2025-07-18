# 📁 codex_mind_model.py

from collections import defaultdict

class CodexMindModel:
    def __init__(self):
        self.symbol_predictions = defaultdict(list)

    def observe(self, glyph):
        if "→" in glyph:
            left, right = glyph.split("→")
            self.symbol_predictions[left.strip()].append(right.strip())

    def predict(self, seed):
        return self.symbol_predictions.get(seed.strip(), [])
