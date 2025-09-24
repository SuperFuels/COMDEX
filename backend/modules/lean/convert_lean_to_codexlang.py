import os
import re
from typing import List, Dict, Any


def convert_lean_to_codexlang(lean_path: str) -> Dict[str, List[Dict[str, Any]]]:
    """
    Converts a Lean file into CodexLang symbolic logic declarations.

    Returns:
        {
            "parsed_declarations": [
                {
                    "name": "my_theorem",
                    "logic": "(A ⊕ B) → (B ⊕ A)",
                    "logic_raw": "...",
                    "codexlang": {...},
                    "glyph_symbol": "...",
                    "glyph_string": "...",
                    "glyph_tree": {},
                    "body": "...",
                    "line": 42
                },
                ...
            ]
        }
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

        # Fallback if no logic was parsed
        logic_str = logic or "True"

        codexlang_block = f"{logic_str}"

        declarations.append({
            "name": name,
            "logic": logic_str,
            "logic_raw": logic_str,
            "codexlang": {
                "logic": logic_str,
                "normalized": logic_str,
                "explanation": "Auto-converted from Lean source"
            },
            "codexlang_string": logic_str,  # legacy shim
            "glyph_symbol": glyph_symbol,
            "glyph_string": f"{glyph_symbol} {name}",
            "glyph_tree": {},   # placeholder for AST-like expansion
            "body": raw_body,
            "line": start_line,
        })

        current_decl = []
        name = None
        start_line = 0
        logic = None
        glyph_symbol = "⟦ Theorem ⟧"

    for i, line in enumerate(lines):
        stripped = line.strip()

        # Match theorem/lemma/axiom
        match = re.match(r"^(theorem|lemma|axiom)\s+([a-zA-Z0-9_']+)\s*:\s*(.*)", stripped)
        if match:
            flush_declaration()
            kind, nm, logic_part = match.groups()
            name = nm
            start_line = i + 1
            logic = logic_part.strip()
            glyph_symbol = "⟦ Axiom ⟧" if kind == "axiom" else "⟦ Theorem ⟧"
            current_decl.append(line)
        elif name:
            # Continue body lines (proof, etc.)
            current_decl.append(line)

    flush_declaration()

    return {"parsed_declarations": declarations}