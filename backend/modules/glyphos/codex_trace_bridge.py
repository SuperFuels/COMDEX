# File: backend/modules/glyphos/codex_trace_bridge.py

from typing import List, Dict
from datetime import datetime
from collections import deque
import threading

MAX_TRACE_LOG = 300

class CodexTraceBridge:
    def __init__(self):
        self.lock = threading.Lock()
        self.trace_log: deque[Dict] = deque(maxlen=MAX_TRACE_LOG)

    def log(self, source: str, glyph: str, trace_type: str):
        entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "source": source,
            "glyph": glyph,
            "type": trace_type
        }
        with self.lock:
            self.trace_log.append(entry)

    def get_trace(self) -> List[Dict]:
        with self.lock:
            return list(self.trace_log)

    def clear(self):
        with self.lock:
            self.trace_log.clear()

codex_trace = CodexTraceBridge()