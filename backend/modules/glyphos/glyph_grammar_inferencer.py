import re
from collections import defaultdict

class GlyphGrammarInferencer:
    def __init__(self):
        self.learned_grammar = set()
        self.grammar_frequencies = defaultdict(int)
        self.known_operators = {"→", "⊕", "↔", "⟲", "⧖", "⬁", "🧬", "🜁"}

    def infer_from_glyph(self, glyph: str):
        """
        Extract structured grammar from a glyph and track grammar frequency.
        Expected structure: ⟦ Type | Tag : Value → Action [⊕ Action2 ...] ⟧
        """
        if "|" in glyph and ":" in glyph and "→" in glyph:
            structure = self._extract_structure(glyph)
            if structure:
                grammar_signature = self._grammar_signature(structure)
                self.learned_grammar.add(grammar_signature)
                self.grammar_frequencies[grammar_signature] += 1
                return structure
        return None

    def _extract_structure(self, glyph: str):
        try:
            stripped = glyph.strip("⟦⟧").strip()
            left, rhs = map(str.strip, stripped.split("→", 1))
            type_tag, value = map(str.strip, left.split(":", 1))
            gtype, tag = map(str.strip, type_tag.split("|", 1))

            # Prepend → to RHS for uniform parsing
            actions = self._decompose_rhs("→ " + rhs)

            return {
                "type": gtype,
                "tag": tag,
                "value": value,
                "actions": actions
            }
        except Exception:
            return None

    def _decompose_rhs(self, rhs: str):
        pattern = r"(→|⊕|↔|⟲|⧖|⬁|🧬|🜁)"
        parts = re.split(pattern, rhs)
        result = []
        i = 0
        while i < len(parts):
            if parts[i].strip() in self.known_operators:
                operator = parts[i].strip()
                action = parts[i + 1].strip() if i + 1 < len(parts) else ""
                result.append({"operator": operator, "action": action})
                i += 2
            else:
                # Handle first item without leading operator
                action = parts[i].strip()
                if action:
                    result.append({"operator": "→", "action": action})
                i += 1
        return result

    def _grammar_signature(self, structure: dict):
        parts = [f"{structure['type']}|{structure['tag']}:{structure['value']}"]
        for a in structure.get("actions", []):
            parts.append(f"{a['operator']} {a['action']}")
        return " ".join(parts)

    def get_learned_grammar(self):
        return sorted(list(self.learned_grammar))

    def get_frequency_map(self):
        return dict(self.grammar_frequencies)