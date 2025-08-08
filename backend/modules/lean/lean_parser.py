# File: backend/modules/lean/lean_parser.py

import re
from typing import List, Dict

THEOREM_PATTERN = re.compile(
    r"theorem\s+([a-zA-Z0-9_']+)\s*(:.*?)?:\s*(.*?)\s*:=\s*(.+)", re.DOTALL
)

def parse_lean_file(lean_text: str) -> List[Dict[str, str]]:
    """
    Parses raw Lean source code into a list of symbolic theorem dicts.

    Returns:
        List[Dict] — each dict includes:
            • symbol: "⟦ Theorem ⟧"
            • name: theorem name
            • logic: raw CodexLang-style logic
            • body: proof content (if any)
    """
    theorems = []
    for match in THEOREM_PATTERN.finditer(lean_text):
        name = match.group(1).strip()
        _type_annotation = match.group(2)
        logic = match.group(3).strip()
        body = match.group(4).strip()

        theorems.append({
            "symbol": "⟦ Theorem ⟧",
            "name": name,
            "logic": logic,
            "body": body
        })

    return theorems


def parse_single_theorem(block: str) -> Dict[str, str]:
    """
    Parses a single theorem block (string) into symbolic fields.
    Useful for partial parsing or CLI testing.
    """
    match = THEOREM_PATTERN.search(block)
    if not match:
        return {}

    return {
        "symbol": "⟦ Theorem ⟧",
        "name": match.group(1).strip(),
        "logic": match.group(3).strip(),
        "body": match.group(4).strip()
    }