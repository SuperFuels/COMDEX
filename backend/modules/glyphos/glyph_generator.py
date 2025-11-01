# backend/modules/glyphos/glyph_generator.py
# 🔁 Glyph synthesis, reverse generation, and CodexLang translation

import re
from typing import List, Dict, Optional

from backend.modules.glyphos.glyph_synthesis_engine import compress_to_glyphs
from backend.modules.hexcore.memory_engine import store_memory_entry

# Glyph rendering template: ⟦ type | tag : value -> action ⟧
GLYPH_TEMPLATE = "\u27E6 {type} | {tag} : {value} -> {action} \u27E7"

class GlyphGenerator:
    def __init__(self):
        pass

    def generate_from_text(self, input_text: str, context: str = "dream") -> List[str]:
        """
        Compress input text into symbolic glyphs and store the result in memory.
        """
        glyphs = compress_to_glyphs(input_text, source=context)
        store_memory_entry("generated_glyphs", {
            "context": context,
            "input": input_text,
            "glyphs": glyphs
        })
        return glyphs

    def reverse_generate_glyph(self, data: Dict[str, str]) -> str:
        """
        Convert a dictionary to a glyph string: ⟦ type | tag : value -> action ⟧
        """
        try:
            return GLYPH_TEMPLATE.format(
                type=data.get("type", "?"),
                tag=data.get("tag", "?"),
                value=data.get("value", "?"),
                action=data.get("action", "?")
            )
        except Exception as e:
            return f"[⚠️ Error generating glyph: {e}]"

    def codexlang_to_glyphs(self, codex_code: str) -> List[str]:
        """
        Convert CodexLang into glyphs. Example CodexLang:
        Memory:Emotion = Love => Store
        Goal:Skill = Flight => Achieve
        """
        glyphs = []
        lines = codex_code.strip().splitlines()

        pattern = r"(\w+):(\w+)\s*=\s*(.+?)\s*=>\s*(\w+)"
        for line in lines:
            line = line.strip()
            match = re.match(pattern, line)
            if match:
                g_type, tag, value, action = match.groups()
                glyphs.append(GLYPH_TEMPLATE.format(
                    type=g_type, tag=tag, value=value, action=action
                ))
            else:
                glyphs.append(f"[⚠️ Invalid CodexLang: {line}]")
        return glyphs


# 🧪 Optional: Standalone test
if __name__ == "__main__":
    g = GlyphGenerator()

    print("🔹 From Text:")
    print(g.generate_from_text("My dreams are full of light."))

    print("\n🔹 Reverse Glyph:")
    dict_data = {
        "type": "Logic",
        "tag": "Truth",
        "value": "Yes",
        "action": "Declare"
    }
    print(g.reverse_generate_glyph(dict_data))

    print("\n🔹 CodexLang:")
    codex_input = """
    Memory:Emotion = Gratitude => Store
    Goal:Skill = Flight => Achieve
    """
    print(g.codexlang_to_glyphs(codex_input))