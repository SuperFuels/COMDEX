# File: backend/modules/dna_chain/dna_utils.py

import os
from typing import Dict, Any

# --- DNA SWITCH REGISTRATION UTILITY ---

SWITCH_LINE_1 = "from backend.modules.dna_chain.switchboard import DNA_SWITCH"
SWITCH_LINE_2 = "DNA_SWITCH.register(__file__)  # Auto-injected"

def inject_dna_switch(file_path: str):
    """
    Injects the DNA switch registration lines into a Python file
    if they are not already present.
    """
    if not file_path.endswith(".py"):
        return

    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Cannot find file: {file_path}")

    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    if SWITCH_LINE_1 in content and SWITCH_LINE_2 in content:
        return  # Already injected

    new_content = f"{SWITCH_LINE_1}\n{SWITCH_LINE_2}\n\n{content}"
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(new_content)

# --- SYMBOLIC GLYPH DIFFING ---

def extract_glyph_diff(before: Dict[str, Any], after: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extracts a structural symbolic difference between two glyphs.

    Returns:
        {
            "before": <original glyph>,
            "after": <mutated glyph>,
            "diff": {
                "<key>": {
                    "from": <value_before>,
                    "to": <value_after>
                },
                ...
            }
        }
    """
    diff = {}
    keys = set(before.keys()) | set(after.keys())

    for key in keys:
        val_before = before.get(key)
        val_after = after.get(key)
        if val_before != val_after:
            diff[key] = {
                "from": val_before,
                "to": val_after
            }

    return {
        "before": before,
        "after": after,
        "diff": diff
    }