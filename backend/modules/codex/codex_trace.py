# 📁 backend/modules/codex/codex_trace.py

import time
from typing import List, Dict

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

    def to_json(self):
        import json
        return json.dumps(self.entries, indent=2)

# ✅ Add this function to support imports from glyph_quantum_core.py
_global_trace = CodexTrace()

def log_codex_trace(glyph: str, context: dict, result: str, source: str = "benchmark"):
    _global_trace.record(glyph, context, result, source)

def get_codex_trace():
    return _global_trace.get_trace()