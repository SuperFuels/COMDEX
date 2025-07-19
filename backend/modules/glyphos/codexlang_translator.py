"""
CodexLang Translator

Translates symbolic glyph strings into structured instruction trees for execution in CodexCore.
Supports nested parsing, symbolic ops, and runtime dispatch.
"""

from backend.modules.glyphos.glyph_instruction_set import get_instruction


def parse_codexlang_string(code_str):
    """
    Converts a symbolic CodexLang string like:
    ⟦ Logic | If: x > 5 → ⊕(Grow, Reflect) ⟧
    Into a structured AST-like dictionary.
    Supports nested operators.
    """
    try:
        body = code_str.strip("⟦⟧ ").strip()
        left, action = body.split("→", 1)
        type_tag, value = left.split(":", 1)
        g_type, tag = type_tag.split("|", 1)

        parsed = {
            "type": g_type.strip(),
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
    Recursively parses expressions like:
    ⊕(Grow, ∇(Dream, Reflect))
    into:
    {
        "op": "⊕",
        "args": [
            "Grow",
            {
                "op": "∇",
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
    Convert parsed structure into an executable function call using dispatch.
    Supports nested expressions and memory context.
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

    return eval_action(parsed_glyph.get("action"))


def run_codexlang_string(glyph_string: str, context: dict = {}):
    """
    Full loop: parse, interpret, and run CodexLang string using CodexCore.
    Handles memory, trace, and metrics.
    Delayed import to avoid circular import error.
    """
    from backend.modules.codex.codex_core import CodexCore  # ⬅ Delayed import
    codex = CodexCore()
    return codex.execute(glyph_string, context=context)


# Example usage
if __name__ == "__main__":
    test = "⟦ Logic | If: x > 5 → ⊕(Grow, ∇(Dream, Reflect)) ⟧"
    parsed = parse_codexlang_string(test)
    print("Parsed AST:", parsed)
    result = translate_to_instruction(parsed)
    print("Translated Result:", result)

    # Full runtime
    output = run_codexlang_string(test, context={"source": "test"})
    print("CodexCore Output:", output)