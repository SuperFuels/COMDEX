# 📁 codex_mind_model.py
# Predicts symbolic operators and tracks context linkage

from collections import deque, Counter
import re

class CodexMindModel:
    def __init__(self):
        self.recent_glyphs = deque(maxlen=50)
        self.symbol_predictions = Counter()
        self.linked_contexts = {}

    def observe(self, glyph: str):
        self.recent_glyphs.append(glyph)

        # Count symbolic operators (⊕, ↔, ⟲, →, ⧖)
        operators = re.findall(r"[⊕↔⟲→⧖]", glyph)
        for op in operators:
            self.symbol_predictions[op] += 1

        # Optionally: link by Tag or Value
        parts = re.findall(r"⟦(.*?)⟧", glyph)
        for part in parts:
            if "|" in part:
                tag_block = part.split("|")[1]
                if ":" in tag_block:
                    tag, value = tag_block.split(":")
                    tag, value = tag.strip(), value.strip()
                    if tag not in self.linked_contexts:
                        self.linked_contexts[tag] = Counter()
                    self.linked_contexts[tag][value] += 1

    def suggest_next_operator(self) -> str:
        """Suggest the most commonly used symbolic operator."""
        if not self.symbol_predictions:
            return "→"
        return self.symbol_predictions.most_common(1)[0][0]

    def dump(self):
        return {
            "recent": list(self.recent_glyphs),
            "predictions": dict(self.symbol_predictions),
            "context_links": {
                k: dict(v) for k, v in self.linked_contexts.items()
            }
        }