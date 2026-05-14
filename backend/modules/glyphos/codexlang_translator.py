"""
CodexLang Translator

Translates symbolic glyph strings into structured instruction trees for execution in CodexCore.
Supports nested parsing, symbolic ops, and runtime dispatch.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from backend.modules.glyphos.glyph_instruction_set import get_instruction
from backend.modules.symbolic_engine.symbolic_kernels.logic_glyphs import (
    AndGlyph,
    OrGlyph,
    NotGlyph,
    ImplicationGlyph,
)

# Canonicalization / collision resolution
from backend.modules.codex.collision_resolver import resolve_op, ALIASES
from backend.modules.codex.canonical_ops import CANONICAL_OPS


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

    def parse(self, glyph_string: str) -> Dict[str, Any]:
        """Parse CodexLang string into a canonical AST dict."""
        return parse_codexlang_string(glyph_string)

    def to_instruction(self, parsed_glyph: Dict[str, Any]):
        """Translate parsed glyph AST into an executable instruction tree."""
        return translate_to_instruction(parsed_glyph, memory=self.memory)

    def run(self, glyph_string: str, context: Optional[dict] = None, trace: bool = False):
        """
        Full parse -> translate -> execute pipeline.
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
def translate_node(node: Any, context: str | None = None):
    """
    Walk a parsed node and normalize all ops into canonical domain-tagged keys.

    Resolution order:
      1) Explicit ALIASES (⊕_q -> quantum:⊕, ⊗_p -> physics:⊗, etc.)
      2) CANONICAL_OPS (flat, non-colliding map - respects monkeypatching in tests)
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
    A ∧ B -> C
    ¬A ∨ B
    Returns nested LogicGlyph trees.
    """
    expr = expr.strip()
    if "->" in expr:
        left, right = expr.split("->", 1)
        return ImplicationGlyph(parse_logic_expression(left), parse_logic_expression(right))
    if "∧" in expr:
        left, right = expr.split("∧", 1)
        return AndGlyph(parse_logic_expression(left), parse_logic_expression(right))
    if "∨" in expr:
        left, right = expr.split("∨", 1)
        return OrGlyph(parse_logic_expression(left), parse_logic_expression(right))
    if expr.startswith("¬"):
        return NotGlyph(parse_logic_expression(expr[1:].strip()))
    return expr  # Raw variable


def logic_to_tree(expr: str):
    """
    Outputs the logic expression as a structured tree (for serialization).
    Used for bytecode encoding and Codex export.
    """
    expr = expr.strip()
    if "->" in expr:
        left, right = expr.split("->", 1)
        return {"op": "->", "args": [logic_to_tree(left), logic_to_tree(right)]}
    if "∧" in expr:
        left, right = expr.split("∧", 1)
        return {"op": "∧", "args": [logic_to_tree(left), logic_to_tree(right)]}
    if "∨" in expr:
        left, right = expr.split("∨", 1)
        return {"op": "∨", "args": [logic_to_tree(left), logic_to_tree(right)]}
    if expr.startswith("¬"):
        return {"op": "¬", "args": [logic_to_tree(expr[1:].strip())]}
    return expr


# ────────────────────────────────────────────────
# CodexLang Parsing
# ────────────────────────────────────────────────
def parse_codexlang_string(code_str: Any) -> Dict[str, Any]:
    """
    Converts a symbolic CodexLang string like:
    ⟦ Logic | If: x > 5 -> ⊕(Grow, Reflect) ⟧
    into a structured AST-like dictionary with canonicalized ops.

    ✅ SoulLaw-compliant and unpack-safe.
    🧩 Includes debug traces for malformed or atomic expressions.

    Also supports adapter payloads passed as dict-strings (single-quote dicts etc).
    """
    import traceback

    try:
        if code_str is None:
            print("[⚠️ DEBUG] parse_codexlang_string got None")
            return {
                "type": "noop",
                "status": "noop",
                "glyph": "∅",
                "reason": "none_input",
                "action": {},
                "raw": None,
                "soul_state": "trusted",
            }

        # If caller already passed a dict, accept it as a payload wrapper.
        if isinstance(code_str, dict):
            action = translate_node(code_str) if "op" in code_str else code_str
            return {"type": "payload", "tag": "dict", "value": None, "action": action, "soul_state": "trusted"}

        if not isinstance(code_str, str):
            print(f"[⚠️ DEBUG] Invalid code_str type in parse_codexlang_string: {type(code_str)}")
            return {
                "type": "noop",
                "status": "noop",
                "glyph": "∅",
                "reason": "invalid_input_type",
                "action": {},
                "raw": repr(code_str),
                "soul_state": "trusted",
            }

        stripped = code_str.strip()
        print(f"[🧠 DEBUG] parse_codexlang_string CALLED with: {repr(stripped)}")

        # ✅ Empty input -> no-op (prevents downstream validators from treating '' as a glyph)
        if not stripped or stripped in ("∅", "null", "none"):
            return {
                "type": "noop",
                "status": "noop",
                "glyph": "∅",
                "reason": "empty_codexlang_string",
                "action": {},
                "raw": stripped,
                "soul_state": "trusted",
            }

        # ─────────────────────────────────────────────────────────────
        # 🧩 Special-case: dict-string payloads (from adapters)
        #   Example: "{'op': '⊕', 'args': ['A','B']}"
        # ─────────────────────────────────────────────────────────────
        if stripped.startswith("{") and stripped.endswith("}"):
            # Try JSON first (double quotes), then ast.literal_eval (single quotes)
            obj = None
            try:
                import json as _json

                obj = _json.loads(stripped)
            except Exception:
                try:
                    import ast

                    obj = ast.literal_eval(stripped)
                except Exception:
                    obj = None

            if isinstance(obj, dict):
                action = translate_node(obj) if "op" in obj else obj
                return {"type": "payload", "tag": "dict", "value": None, "action": action, "soul_state": "trusted"}

        # 🩹 Atomic single-symbol guard
        if not any(sym in stripped for sym in ["->", ":", "⊕", "⊗", "↔", "=", "⟦", "⟧"]):
            print(f"[DEBUG] Treating '{stripped}' as atomic Codex term")
            return {"type": "atom", "value": stripped, "ast": None, "soul_state": "trusted"}

        # ──────────────────────────────────────────────
        body = stripped.strip("⟦⟧ ").strip()
        if not body:
            return {"type": "noop", "status": "noop", "glyph": "∅", "reason": "empty_body", "action": {}, "soul_state": "trusted"}

        # 🧩 Case 1 - shorthand form (no ->)
        if "->" not in body:
            print(f"[DEBUG] Shorthand CodexLang detected: {body}")
            if ":" not in body or "|" not in body:
                return {
                    "type": "incomplete",
                    "expr": body,
                    "soul_state": "partial",
                    "message": "Missing ':' or '|' in shorthand CodexLang",
                }

            try:
                type_tag, action = body.split(":", 1)
                g_type, tag = type_tag.split("|", 1)
            except ValueError as ve:
                print(f"[⚠️ DEBUG] Shorthand split ValueError: {ve}")
                return {
                    "type": "incomplete",
                    "expr": body,
                    "soul_state": "partial",
                    "message": f"Malformed shorthand split: {ve}",
                }

            parsed_action = parse_action_expr(action.strip())
            parsed_action = translate_node(parsed_action, context=g_type.strip().lower())
            return {
                "type": g_type.strip().lower(),
                "tag": tag.strip(),
                "value": None,
                "action": parsed_action,
                "soul_state": "trusted",
            }

        # 🧩 Case 2 - full form (->)
        parts = body.split("->", 1)
        print(f"[DEBUG] parts after split('->',1): {len(parts)} -> {parts}")
        if len(parts) != 2:
            return {
                "type": "incomplete",
                "expr": body,
                "soul_state": "partial",
                "message": "Missing right-hand operand after '->'",
            }

        left, action = parts
        if ":" not in left or "|" not in left:
            print("[⚠️ DEBUG] Left-hand side missing ':' or '|'")
            return {
                "type": "incomplete",
                "expr": left,
                "soul_state": "partial",
                "message": "Malformed left-hand side",
            }

        try:
            type_tag, value = left.split(":", 1)
            g_type, tag = type_tag.split("|", 1)
        except ValueError as ve:
            print(f"[⚠️ DEBUG] Left-hand split ValueError: {ve}")
            return {
                "type": "incomplete",
                "expr": left,
                "soul_state": "partial",
                "message": f"Malformed left-hand type/tag/value section: {ve}",
            }

        parsed_action = parse_action_expr(action.strip())
        parsed_action = translate_node(parsed_action, context=g_type.strip().lower())

        parsed: Dict[str, Any] = {
            "type": g_type.strip().lower(),
            "tag": tag.strip(),
            "value": value.strip(),
            "action": parsed_action,
            "soul_state": "trusted",
        }

        if parsed["type"] == "logic":
            parsed["tree"] = translate_node(logic_to_tree(action.strip()), context="logic")

        print(f"[✅ DEBUG] Parsed full CodexLang OK -> type={parsed['type']}, tag={parsed['tag']}")
        return parsed

    except Exception as e:
        print(f"[❌ DEBUG] Exception in parse_codexlang_string: {e}")
        traceback.print_exc()
        return {"type": "error", "soul_state": "violated", "expr": str(code_str), "message": str(e)}


def parse_action_expr(expr: str):
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
    op = expr[: expr.find("(")].strip()
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
def translate_to_instruction(parsed_glyph: Dict[str, Any], memory=None, trace_log=None):
    def eval_action(action):
        if isinstance(action, str):
            instr = get_instruction(action)
            result = instr.execute() if instr else action
            if trace_log is not None:
                trace_log.append({"stage": "execute", "op": action, "args": [], "result": result})
            return result

        elif isinstance(action, dict):
            # If this is a full instruction node, expect {"op":..., "args":[...]}
            if "op" in action:
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
                    trace_log.append({"stage": "execute", "op": op, "args": args, "result": result})
                return result

            # Otherwise treat as already-materialized payload
            if trace_log is not None:
                trace_log.append({"stage": "payload", "op": "dict", "result": action})
            return action

        elif hasattr(action, "evaluate"):
            result = action.evaluate()
            if trace_log is not None:
                trace_log.append({"stage": "evaluate", "op": type(action).__name__, "result": result})
            return result

        # ⚠️ Always log fallthrough
        if trace_log is not None:
            trace_log.append({"stage": "fallback", "op": str(action), "result": action})
        return action

    return eval_action(parsed_glyph.get("action"))


def run_codexlang_string(glyph_string: str, context: Optional[dict] = None):
    """
    Full CodexLang runtime: parse, dispatch, and execute symbolic glyph string.
    Uses CodexCore for actual logic execution.
    """
    from backend.modules.codex.codex_core import CodexCore  # ⬅ Delayed import

    codex = CodexCore()
    return codex.execute(glyph_string, context=context or {})


# Debug entry point
if __name__ == "__main__":
    test = "⟦ Logic | Test: A ∧ B -> ¬C ⟧"
    print("\n[🔍] Parsing:", test)
    parsed = parse_codexlang_string(test)
    print("Parsed AST:", parsed)

    translated = translate_to_instruction(parsed)
    print("Translated Instruction:", translated)

    output = run_codexlang_string(test, context={"source": "test"})
    print("CodexCore Output:", output)