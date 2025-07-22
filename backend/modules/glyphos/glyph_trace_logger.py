import time
import json
from pathlib import Path
from typing import List, Optional

LOG_PATH = Path("logs/glyph_trace_log.json")


class GlyphTraceLogger:
    def __init__(self, persist: bool = True):
        self.trace_log: List[dict] = []
        self.persist = persist
        self._load_existing_log()

    def _load_existing_log(self):
        if self.persist and LOG_PATH.exists():
            try:
                with open(LOG_PATH, "r") as f:
                    self.trace_log = json.load(f)
            except Exception:
                self.trace_log = []

    def _save_log(self):
        if not self.persist:
            return
        LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        try:
            with open(LOG_PATH, "w") as f:
                json.dump(self.trace_log[-500:], f, indent=2)  # Keep last 500 entries
        except Exception as e:
            print(f"[⚠️] Failed to persist trace log: {e}")

    def log_trace(self, glyph: str, result: str, context: str = "runtime") -> dict:
        entry = {
            "timestamp": time.time(),
            "iso_time": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "glyph": glyph,
            "result": result,
            "context": context
        }
        self.trace_log.append(entry)
        self._save_log()
        return entry

    def get_recent_traces(self, limit: int = 25) -> List[dict]:
        return self.trace_log[-limit:]

    def filter_traces(self, glyph: Optional[str] = None, context: Optional[str] = None) -> List[dict]:
        filtered = self.trace_log
        if glyph:
            filtered = [t for t in filtered if t["glyph"] == glyph]
        if context:
            filtered = [t for t in filtered if t["context"] == context]
        return filtered[-100:]

    def export_to_scroll(self) -> dict:
        """
        Export the trace log as a .codexscroll structure.
        """
        return {
            "scroll_type": "glyph_trace",
            "created": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "entries": self.trace_log[-100:]  # last 100 traces
        }


# ✅ Singleton
glyph_trace = GlyphTraceLogger()

# 🧪 Optional test
if __name__ == "__main__":
    glyph_trace.log_trace("⚛", "dream started", context="tessaris")
    glyph_trace.log_trace("⬁", "mutation proposed", context="dna")
    print("Last 2 traces:", glyph_trace.get_recent_traces(2))
    print("Exported scroll:", json.dumps(glyph_trace.export_to_scroll(), indent=2))