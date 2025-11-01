# backend/modules/glyphos/codex_runtime_bridge.py
# 🔁 CodexLang ↔ GlyphOS Runtime Bridge

import time
from typing import Dict, Any
from backend.modules.websocket_manager import websocket_manager

from backend.modules.hexcore.memory_engine import MemoryEngine


async def execute_codex_for_glyph(glyph: str, context: Dict[str, Any]) -> Dict[str, Any]:
    from backend.modules.codex.codex_executor import codex_executor
    """
    Execute CodexLang logic for a given glyph symbol within GlyphRuntime.
    """
    try:
        start = time.time()
        result = codex_executor.execute_codexlang(glyph, context=context)
        duration = time.time() - start

        output = {
            "status": result.get("status", "unknown"),
            "output": result.get("output", {}),
            "duration": duration,
        }

        # Broadcast result to WebSocket clients
        await websocket_manager.broadcast({
            "event": "codex_runtime_result",
            "payload": {
                "glyph": glyph,
                "container": context.get("container_id", "unknown"),
                "coord": context.get("coord", ""),
                "status": output["status"],
                "duration": output["duration"],
            },
            "source": "codex_runtime_bridge",
            "timestamp": int(time.time())
        })

        # Store SQI feedback in memory
        MemoryEngine.store({
            "type": "codex_runtime_result",
            "timestamp": time.time(),
            "glyph": glyph,
            "context": context,
            "output": output,
        })

        print(f"[⚡ CodexBridge] Executed glyph '{glyph}' -> {output['status']} in {output['duration']:.4f}s")
        return output

    except Exception as e:
        print(f"[⚠️ CodexBridge] Execution failed for glyph '{glyph}': {e}")
        return {"status": "error", "error": str(e)}