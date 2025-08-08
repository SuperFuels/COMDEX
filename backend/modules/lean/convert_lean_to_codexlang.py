import os
import re
from typing import List, Dict


def convert_lean_to_codexlang(lean_path: str) -> Dict[str, List[Dict[str, str]]]:
    """
    Converts a Lean file into CodexLang symbolic logic declarations.
    Returns:
        {
            "parsed_declarations": [
                {
                    "name": "my_theorem",
                    "codexlang": "...",
                    "glyph_string": "...",
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

    declarations = []
    current_decl = []
    name = None
    start_line = 0

    def flush_declaration():
        nonlocal declarations, current_decl, name, start_line
        if not current_decl or not name:
            return

        raw_body = "".join(current_decl).strip()

        codexlang_block = f"""
⟦ Theorem ⟧ {{
  name: "{name}",
  body: """
        codexlang_block += '"""' + raw_body + '"""' + "\n}"

        glyph_string = f"⟦ Theorem ⟧ {name}"

        declarations.append({
            "name": name,
            "codexlang": codexlang_block.strip(),
            "glyph_string": glyph_string,
            "body": raw_body,
            "line": start_line
        })

        current_decl = []
        name = None
        start_line = 0

    for i, line in enumerate(lines):
        stripped = line.strip()

        # Detect start of theorem/lemma/proof
        match = re.match(r"^(theorem|lemma)\s+([a-zA-Z0-9_']+)\s*:.*", stripped)
        if match:
            flush_declaration()
            name = match.group(2)
            start_line = i + 1
            current_decl.append(line)
        elif name:
            # Continue accumulating proof block
            current_decl.append(line)

    flush_declaration()  # Final flush

    return {
        "parsed_declarations": declarations
    }