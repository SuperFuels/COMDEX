# File: backend/modules/glyphnet/glyphnet_command.py

import re
from typing import Dict, Any, Optional
from ..glyphos.glyph_logic import parse_glyph_packet
from ..glyphos.glyph_executor import execute_glyph_logic
from ..hexcore.memory_engine import store_memory
from ..codex.codex_metrics import record_execution_metrics
from ..codex.codex_trace import CodexTrace

COMMAND_PATTERN = re.compile(r"⌘\s*Execute\s*(⟦.+⟧)")

def parse_symbolic_command(command_str: str) -> Optional[Dict[str, Any]]:
    """
    Parses a symbolic terminal command and extracts a glyph logic payload.
    Supports commands like:
        ⌘ Execute ⟦ Glyph → Logic ⟧
    """
    match = COMMAND_PATTERN.match(command_str.strip())
    if not match:
        return None

    symbolic_logic = match.group(1)
    return {
        "glyph": "🧠",
        "symbolic": symbolic_logic
    }

def execute_symbolic_command(command_str: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Executes a symbolic command string as glyph logic.
    """
    parsed = parse_symbolic_command(command_str)
    if not parsed:
        return {"status": "error", "message": "Invalid symbolic command"}

    logic_tree = parse_glyph_packet(parsed)
    result = execute_glyph_logic(logic_tree, context=context)

    store_memory(result.get("memory"))
    record_execution_metrics("glyphnet_command", result)

    trace_id = context.get("trace_id") if context else None
    if trace_id:
        CodexTrace.log_event("symbolic_command_executed", {
            "trace_id": trace_id,
            "command": command_str,
            "result": result
        })

    return {"status": "ok", "result": result}