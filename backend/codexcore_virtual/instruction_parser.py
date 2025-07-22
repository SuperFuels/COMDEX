# 📁 backend/codexcore_virtual/instruction_parser.py

from typing import List, Dict
import re

# Simple symbolic operator mapping
OPCODES = {
    "⊕": "⊕",     # Store
    "→": "→",     # Forward
    "⟲": "⟲",     # Reflect/Mutate
    "↔": "↔",     # Entangle
    "⧖": "⧖",     # Delay/Cost
}

def parse_codex_instructions(codex_str: str) -> List[Dict[str, any]]:
    """
    Parses a CodexLang glyph string into a list of symbolic CPU instructions.
    """
    instructions = []

    # Basic pattern for split: Symbol:Value → Target => ⟲(action)
    segments = re.split(r"\s*=>\s*", codex_str)

    for segment in segments:
        # Handle ⟲(Action) style
        match = re.match(r"(\S+)\((.*?)\)", segment)
        if match:
            op = match.group(1)
            arg = match.group(2)
            if op in OPCODES:
                instructions.append({"opcode": OPCODES[op], "args": [arg]})
            continue

        # Handle a → b
        if "→" in segment:
            parts = segment.split("→")
            if len(parts) == 2:
                source = parts[0].strip()
                dest = parts[1].strip()
                instructions.append({"opcode": "→", "args": [source, dest]})
            continue

        # Handle a ⊕ b
        if "⊕" in segment:
            parts = segment.split("⊕")
            if len(parts) == 2:
                key = parts[0].strip()
                value = parts[1].strip()
                instructions.append({"opcode": "⊕", "args": [key, value]})
            continue

        # Otherwise use print fallback
        instructions.append({"opcode": "print", "args": [segment.strip()]})

    return instructions