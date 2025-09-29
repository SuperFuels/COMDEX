# File: backend/modules/lean/convert_lean_to_codexlang.py
"""
Lean → CodexLang Bridge
────────────────────────
Parses Lean theorems/axioms into CodexLang AST ({op, args}) form,
normalized through Symatics rewriter.

Uses symatics.adapter to avoid direct reliance on old Atom/Interf classes.
"""

import os
import re
import math
from typing import List, Dict, Any

from backend.symatics import adapter, rewriter as R


def _strip_comments(s: str) -> str:
    """Remove Lean-style comments (starting with `--`) from a line or block."""
    return re.sub(r"--.*$", "", s).strip()


# -----------------------
# Minimal Lean → Codex AST
# -----------------------

def lean_to_ast(logic: str) -> Dict[str, Any]:
    """
    Very minimal parser: supports patterns like
      (A ⋈[φ] B), ⊥, atoms A/B/C.
    Produces CodexLang AST nodes.
    """
    logic = logic.strip()

    # Bottom
    if logic == "⊥":
        return {"op": "logic:⊥", "args": []}

    # Atom
    if re.fullmatch(r"[A-Z]", logic):
        return {"op": "lit", "value": logic}

    # Interference connective
    m = re.match(r"^\((\w+)\s*⋈\[(.*?)\]\s*(\w+)\)$", logic)
    if m:
        left, phi_str, right = m.groups()
        try:
            # Normalize Lean's phase symbols into numeric values
            if phi_str in ("π", "pi_phase"):
                φ = math.pi
            elif phi_str in ("0", "zero_phase"):
                φ = 0.0
            else:
                φ = float(phi_str)
        except Exception:
            φ = 0.0
        return {
            "op": "interf:⋈",
            "phase": φ,
            "args": [
                {"op": "lit", "value": left},
                {"op": "lit", "value": right},
            ],
        }

    # Fallback: atom-like literal
    return {"op": "lit", "value": logic}


# -----------------------
# Main conversion function
# -----------------------

def convert_lean_to_codexlang(lean_path: str) -> Dict[str, List[Dict[str, Any]]]:
    """
    Converts a Lean file into CodexLang symbolic logic declarations.
    Returns { "parsed_declarations": [ {name, logic, ...}, ... ] }
    """
    if not os.path.isfile(lean_path):
        raise FileNotFoundError(f"Lean file not found: {lean_path}")

    with open(lean_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    declarations: List[Dict[str, Any]] = []
    current_decl: List[str] = []
    name: str | None = None
    start_line: int = 0
    logic: str | None = None
    glyph_symbol: str = "⟦ Theorem ⟧"

    def flush_declaration():
        nonlocal declarations, current_decl, name, start_line, logic, glyph_symbol
        if not current_decl or not name:
            return

        raw_body = "".join(current_decl).strip()
        logic_str = _strip_comments(logic or "True")

        # Build Codex AST + normalize through Symatics
        try:
            codex_ast = lean_to_ast(logic_str)
            sym_expr = adapter.codex_ast_to_sym(codex_ast)
            normalized_expr = R.normalize(sym_expr)
            glyph_tree = adapter.sym_to_codex_ast(normalized_expr)
            normalized_logic = str(glyph_tree)
        except Exception:
            glyph_tree = {}
            normalized_logic = logic_str

        declarations.append({
            "name": name,
            "logic": normalized_logic,        # ✅ normalized logic (stringified AST)
            "logic_raw": logic_str,           # keep raw for traceability
            "codexlang": {
                "logic": logic_str,
                "normalized": normalized_logic,
                "explanation": "Auto-converted + normalized from Lean source"
            },
            "codexlang_string": normalized_logic,
            "glyph_symbol": glyph_symbol,
            "glyph_string": f"{glyph_symbol} {name}",
            "glyph_tree": glyph_tree,
            "body": raw_body,
            "line": start_line,
        })

        # reset state
        current_decl = []
        name = None
        start_line = 0
        logic = None
        glyph_symbol = "⟦ Theorem ⟧"

    for i, line in enumerate(lines):
        stripped = line.strip()

        # --- New declaration line ---
        match = re.match(r"^(theorem|lemma|axiom)\s+([a-zA-Z0-9_']+)\s*:\s*(.+)$", stripped)
        if match:
            flush_declaration()
            kind, nm, logic_part = match.groups()
            name = nm
            start_line = i + 1
            logic = _strip_comments(logic_part)
            glyph_symbol = "⟦ Axiom ⟧" if kind == "axiom" else "⟦ Theorem ⟧"
            current_decl = [line]
        elif name:
            # --- Continuation of current declaration ---
            current_decl.append(line)
            logic = (logic or "") + " " + _strip_comments(stripped)

    flush_declaration()
    return {"parsed_declarations": declarations}

if __name__ == "__main__":
    import json
    # pick one of your Lean sources:
    lean_file = "backend/modules/lean/symatics_axioms.lean"

    result = convert_lean_to_codexlang(lean_file)
    print(json.dumps(result, indent=2, ensure_ascii=False))