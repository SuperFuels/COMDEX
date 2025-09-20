# backend/modules/glyphnet/glyphnet_command.py

import re
import logging
from typing import Dict, Any, Optional, Callable

from backend.modules.glyphos.glyph_logic import parse_glyph_packet
from backend.modules.glyphos.glyph_executor import execute_glyph_logic
from backend.modules.hexcore.memory_engine import store_memory
from backend.modules.codex.codex_metrics import record_execution_metrics
from backend.modules.codex.codex_trace import CodexTrace

logger = logging.getLogger(__name__)

# Regex now captures command keyword + payload
COMMAND_PATTERN = re.compile(r"⌘\s*(\w+)\s*(⟦.+⟧)")

# Registry of command → handler
COMMAND_HANDLERS: Dict[str, Callable[[str, Optional[Dict[str, Any]]], Dict[str, Any]]] = {}

def register_command(name: str, handler: Callable[[str, Optional[Dict[str, Any]]], Dict[str, Any]]):
    COMMAND_HANDLERS[name.lower()] = handler
    logger.info(f"[GlyphNetCommand] Registered command: {name}")


def parse_symbolic_command(command_str: str) -> Optional[Dict[str, Any]]:
    """Parse command string into {command, payload} dict."""
    match = COMMAND_PATTERN.match(command_str.strip())
    if not match:
        return None
    return {
        "command": match.group(1).lower(),
        "symbolic": match.group(2),
    }


# --- Default handler: Execute ---
def handle_execute(payload: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    logic_tree = parse_glyph_packet({"glyph": "🧠", "symbolic": payload})
    result = execute_glyph_logic(logic_tree, context=context)
    store_memory(result.get("memory"))
    record_execution_metrics("glyphnet_command_execute", result)

    if context and "trace_id" in context:
        CodexTrace.log_event("symbolic_command_executed", {
            "trace_id": context["trace_id"],
            "command": "execute",
            "payload": payload,
            "result": result
        })
    return {"status": "ok", "result": result}


# Register core commands
register_command("execute", handle_execute)


def execute_symbolic_command(command_str: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Main entry: parses string, dispatches to handler."""
    parsed = parse_symbolic_command(command_str)
    if not parsed:
        return {"status": "error", "message": "Invalid symbolic command"}

    command = parsed["command"]
    payload = parsed["symbolic"]

    handler = COMMAND_HANDLERS.get(command)
    if not handler:
        return {"status": "error", "message": f"Unknown command: {command}"}

    return handler(payload, context)