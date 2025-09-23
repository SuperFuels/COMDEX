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
                    "codexlang": {
                        "logic": "...",
                        "normalized": "...",
                        "explanation": "...",
                    },
                    "codexlang_string": "...",   # legacy compat shim
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

    def flush_declaration():
        nonlocal declarations, current_decl, name, start_line
        if not current_decl or not name:
            return

        raw_body = "".join(current_decl).strip()

        codexlang_block = f"""
⟦ Theorem ⟧ {{
  name: "{name}",
  body: \"\"\"{raw_body}\"\"\"
}}
""".strip()

        glyph_symbol = "⟦ Theorem ⟧"
        glyph_string = f"{glyph_symbol} {name}"

        declarations.append({
            "name": name,
            "codexlang": {
                "logic": codexlang_block,
                "normalized": codexlang_block,
                "explanation": "Auto-converted from Lean source"
            },
            # 🔧 Legacy shim: keep string version for old consumers
            "codexlang_string": codexlang_block,
            "glyph_symbol": glyph_symbol,
            "glyph_string": glyph_string,
            "glyph_tree": {},   # placeholder for AST-like expansion
            "body": raw_body,
            "line": start_line,
        })

        current_decl = []
        name = None
        start_line = 0

    for i, line in enumerate(lines):
        stripped = line.strip()

        # Detect theorem/lemma start
        match = re.match(r"^(theorem|lemma)\s+([a-zA-Z0-9_']+)\s*:.*", stripped)
        if match:
            flush_declaration()
            name = match.group(2)
            start_line = i + 1
            current_decl.append(line)
        elif name:
            # Accumulate proof lines
            current_decl.append(line)

    flush_declaration()

    return {"parsed_declarations": declarations}