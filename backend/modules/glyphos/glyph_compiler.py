# glyph_compiler.py

import json
import hashlib

# Simple opcode map
OPCODES = {
    "teleport": "0x01",
    "write_cube": "0x02",
    "run_mutation": "0x03",
    "log": "0x04"
}

def compile_glyph(parsed_glyph: dict) -> str:
    """
    Converts a glyph into a compressed instruction string.
    """
    action = parsed_glyph.get("action")
    opcode = OPCODES.get(action, "0xFF")  # Unknown

    operands = []

    if action == "teleport":
        destination = parsed_glyph.get("target", "unknown")
        operands.append(destination)

    elif action == "write_cube":
        coords = parsed_glyph.get("target", [0, 0, 0])
        glyph = parsed_glyph.get("value", "⛓️")
        operands.extend(map(str, coords))
        operands.append(glyph)

    elif action == "run_mutation":
        module = parsed_glyph.get("module", "unknown")
        reason = parsed_glyph.get("reason", "none")
        operands.append(module)
        operands.append(reason)

    elif action == "log":
        msg = parsed_glyph.get("message", "")
        operands.append(msg)

    # Compress into a single string
    bytecode = f"{opcode}|{'|'.join(operands)}"

    # Optional checksum for data integrity
    checksum = hashlib.md5(bytecode.encode()).hexdigest()[:8]
    return f"{bytecode}|#{checksum}"

def decompile_glyph(bytecode: str) -> dict:
    """
    Converts bytecode back into a glyph dictionary.
    """
    parts = bytecode.split("|")
    opcode = parts[0]
    data = parts[1:-1]
    checksum = parts[-1].replace("#", "")

    # Verify checksum
    verify = hashlib.md5("|".join(parts[:-1]).encode()).hexdigest()[:8]
    if verify != checksum:
        raise ValueError("❌ Bytecode integrity check failed.")

    action = {v: k for k, v in OPCODES.items()}.get(opcode, "unknown")
    glyph = {"action": action}

    if action == "teleport":
        glyph["target"] = data[0]

    elif action == "write_cube":
        glyph["target"] = list(map(int, data[:3]))
        glyph["value"] = data[3]

    elif action == "run_mutation":
        glyph["module"] = data[0]
        glyph["reason"] = data[1]

    elif action == "log":
        glyph["message"] = data[0]

    return glyph