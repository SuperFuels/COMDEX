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
    "axiom":   "⟦ Axiom ⟧",
    "constant": "⟦ Constant ⟧",
}


def convert_lean_to_codexlang(path: str) -> Dict[str, Any]:
    """
    Parse a .lean file and convert declarations to CodexLang + glyph trees.
    Returns a dict that downstream can embed into any container.
    """
    if not os.path.isfile(path):
        raise ValueError(f"Invalid .lean file path: {path}")
    if not path.endswith(".lean"):
        raise ValueError(f"Expected a .lean file, got: {path}")

    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    # normalize line endings
    content = content.replace("\r\n", "\n").replace("\r", "\n")
    # drop block comments
    content = re.sub(r"/-\*?[\s\S]*?\*/-|/-[\s\S]*?-/", "", content)
    # drop single-line comments
    content = re.sub(r"^[ \t]*--.*?$", "", content, flags=re.MULTILINE)
    # drop attributes like @[simp]
    content = re.sub(r"(?m)^\s*@\[[^\]]*\]\s*\n", "", content)

    declarations: List[Dict[str, Any]] = []

    # Pattern now supports optional := body (for axiom/constant/defs without proof)
    pattern = re.compile(
        r"""(?mx)
        ^\s*
        (theorem|lemma|example|def|axiom|constant)  # kind
        \s+([A-Za-z_][\w']*)                        # name
        (?:\s*\((.*?)\))?                           # optional params
        \s*:\s*
        (.*?)                                       # type
        (?:\s*:=\s*(.*?)(?=                         # optional body
             ^\s*(?:theorem|lemma|example|def|axiom|constant)\b
            | \Z
        ))?
        """,
        re.DOTALL,
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
            "body": (body or "").strip(),
        }

        # Build CodexLang node
        decl["codexlang"] = lean_decl_to_codexlang(decl)

        # Normalize (soft) for nice display
        try:
            decl["codexlang"]["normalized"] = CodexLangRewriter.simplify(
                decl["codexlang"]["logic"], mode="soft"
            )
        except TypeError:
            decl["codexlang"]["normalized"] = CodexLangRewriter.simplify(
                decl["codexlang"]["logic"]
            )

        # Glyph tree
        decl["glyph_tree"] = build_glyph_tree(decl)

        # Registry hook
        try:
            symbolic_registry.register(decl["name"], decl["glyph_tree"])  # type: ignore[attr-defined]
        except Exception:
            pass

        # Human preview
        decl["preview"] = emit_codexlang_glyph(decl["codexlang"], glyph_symbol)

        # Params + deps
        decl["parsed_params"] = parse_params(decl["params"])
        decl["depends_on"] = detect_dependencies(decl["body"])

        declarations.append(decl)

    if not declarations:
        raise ValueError(
            f"No Lean declarations found in {path}. "
            "Expected lines like: 'theorem name : type := proof' or 'axiom name : type'"
        )

    return {
        "source": os.path.normpath(path),
        "logic_type": "lean_math",
        "parsed_declarations": declarations,
    }


def parse_params(param_str: str) -> List[str]:
    if not param_str:
        return []
    if "," in param_str:
        parts = [p.strip() for p in param_str.split(",")]
    else:
        parts = [param_str.strip()]
    return [p for p in parts if p]


def detect_dependencies(body: str) -> List[str]:
    if not body:
        return []
    b = re.sub(r"/-.*?-/", "", body, flags=re.DOTALL)
    b = re.sub(r"^[ \t]*--.*?$", "", b, flags=re.MULTILINE)

    hits: List[str] = []
    hits += re.findall(r"\b(?:[A-Z]?[a-zA-Z_]\w*(?:\.[A-Za-z_]\w+)*)\b", b)
    hits += re.findall(r"\b\w+_(?:lemma|thm|proof)\b", b)

    seen, out = set(), []
    for h in hits:
        if h not in seen and len(h) > 2:
            seen.add(h)
            out.append(h)
    return out[:64]


def lean_decl_to_codexlang(decl: Dict[str, str]) -> Dict[str, Any]:
    name = decl["name"]
    typ = decl["type"]
    glyph_symbol = decl.get("glyph_symbol", "⟦ Theorem ⟧")

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
            {
                "type": "Definition" if glyph_symbol == "⟦ Definition ⟧" else "Proof",
                "value": decl.get("body", ""),
            },
        ],
    }


def build_glyph_tree(decl: Dict[str, Any]) -> Dict[str, Any]:
    node = decl["codexlang"]
    if _HAS_LOGIC_GLYPH and hasattr(LogicGlyph, "from_codexlang"):
        try:
            lg = LogicGlyph.from_codexlang(node)  # type: ignore[attr-defined]
            return lg.to_dict()
        except Exception:
            pass

    return {
        "type": "LogicGlyph",
        "name": node.get("name"),
        "logic": node.get("logic"),
        "operator": node.get("operator"),
        "args": node.get("args", []),
    }


def emit_codexlang_glyph(node: Dict[str, Any], glyph_symbol: str = "⟦ Theorem ⟧") -> str:
    name = node.get("name", "unknown")
    logic = node.get("logic", "???")
    if glyph_symbol == "⟦ Definition ⟧":
        label = "Define"
    elif glyph_symbol in ("⟦ Axiom ⟧", "⟦ Constant ⟧"):
        label = "Assume"
    else:
        label = "Prove"
    return f"{glyph_symbol} | {name} : {logic} → {label} ⟧"


def lean_to_dc_container(path: str) -> Dict[str, Any]:
    parsed = convert_lean_to_codexlang(path)

    container: Dict[str, Any] = {
        "type": "dc_container",
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

        container["glyphs"].append(emit_codexlang_glyph(decl["codexlang"], gsym))

        container["thought_tree"].append({
            "name": decl["name"],
            "glyph": gsym,
            "node": decl["glyph_tree"],
        })

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