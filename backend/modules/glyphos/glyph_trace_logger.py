import time

class GlyphTraceLogger:
    def __init__(self):
        self.trace_log = []

    def log_trace(self, glyph, result, context="runtime"):
        entry = {
            "timestamp": time.time(),
            "glyph": glyph,
            "result": result,
            "context": context
        }
        self.trace_log.append(entry)
        return entry

    def get_recent_traces(self, limit=25):
        return self.trace_log[-limit:]
