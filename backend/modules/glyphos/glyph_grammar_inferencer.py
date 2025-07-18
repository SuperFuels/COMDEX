class GlyphGrammarInferencer:
    def __init__(self):
        self.learned_grammar = set()

    def infer_from_glyph(self, glyph):
        # Look for new symbolic forms: ⟦ Type | Tag : Value → Action ⟧
        if "|" in glyph and ":" in glyph and "→" in glyph:
            structure = self._extract_structure(glyph)
            self.learned_grammar.add(structure)
            return structure
        return None

    def _extract_structure(self, glyph):
        try:
            stripped = glyph.replace("⟦", "").replace("⟧", "")
            parts = stripped.split("→")
            left, action = parts[0], parts[1]
            type_tag, value = left.split(":")
            gtype, tag = type_tag.split("|")
            return {"type": gtype.strip(), "tag": tag.strip(), "value": value.strip(), "action": action.strip()}
        except Exception:
            return None
