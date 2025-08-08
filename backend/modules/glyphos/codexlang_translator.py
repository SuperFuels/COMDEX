"""
CodexLang Translator

Translates symbolic glyph strings into structured instruction trees for execution in CodexCore.
Supports nested parsing, symbolic ops, and runtime dispatch.
"""

from backend.modules.glyphos.glyph_instruction_set import get_instruction
from backend.modules.symbolic_engine.symbolic_kernels.logic_glyphs import (
    AndGlyph, OrGlyph, NotGlyph, ImplicationGlyph
)


def parse_logic_expression(expr: str):
    """
    Parses logical expressions like:
    A ∧ B → C
    ¬A ∨ B
    Returns nested LogicGlyph trees.
    """
    expr = expr.strip()
    if "→" in expr:
        left, right = expr.split("→", 1)
        return ImplicationGlyph(parse_logic_expression(left), parse_logic_expression(right))
    elif "∧" in expr:
        left, right = expr.split("∧", 1)
        return AndGlyph(parse_logic_expression(left), parse_logic_expression(right))
    elif "∨" in expr:
        left, right = expr.split("∨", 1)
        return OrGlyph(parse_logic_expression(left), parse_logic_expression(right))
    elif expr.startswith("¬"):
        return NotGlyph(parse_logic_expression(expr[1:].strip()))
    else:
        return expr  # Raw variable


def logic_to_tree(expr: str):
    """
    Outputs the logic expression as a structured tree (for serialization).
    Used for bytecode encoding and Codex export.
    """
    expr = expr.strip()
    if "→" in expr:
        left, right = expr.split("→", 1)
        return {"op": "→", "args": [logic_to_tree(left), logic_to_tree(right)]}
    elif "∧" in expr:
        left, right = expr.split("∧", 1)
        return {"op": "∧", "args": [logic_to_tree(left), logic_to_tree(right)]}
    elif "∨" in expr:
        left, right = expr.split("∨", 1)
        return {"op": "∨", "args": [logic_to_tree(left), logic_to_tree(right)]}
    elif expr.startswith("¬"):
        return {"op": "¬", "args": [logic_to_tree(expr[1:].strip())]}
    else:
        return expr


def parse_codexlang_string(code_str):
    """
    Converts a symbolic CodexLang string like:
    ⟦ Logic | If: x > 5 → ⊕(Grow, Reflect) ⟧
    Into a structured AST-like dictionary.
    """
    try:
        body = code_str.strip("⟦⟧ ").strip()
        left, action = body.split("→", 1)
        type_tag, value = left.split(":", 1)
        g_type, tag = type_tag.split("|", 1)

        type_str = g_type.strip().lower()
        if type_str == "logic":
            parsed = {
                "type": type_str,
                "tag": tag.strip(),
                "value": value.strip(),
                "action": parse_logic_expression(action.strip()),
                "tree": logic_to_tree(action.strip())  # ✅ structured version
            }
        else:
            parsed = {
                "type": type_str,
                "tag": tag.strip(),
                "value": value.strip(),
                "action": parse_action_expr(action.strip())
            }

        return parsed
    except Exception as e:
        print(f"[⚠️] Failed to parse CodexLang string: {e}")
        return None


def parse_action_expr(expr):
    """
    Recursively parses nested operator expressions like:
    ⊕(Grow, ↔(Dream, Reflect))
    Into:
    {
        "op": "⊕",
        "args": [
            "Grow",
            {
                "op": "↔",
                "args": ["Dream", "Reflect"]
            }
        ]
    }
    """
    expr = expr.strip()
    if "(" not in expr:
        return expr

    op = expr[0]
    inner = expr[expr.find("(")+1 : -1]
    args = []
    depth = 0
    buffer = ""
    for char in inner:
        if char == "," and depth == 0:
            args.append(parse_action_expr(buffer.strip()))
            buffer = ""
        else:
            if char == "(":
                depth += 1
            elif char == ")":
                depth -= 1
            buffer += char
    if buffer:
        args.append(parse_action_expr(buffer.strip()))

    return {"op": op, "args": args}


def translate_to_instruction(parsed_glyph, memory=None):
    """
    Convert parsed structure into an executable tree using dispatch system.
    Uses symbolic operator functions from the glyph_instruction_set.
    """
    def eval_action(action):
        if isinstance(action, str):
            instr = get_instruction(action)
            return instr.execute() if instr else action

        elif isinstance(action, dict):
            op = action.get("op")
            args = [eval_action(arg) for arg in action.get("args", [])]
            instr = get_instruction(op)
            if instr:
                try:
                    return instr.execute(*args, memory=memory)
                except TypeError:
                    return instr.execute(*args)
            else:
                return {"error": f"Unknown operator: {op}", "args": args}

        elif hasattr(action, "evaluate"):
            return action.evaluate()

        return action

    return eval_action(parsed_glyph.get("action"))


def run_codexlang_string(glyph_string: str, context: dict = {}):
    """
    Full CodexLang runtime: parse, dispatch, and execute symbolic glyph string.
    Uses CodexCore for actual logic execution.
    """
    from backend.modules.codex.codex_core import CodexCore  # ⬅ Delayed import
    codex = CodexCore()
    return codex.execute(glyph_string, context=context)


# Debug entry point
if __name__ == "__main__":
    test = "⟦ Logic | Test: A ∧ B → ¬C ⟧"
    print("\n[🔍] Parsing:", test)
    parsed = parse_codexlang_string(test)
    print("Parsed AST:", parsed)

    translated = translate_to_instruction(parsed)
    print("Translated Instruction:", translated)

    output = run_codexlang_string(test, context={"source": "test"})
    print("CodexCore Output:", output)