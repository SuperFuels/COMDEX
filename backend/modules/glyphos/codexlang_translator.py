# backend/modules/glyphos/codexlang_translator.py

"""
CodexLang Translator

Translates symbolic glyph strings into structured instruction trees for execution in CodexCore.
Supports basic parsing, operator chaining, and embedded metadata.
"""

from backend.modules.glyphos.glyph_instruction_set import get_instruction
from backend.modules.codex.codex_core import CodexCore

codex = CodexCore()


def parse_codexlang_string(code_str):
    """
    Converts a symbolic CodexLang string like:
    ⟦ Logic | If: x > 5 → ⊕(Grow, Reflect) ⟧
    Into a structured AST-like dictionary:
    {
        "type": "Logic",
        "tag": "If",
        "value": "x > 5",
        "action": {
            "op": "⊕",
            "args": ["Grow", "Reflect"]
        }
    }
    """
    try:
        body = code_str.strip("⟦⟧ ")
        left, action = body.split("→")
        type_tag, value = left.split(":")
        g_type, tag = type_tag.split("|")

        # Extract inner function or action
        action = action.strip()
        if "(" in action and action.endswith(")"):
            op_symbol = action[0]
            args = action[action.find("(") + 1 : -1].split(",")
            args = [a.strip() for a in args]
            action_data = {
                "op": op_symbol,
                "args": args
            }
        else:
            action_data = action

        return {
            "type": g_type.strip(),
            "tag": tag.strip(),
            "value": value.strip(),
            "action": action_data
        }
    except Exception as e:
        print(f"[⚠️] Failed to parse CodexLang string: {e}")
        return None


def translate_to_instruction(parsed_glyph):
    """
    Convert parsed structure into an executable function call.
    """
    action = parsed_glyph.get("action")

    if isinstance(action, str):
        # Simple direct action string
        instr = get_instruction(action)
        return instr.execute(parsed_glyph["value"]) if instr else None

    elif isinstance(action, dict):
        instr = get_instruction(action.get("op"))
        if instr:
            return instr.execute(*action.get("args", []))

    return None


def run_codexlang_string(glyph_string: str, context: dict = {}):
    """
    Parses and executes a full CodexLang symbolic glyph string.
    Uses CodexCore to handle memory, mutations, logging, etc.
    """
    return codex.execute(glyph_string, context=context)


# Example usage:
if __name__ == "__main__":
    s = "⟦ Logic | If: x > 5 → ⊕(Grow, Reflect) ⟧"
    parsed = parse_codexlang_string(s)
    result = translate_to_instruction(parsed)
    print("Parsed:", parsed)
    print("Result:", result)

    # Execute in full loop
    output = run_codexlang_string(s, context={"source": "example_test"})
    print("CodexCore Output:", output)