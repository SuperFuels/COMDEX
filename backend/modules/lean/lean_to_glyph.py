# File: backend/modules/lean/lean_to_glyph.py

import os
import re
import sys
import json
from typing import Dict, Any, List

# ---------------------------------------------------------------------
# Resilient imports (graceful fallbacks so this file never hard-crashes)
# ---------------------------------------------------------------------

# CodexLangRewriter (soft simplifier)
try:
    from backend.modules.codex.codexlang_rewriter import CodexLangRewriter  # type: ignore
except Exception:
    class CodexLangRewriter:  # minimal stub
        @classmethod
        def simplify(cls, expr: str, mode: str = "soft") -> str:
            return expr

# LogicGlyph (optional; we can fall back to dict trees)
try:
    # Prefer symbolic_engine location you confirmed exists
    from backend.modules.symbolic_engine.symbolic_kernels.logic_glyphs import LogicGlyph  # type: ignore
    _HAS_LOGIC_GLYPH = True
except Exception:
    LogicGlyph = None  # type: ignore
    _HAS_LOGIC_GLYPH = False

# Symbolic registry (optional; fall back to no-op)
try:
    from backend.modules.codex.symbolic_registry import symbolic_registry  # type: ignore
except Exception:
    class _NoOpRegistry:
        def register(self, *args, **kwargs):
            return None
    symbolic_registry = _NoOpRegistry()  # type: ignore


# ---------------------------------------
# Glyph kind mapping (Theorem/Lemma/etc.)
# ---------------------------------------
KIND_TO_GLYPH = {
    "theorem": "⟦ Theorem ⟧",
    "lemma":   "⟦ Lemma ⟧",
    "example": "⟦ Example ⟧",
    "def":     "⟦ Definition ⟧",
}


def convert_lean_to_codexlang(path: str) -> Dict[str, Any]:
    """
    Parse a .lean file and convert declarations to CodexLang + glyph trees.
    Returns a dict that downstream can embed into any container.
    """
    if not os.path.isfile(path) or not path.endswith(".lean"):
        raise ValueError("Invalid .lean file path")

    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    declarations: List[Dict[str, Any]] = []

    # theorems / lemmas / examples / defs:
    #   name (optional params) : type := body
    pattern = re.compile(
        r"^(theorem|lemma|example|def)\s+(\w+)"            # kind and name
        r"(?:\s*\((.*?)\))?\s*:\s*"                        # optional params
        r"(.*?)\s*:=\s*"                                   # type
        r"(.*?)(?=\n(?:theorem|lemma|example|def)\b|\Z)",  # body until next decl
        re.DOTALL | re.MULTILINE
    )

    matches = pattern.findall(content)

    for kind, name, params, typ, body in matches:
        glyph_symbol = KIND_TO_GLYPH.get(kind, "⟦ Theorem ⟧")
        decl: Dict[str, Any] = {
            "kind": kind,
            "glyph_symbol": glyph_symbol,
            "name": name,
            "params": params.strip() if params else "",
            "type": typ.strip(),
            "body": body.strip(),
        }

        # Build CodexLang node
        decl["codexlang"] = lean_decl_to_codexlang(decl)

        # Normalize logic (soft mode; keep human readability)
        try:
            decl["codexlang"]["normalized"] = CodexLangRewriter.simplify(
                decl["codexlang"]["logic"], mode="soft"
            )
        except TypeError:
            # Older rewriter w/o mode argument
            decl["codexlang"]["normalized"] = CodexLangRewriter.simplify(
                decl["codexlang"]["logic"]
            )

        # Build LogicGlyph tree or fallback dict
        decl["glyph_tree"] = build_glyph_tree(decl)

        # Registry hook (no-op if registry unavailable)
        try:
            symbolic_registry.register(decl["name"], decl["glyph_tree"])
        except Exception:
            pass

        # Preview string (Prove vs Define)
        decl["preview"] = emit_codexlang_glyph(decl["codexlang"], glyph_symbol)

        # Params + dependency scan
        decl["parsed_params"] = parse_params(decl["params"])
        decl["depends_on"] = detect_dependencies(decl["body"])

        declarations.append(decl)

    return {
        "source": path,
        "logic_type": "lean_math",
        "parsed_declarations": declarations,
    }


def parse_params(param_str: str) -> List[str]:
    """
    Very light param splitter: "(a b : Nat)" is usually parsed by Lean;
    here we just keep a simple comma/space split for display.
    """
    if not param_str:
        return []
    # Split by commas first; if none, split by spaces where that makes sense
    parts: List[str] = []
    if "," in param_str:
        parts = [p.strip() for p in param_str.split(",")]
    else:
        # keep groups like "a b : Nat" together
        parts = [param_str.strip()]
    return [p for p in parts if p]


def detect_dependencies(body: str) -> List[str]:
    """
    Heuristic: detect references to lemmas/theorems in the body.
    You can strengthen this later with a Lean AST export.
    """
    # common Lean core name patterns (e.g., nat.add_zero, Nat.mul_one)
    hits = re.findall(r"\b([A-Za-z_][\w\.]*\.[A-Za-z_]\w*)\b", body)
    # also catch "_lemma", "_thm", "_proof" names
    hits += re.findall(r"\b\w+_(?:lemma|thm|proof)\b", body)
    # de-dupe preserving order
    seen, deps = set(), []
    for h in hits:
        if h not in seen:
            seen.add(h)
            deps.append(h)
    return deps


def lean_decl_to_codexlang(decl: Dict[str, str]) -> Dict[str, Any]:
    """
    Translate the Lean declaration header into a CodexLang node.
    For 'def', we emit ⟦ Definition ⟧ and mark the body as Definition.
    """
    name = decl["name"]
    typ = decl["type"]
    glyph_symbol = decl.get("glyph_symbol", "⟦ Theorem ⟧")

    # Preserve core logical operators/symbols
    logic = (
        typ.replace("∀", "∀")
           .replace("∃", "∃")
           .replace("→", "→")
           .replace("↔", "↔")
           .replace("∧", "∧")
           .replace("∨", "∨")
           .replace("¬", "¬")
           .replace("⊤", "⊤")
           .replace("⊥", "⊥")
    )

    return {
        "symbol": glyph_symbol,
        "name": name,
        "logic": logic,
        "operator": "⊕",
        "args": [
            {"type": "CodexLang", "value": logic},
            {"type": "Definition" if glyph_symbol == "⟦ Definition ⟧" else "Proof", "value": decl["body"]},
        ],
    }


def build_glyph_tree(decl: Dict[str, Any]) -> Dict[str, Any]:
    """
    Create a LogicGlyph tree if the class is available; otherwise a dict snapshot.
    """
    node = decl["codexlang"]
    if _HAS_LOGIC_GLYPH and hasattr(LogicGlyph, "from_codexlang"):
        try:
            lg = LogicGlyph.from_codexlang(node)  # type: ignore[attr-defined]
            return lg.to_dict()
        except Exception:
            pass

    # Fallback: mirror the CodexLang node as a simple structured dict
    return {
        "type": "LogicGlyph",
        "name": node.get("name"),
        "logic": node.get("logic"),
        "operator": node.get("operator"),
        "args": node.get("args", []),
    }


def emit_codexlang_glyph(node: Dict[str, Any], glyph_symbol: str = "⟦ Theorem ⟧") -> str:
    """
    Human-readable preview for HUDs and logs.
    The label is 'Prove' for theorems/lemmas/examples and 'Define' for definitions.
    """
    name = node.get("name", "unknown")
    logic = node.get("logic", "???")
    label = "Define" if glyph_symbol == "⟦ Definition ⟧" else "Prove"
    return f"{glyph_symbol} | {name} : {logic} → {label} ⟧"


def lean_to_dc_container(path: str) -> Dict[str, Any]:
    """
    Convenience: build a DC-style container directly from a Lean file.
    (Other container shapes should be handled by lean_exporter or injectors.)
    """
    parsed = convert_lean_to_codexlang(path)

    container: Dict[str, Any] = {
        "type": "dc_container",  # Universal symbolic container ID can override this downstream
        "id": f"lean::{os.path.basename(path)}",
        "metadata": {
            "origin": "lean_import",
            "source_path": parsed["source"],
            "logic_type": parsed["logic_type"],
        },
        "glyphs": [],
        "thought_tree": [],
        "symbolic_logic": [],
        "previews": [],
        "dependencies": [],
    }

    for decl in parsed["parsed_declarations"]:
        gsym = decl.get("glyph_symbol", "⟦ Theorem ⟧")

        # Human-readable glyph list
        container["glyphs"].append(emit_codexlang_glyph(decl["codexlang"], gsym))

        # Thought tree
        container["thought_tree"].append({
            "name": decl["name"],
            "glyph": gsym,
            "node": decl["glyph_tree"],
        })

        # Symbolic logic entry with full payload
        container["symbolic_logic"].append({
            "name": decl["name"],
            "symbol": gsym,
            "logic": decl["codexlang"]["logic"],
            "codexlang": decl["codexlang"],
            "glyph_tree": decl["glyph_tree"],
            "source": path,
            "body": decl.get("body", ""),
        })

        container["previews"].append(decl["preview"])
        container["dependencies"].append({
            "theorem": decl["name"],
            "depends_on": decl["depends_on"],
        })

    return container


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python lean_to_glyph.py <path_to_lean_file>")
        sys.exit(1)

    input_path = sys.argv[1]
    try:
        dc_container = lean_to_dc_container(input_path)
        print(json.dumps(dc_container, indent=2, ensure_ascii=False))
    except Exception as e:
        print(f"[❌] Error: {e}", file=sys.stderr)
        sys.exit(1)