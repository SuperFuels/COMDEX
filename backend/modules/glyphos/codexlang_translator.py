"""
CodexLang Translator

Translates symbolic glyph strings into structured instruction trees for execution in CodexCore.
Supports nested parsing, symbolic ops, and runtime dispatch.
"""

from backend.modules.codex.canonical_ops import CANONICAL_OPS
from backend.modules.glyphos.glyph_instruction_set import get_instruction
from backend.modules.symbolic_engine.symbolic_kernels.logic_glyphs import (
    AndGlyph, OrGlyph, NotGlyph, ImplicationGlyph
)


# ────────────────────────────────────────────────
# CodexLangTranslator class (wrapper)
# ────────────────────────────────────────────────

class CodexLangTranslator:
    """
    Object-oriented wrapper around CodexLang parsing/translation utilities.
    Provides a stable API for tests and executor pipeline.
    """

    def __init__(self, memory=None):
        self.memory = memory

    def parse(self, glyph_string: str):
        """Parse CodexLang string into a canonical AST dict."""
        return parse_codexlang_string(glyph_string)

    def to_instruction(self, parsed_glyph: dict):
        """Translate parsed glyph AST into an executable instruction tree."""
        return translate_to_instruction(parsed_glyph, memory=self.memory)

    def run(self, glyph_string: str, context: dict = None, trace: bool = False):
        """
        Full parse → translate → execute pipeline.
        If trace=True, returns detailed step log.
        """
        trace_log = []

        # Stage 1: Input
        if trace:
            trace_log.append({"stage": "input", "data": glyph_string})

        # Stage 2: Parse
        parsed = self.parse(glyph_string)
        if not parsed:
            return {"status": "error", "error": "Failed to parse glyph string"}

        if trace:
            trace_log.append({"stage": "parsed", "data": parsed})

        # Stage 3: Canonicalization
        canonicalized = translate_node(parsed.get("action"))
        if trace:
            trace_log.append({"stage": "canonicalized", "data": canonicalized})

        # Stage 4: Instruction translation
        instruction = self.to_instruction(parsed)
        if trace:
            trace_log.append({"stage": "instruction", "data": instruction})

        # Stage 5: Execution (through CodexCore)
        from backend.modules.codex.codex_core import CodexCore
        codex = CodexCore()
        result = codex.execute(glyph_string, context=context or {})

        if trace:
            trace_log.append({"stage": "executed", "data": result})
            return {"status": "ok", "result": result, "trace": trace_log}

        return result

# ────────────────────────────────────────────────
# Canonicalization
# ────────────────────────────────────────────────
from backend.modules.codex.collision_resolver import resolve_op, ALIASES
from backend.modules.codex.canonical_ops import CANONICAL_OPS

from backend.modules.codex.collision_resolver import resolve_op, ALIASES
from backend.modules.codex.canonical_ops import CANONICAL_OPS

from backend.modules.codex.collision_resolver import resolve_op, ALIASES
from backend.modules.codex.canonical_ops import CANONICAL_OPS

from backend.modules.codex.collision_resolver import resolve_op, ALIASES
from backend.modules.codex.canonical_ops import CANONICAL_OPS

def translate_node(node, context: str = None):
    """
    Walk a parsed node and normalize all ops into canonical domain-tagged keys.

    Resolution order:
      1) Explicit ALIASES (⊕_q → quantum:⊕, ⊗_p → physics:⊗, etc.)
      2) CANONICAL_OPS (flat, non-colliding map — respects monkeypatching in tests)
      3) resolve_op (handles collisions + priority fallback, optionally using context)
    """
    if isinstance(node, dict) and "op" in node:
        sym = node["op"]

        # 1️⃣ Alias detection must come first
        if sym in ALIASES:
            node["op"] = ALIASES[sym]

        # 2️⃣ Canonical direct mapping (supports monkeypatches in tests)
        elif sym in CANONICAL_OPS:
            node["op"] = CANONICAL_OPS[sym]

        # 3️⃣ Collision resolver (use context if available)
        else:
            node["op"] = resolve_op(sym, context=context)

        # Recurse into children, passing the same context
        node["args"] = [translate_node(arg, context=context) for arg in node.get("args", [])]

    return node


# ────────────────────────────────────────────────
# Logic Parsing
# ────────────────────────────────────────────────

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


# ────────────────────────────────────────────────
# CodexLang Parsing
# ────────────────────────────────────────────────

from backend.modules.codex.canonical_ops import CANONICAL_OPS

def parse_codexlang_string(code_str):
    """
    Converts a symbolic CodexLang string like:
    ⟦ Logic | If: x > 5 → ⊕(Grow, Reflect) ⟧
    Into a structured AST-like dictionary with canonicalized ops.
    """
    try:
        body = code_str.strip("⟦⟧ ").strip()

        # Handle shorthand form (no → present)
        if "→" not in body:
            type_tag, action = body.split(":", 1)
            g_type, tag = type_tag.split("|", 1)
            parsed_action = parse_action_expr(action.strip())
            parsed_action = translate_node(parsed_action, context=g_type.strip().lower())
            return {
                "type": g_type.strip().lower(),
                "tag": tag.strip(),
                "value": None,
                "action": parsed_action,
            }

        # Handle full → form
        left, action = body.split("→", 1)
        type_tag, value = left.split(":", 1)
        g_type, tag = type_tag.split("|", 1)

        parsed_action = parse_action_expr(action.strip())
        parsed_action = translate_node(parsed_action, context=g_type.strip().lower())

        parsed = {
            "type": g_type.strip().lower(),
            "tag": tag.strip(),
            "value": value.strip(),
            "action": parsed_action,
        }

        if parsed["type"] == "logic":
            # ✅ ensure disambiguation inside logic trees
            parsed["tree"] = translate_node(logic_to_tree(action.strip()), context="logic")

        return parsed

    except Exception as e:   # ✅ keep error logging
        print(f"[⚠️] Failed to parse CodexLang string: {e}")
        return None

def parse_action_expr(expr):
    """
    Recursively parses nested operator expressions like:
    ⊕(Grow, ↔(Dream, Reflect))
    or ⊕_q(A, B)

    Returns a dict:
    {
        "op": "⊕_q",
        "args": ["A", {"op": "↔", "args": ["Dream", "Reflect"]}]
    }
    """
    expr = expr.strip()
    if "(" not in expr:
        return expr

    # Extract operator before the first "("
    op = expr[:expr.find("(")].strip()
    inner = expr[expr.find("(") + 1 : -1]

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


# ────────────────────────────────────────────────
# Translation / Execution
# ────────────────────────────────────────────────

def translate_to_instruction(parsed_glyph, memory=None, trace_log=None):
    def eval_action(action):
        if isinstance(action, str):
            instr = get_instruction(action)
            result = instr.execute() if instr else action
            if trace_log is not None:
                trace_log.append({
                    "stage": "execute",
                    "op": action,
                    "args": [],
                    "result": result,
                })
            return result

        elif isinstance(action, dict):
            op = action.get("op")
            args = [eval_action(arg) for arg in action.get("args", [])]
            instr = get_instruction(op)
            if instr:
                try:
                    result = instr.execute(*args, memory=memory)
                except TypeError:
                    result = instr.execute(*args)
            else:
                result = {"error": f"Unknown operator: {op}", "args": args}

            if trace_log is not None:
                trace_log.append({
                    "stage": "execute",
                    "op": op,
                    "args": args,
                    "result": result,
                })
            return result

        elif hasattr(action, "evaluate"):
            result = action.evaluate()
            if trace_log is not None:
                trace_log.append({
                    "stage": "evaluate",
                    "op": type(action).__name__,
                    "result": result,
                })
            return result

        # ⚠️ Always log fallthrough
        if trace_log is not None:
            trace_log.append({
                "stage": "fallback",
                "op": str(action),
                "result": action,
            })
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