"""
Glyph -> Lean Translator
──────────────────────────────────────────────
Reconstructs Lean axioms or theorems from symbolic CodexLang expressions.

Uses glyph_bindings for operator mapping.
"""

import re
import json
import os
import sys
from typing import Dict, Any
from backend.modules.lean.imports.glyph_bindings import GLYPH_TO_LEAN


def glyph_to_lean_expr(expr: str) -> str:
    """Replace symbolic glyph operators with corresponding Lean identifiers."""
    lean_expr = expr
    for glyph, lean_name in GLYPH_TO_LEAN.items():
        lean_expr = lean_expr.replace(glyph, lean_name)
    return lean_expr


def glyph_to_lean_axiom(name: str, expr: str, kind: str = "axiom", use_prelude: bool = True) -> str:
    """Convert a symbolic expression into a Lean declaration string."""
    prelude = "import ./symatics_axioms_wave\n\n" if use_prelude else ""
    logic = glyph_to_lean_expr(expr)

    kind_map = {
        "Axiom": "axiom",
        "Theorem": "theorem",
        "Lemma": "lemma",
        "Def": "def",
        "Constant": "constant",
        "Example": "example",
        "Notation": "-- notation",
    }
    keyword = kind_map.get(kind.capitalize(), "axiom")
    return f"{prelude}{keyword} {name} : {logic}"


def build_lean_from_codex(container: Dict[str, Any], out_path: str) -> None:
    """Convert all symbolic_logic entries from a container into a Lean file."""
    decls = []
    for entry in container.get("symbolic_logic", []):
        name = entry.get("name", "unnamed")
        logic = entry.get("logic", "True")
        kind = entry.get("symbol", "Axiom").replace("⟦", "").replace("⟧", "").strip()
        decls.append(glyph_to_lean_axiom(name, logic, kind, use_prelude=False))

    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n\n".join(decls))

    print(f"[✅] Generated Lean file: {out_path}")


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser(description="Glyph -> Lean translator")
    ap.add_argument("glyph_path", help="Path to .glyph JSON or plaintext glyph file")
    ap.add_argument("--out", "-o", help="Write Lean output to file")
    args = ap.parse_args()

    if not os.path.exists(args.glyph_path):
        print(f"❌ Glyph file not found: {args.glyph_path}")
        sys.exit(1)

    print(f"[DEBUG] reading glyph file: {args.glyph_path}")
    text = open(args.glyph_path, "r", encoding="utf-8").read().strip()
    print(f"[DEBUG] first 200 chars: {repr(text[:200])}")

    try:
        container = json.loads(text)
        glyph_objects = container.get("symbolic_logic", [])
        print(f"[DEBUG] loaded {len(glyph_objects)} glyphs from JSON container")
    except json.JSONDecodeError:
        glyph_objects = []
        pattern = re.compile(r"⟦ (\w+) ⟧\s+(\w+).*?Logic:\s*(.+?)(?=\n*|$)", re.DOTALL)
        for m in pattern.finditer(text):
            kind, name, logic = m.groups()
            glyph_objects.append({"symbol": kind, "name": name, "logic": logic})

    lines = []

    # 🧩 Convert each glyph to Lean syntax
    for item in glyph_objects:
        name = item.get("name", "unnamed")
        raw_logic = item.get("logic", "True")
        kind = item.get("symbol", "Axiom").replace("⟦", "").replace("⟧", "").strip()

        # Try to extract parameters from logic if missing
        params = item.get("params", "").strip()
        if not params:
            m = re.match(r"\s*\(([^)]*)\)\s*:\s*", raw_logic)
            if m:
                params = f"({m.group(1)})"
                raw_logic = raw_logic[m.end():].strip()
        param_str = f" {params}" if params else ""

        # Split type and proof body
        if ":=" in raw_logic:
            logic_part, body_part = [s.strip() for s in raw_logic.split(":=", 1)]
        else:
            logic_part, body_part = raw_logic.strip(), ""

        keyword = kind.lower() if kind.lower() in {
            "theorem", "axiom", "lemma", "constant", "def", "example"
        } else "axiom"

        # Build the Lean declaration
        if body_part:
            line = f"{keyword} {name}{param_str} : {glyph_to_lean_expr(logic_part)} := {body_part}"
        else:
            line = f"{keyword} {name}{param_str} : {glyph_to_lean_expr(logic_part)}"

        lines.append(line)

    # ✅ Remove redundant "end Test" fragments
    output = "\n\n".join(lines)
    clean_output = re.sub(r"\bend\s+Test\b", "", output.strip(), flags=re.IGNORECASE)

    # ✅ Wrap in standard Lean boilerplate
    wrapped_output = (
        "import Init\nopen Nat\n\nnamespace Test\n\n"
        + clean_output.strip()
        + "\n\nend Test\n"
    )

    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(wrapped_output)
        print(f"[✅] Written to {args.out}")
    else:
        print("=== Reconstructing Lean ===")
        print(wrapped_output)