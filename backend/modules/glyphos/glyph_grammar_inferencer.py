# backend/modules/glyphos/glyph_grammar_inferencer.py

import re
from collections import defaultdict
from typing import Optional, List, Dict, Any


class GlyphGrammarInferencer:
    def __init__(self):
        self.learned_grammar: set[str] = set()
        self.grammar_frequencies: dict[str, int] = defaultdict(int)
        self.known_operators: set[str] = {"→", "⊕", "↔", "⟲", "⧖", "⬁", "🧬", "🜁"}

    def infer_from_glyph(self, glyph: str) -> Optional[Dict[str, Any]]:
        """
        Extract structured grammar from a glyph and track grammar frequency.
        Example structure:
        {
            "type": "Memory",
            "tag": "Emotion",
            "value": "Love",
            "actions": [{"operator": "→", "action": "Store"}]
        }
        """
        if "|" in glyph and ":" in glyph and "→" in glyph:
            structure = self._extract_structure(glyph)
            if structure:
                signature = self._grammar_signature(structure)
                self.learned_grammar.add(signature)
                self.grammar_frequencies[signature] += 1
                return structure
        return None

    def _extract_structure(self, glyph: str) -> Optional[Dict[str, Any]]:
        try:
            stripped = glyph.strip("⟦⟧").strip()
            left, rhs = map(str.strip, stripped.split("→", 1))
            type_tag, value = map(str.strip, left.split(":", 1))
            gtype, tag = map(str.strip, type_tag.split("|", 1))

            actions = self._decompose_rhs("→ " + rhs)
            return {
                "type": gtype,
                "tag": tag,
                "value": value,
                "actions": actions
            }
        except Exception as e:
            print(f"[⚠️ Grammar Error] Failed to parse glyph: {e}")
            return None

    def _decompose_rhs(self, rhs: str) -> List[Dict[str, str]]:
        """
        Break the RHS into operator-action pairs.
        """
        pattern = r"(→|⊕|↔|⟲|⧖|⬁|🧬|🜁)"
        parts = re.split(pattern, rhs)
        result = []
        i = 0
        while i < len(parts):
            part = parts[i].strip()
            if part in self.known_operators:
                operator = part
                action = parts[i + 1].strip() if i + 1 < len(parts) else ""
                result.append({"operator": operator, "action": action})
                i += 2
            else:
                # Handle first item without leading operator
                if part:
                    result.append({"operator": "→", "action": part})
                i += 1
        return result

    def _grammar_signature(self, structure: Dict[str, Any]) -> str:
        base = f"{structure['type']}|{structure['tag']}:{structure['value']}"
        ops = " ".join(f"{a['operator']} {a['action']}" for a in structure.get("actions", []))
        return f"{base} {ops}"

    def get_learned_grammar(self) -> List[str]:
        return sorted(self.learned_grammar)

    def get_frequency_map(self) -> Dict[str, int]:
        return dict(self.grammar_frequencies)