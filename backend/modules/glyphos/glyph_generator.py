# backend/modules/glyphos/glyph_generator.py
# 🔁 Glyph synthesis, reverse generation, and CodexLang translation

from typing import List, Dict, Optional
import re
from backend.modules.glyphos.glyph_synthesis_engine import compress_to_glyphs
from backend.modules.hexcore.memory_engine import store_memory_entry

GLYPH_TEMPLATE = "\u27E6 {type} | {tag} : {value} → {action} \u27E7"

class GlyphGenerator:
    def __init__(self):
        pass

    def generate_from_text(self, input_text: str, context: str = "dream") -> List[str]:
        """
        Compress input text into glyphs using synthesis engine and store in memory.
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
        Convert a dictionary to a glyph string: ⟦ type | tag : value → action ⟧
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
        Translate CodexLang string (e.g., 'Memory:Emotion = Love => Store') into glyph(s).
        Currently supports one expression per line.
        """
        glyphs = []
        for line in codex_code.strip().splitlines():
            line = line.strip()
            pattern = r"(\w+):(\w+)\s*=\s*(.+?)\s*=>\s*(\w+)"
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

    print(g.generate_from_text("My dreams are full of light."))

    dict_data = {
        "type": "Logic",
        "tag": "Truth",
        "value": "Yes",
        "action": "Declare"
    }
    print(g.reverse_generate_glyph(dict_data))

    codex_input = """
    Memory:Emotion = Gratitude => Store
    Goal:Skill = Flight => Achieve
    """
    print(g.codexlang_to_glyphs(codex_input))