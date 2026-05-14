# backend/modules/glyphos/glyph_compiler.py

import hashlib
from typing import Dict, List

# ✅ Optional: For logic evaluation compression
import json

# Simple opcode map
OPCODES: Dict[str, str] = {
    "teleport": "0x01",
    "write_cube": "0x02",
    "run_mutation": "0x03",
    "log": "0x04",
    "logic_eval": "0x05"  # ✅ New logic evaluation opcode
}

REVERSE_OPCODES: Dict[str, str] = {v: k for k, v in OPCODES.items()}


def compile_glyph(parsed_glyph: dict) -> str:
    """
    Converts a glyph dictionary into a compressed bytecode string.
    """
    action = parsed_glyph.get("action", "unknown")

    # ✅ Support logic trees from structured glyphs
    if parsed_glyph.get("type", "").lower() == "logic" and "tree" in parsed_glyph:
        action = "logic_eval"
        tree = parsed_glyph["tree"]
        try:
            encoded_tree = json.dumps(tree, separators=(",", ":"))
        except Exception:
            encoded_tree = "invalid_tree"
        bytecode = f"{OPCODES[action]}|{encoded_tree}"
        checksum = hashlib.md5(bytecode.encode()).hexdigest()[:8]
        return f"{bytecode}|#{checksum}"

    opcode = OPCODES.get(action, "0xFF")
    operands: List[str] = []

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
        operands.extend([module, reason])

    elif action == "log":
        msg = parsed_glyph.get("message", "")
        operands.append(msg)

    # Compress and add checksum
    bytecode = f"{opcode}|{'|'.join(operands)}"
    checksum = hashlib.md5(bytecode.encode()).hexdigest()[:8]
    return f"{bytecode}|#{checksum}"


def decompile_glyph(bytecode: str) -> dict:
    """
    Decompresses bytecode back into a glyph action dictionary.
    Validates checksum for integrity.
    """
    try:
        parts = bytecode.split("|")
        if len(parts) < 2:
            raise ValueError("Malformed bytecode")

        opcode = parts[0]
        data = parts[1:-1]
        checksum = parts[-1].replace("#", "")

        # Verify checksum
        raw = "|".join(parts[:-1])
        verify = hashlib.md5(raw.encode()).hexdigest()[:8]
        if verify != checksum:
            raise ValueError("❌ Bytecode integrity check failed.")

        action = REVERSE_OPCODES.get(opcode, "unknown")
        glyph = {"action": action}

        if action == "teleport":
            glyph["target"] = data[0]

        elif action == "write_cube" and len(data) >= 4:
            glyph["target"] = list(map(int, data[:3]))
            glyph["value"] = data[3]

        elif action == "run_mutation":
            glyph["module"] = data[0]
            glyph["reason"] = data[1]

        elif action == "log":
            glyph["message"] = data[0]

        elif action == "logic_eval":
            try:
                glyph["tree"] = json.loads(data[0])
                glyph["type"] = "logic"
            except Exception as e:
                glyph["tree"] = f"Failed to parse logic: {e}"
                glyph["type"] = "logic"

        return glyph

    except Exception as e:
        print(f"[⚠️] Failed to decompile glyph: {e}")
        return {"action": "unknown", "error": str(e)}