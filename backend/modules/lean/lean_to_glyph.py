# File: backend/modules/lean/lean_to_glyph.py

import os
import re
import sys
import json
from typing import Dict, Any, List


def convert_lean_to_codexlang(path: str) -> Dict[str, Any]:
    """
    Load a .lean file and convert its theorem structures to CodexLang.
    Returns symbolic dict that can be embedded into a .dc container.
    """
    if not os.path.isfile(path) or not path.endswith(".lean"):
        raise ValueError("Invalid .lean file path")

    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    declarations = []

    # Improved pattern: optional parameter block, full type and body capture
    pattern = re.compile(
        r"^(theorem|lemma|example|def)\s+(\w+)"            # kind and name
        r"(?:\s*\((.*?)\))?\s*:\s*"                        # optional params
        r"(.*?)\s*:=\s*"                                   # type
        r"(.*?)(?=\n(?:theorem|lemma|example|def)|\Z)",    # body until next decl
        re.DOTALL | re.MULTILINE
    )

    matches = pattern.findall(content)

    for kind, name, params, typ, body in matches:
        decl = {
            "kind": kind,
            "name": name,
            "params": params.strip() if params else "",
            "type": typ.strip(),
            "body": body.strip()
        }
        decl["codexlang"] = lean_decl_to_codexlang(decl)
        decl["glyph_string"] = emit_codexlang_glyph(decl["codexlang"])
        declarations.append(decl)

    return {
        "source": path,
        "logic_type": "lean_math",
        "parsed_declarations": declarations
    }


def lean_decl_to_codexlang(decl: Dict[str, str]) -> Dict[str, Any]:
    """
    Convert a Lean declaration to a symbolic CodexLang glyph tree.
    """
    name = decl["name"]
    typ = decl["type"]

    # Replace core Lean logic operators with symbolic equivalents
    logic = (
        typ.replace("∀", "∀")
           .replace("∃", "∃")
           .replace("→", "→")
           .replace("↔", "↔")
           .replace("∧", "∧")
           .replace("∨", "∨")
           .replace("¬", "¬")
    )

    return {
        "symbol": "⟦ Theorem ⟧",
        "name": name,
        "logic": logic,
        "operator": "⊕",
        "args": [
            {"type": "CodexLang", "value": logic},
            {"type": "Proof", "value": decl["body"]}
        ]
    }


def emit_codexlang_glyph(node: Dict[str, Any]) -> str:
    """
    Emit a glyph string from a symbolic CodexLang node.
    Useful for runtime execution or embedding.
    """
    name = node.get("name", "unknown")
    logic = node.get("logic", "???")
    return f"⟦ Theorem | {name} : {logic} → Prove ⟧"


def lean_to_dc_container(path: str) -> Dict[str, Any]:
    """
    Convert a .lean file into a valid .dc container embedding symbolic logic.
    """
    parsed = convert_lean_to_codexlang(path)

    container = {
        "type": "dc_container",
        "id": f"lean::{os.path.basename(path)}",
        "metadata": {
            "origin": "lean_import",
            "source_path": parsed["source"],
            "logic_type": parsed["logic_type"]
        },
        "glyphs": [],
        "thought_tree": [],
        "symbolic_logic": [],
    }

    for decl in parsed["parsed_declarations"]:
        codexlang = decl["codexlang"]
        container["glyphs"].append("⟦ Theorem ⟧")
        container["thought_tree"].append({
            "name": decl["name"],
            "glyph": "⟦ Theorem ⟧",
            "node": codexlang
        })
        container["symbolic_logic"].append(codexlang)

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