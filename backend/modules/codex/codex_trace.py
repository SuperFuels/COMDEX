# 📁 backend/modules/codex/codex_trace.py

import time
import json
from typing import List, Dict, Optional

class CodexTrace:
    def __init__(self):
        self.entries: List[Dict] = []

    def record(self, glyph: str, context: dict, result: str, source: str = "benchmark"):
        self.entries.append({
            "timestamp": time.time(),
            "glyph": glyph,
            "context": context,
            "result": result,
            "source": source
        })

    def get_trace(self) -> List[Dict]:
        return self.entries

    def clear(self):
        self.entries = []

    def to_json(self) -> str:
        return json.dumps(self.entries, indent=2)

    def get_latest_trace(self, container_id: Optional[str] = None) -> Optional[Dict]:
        """
        Retrieve the most recent trace entry for a given container_id (if available).
        """
        for entry in reversed(self.entries):
            ctx = entry.get("context", {})
            if container_id is None or ctx.get("container_id") == container_id:
                return {
                    "ghx_id": ctx.get("ghx_id"),
                    "path": ctx.get("collapse_trace"),
                    "container_id": ctx.get("container_id"),
                    "timestamp": entry.get("timestamp"),
                    "glyph": entry.get("glyph"),
                    "result": entry.get("result"),
                    "source": entry.get("source"),
                }
        return None

# ✅ Global singleton
_global_trace = CodexTrace()

def log_codex_trace(glyph: str, context: dict, result: str, source: str = "benchmark"):
    _global_trace.record(glyph, context, result, source)

def get_codex_trace():
    return _global_trace.get_trace()

def get_latest_trace(container_id: Optional[str] = None):
    return _global_trace.get_latest_trace(container_id)

# ✅ NEW: Provide execution path wrapper for GHXEncoder
def trace_glyph_execution_path(glyph_id: str) -> Dict:
    """
    Trace the execution path for a specific glyph ID based on CodexTrace logs.
    Returns a lightweight dict structure usable by GHXEncoder.
    """
    matching = [e for e in _global_trace.get_trace() if e.get("glyph") == glyph_id]
    return {
        "glyph_id": glyph_id,
        "steps": matching,
        "count": len(matching),
        "latest": matching[-1] if matching else None
    }