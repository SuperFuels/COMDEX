# 📁 codex_metrics.py

class CodexMetrics:
    def __init__(self):
        self.metrics = {
            "glyphs_executed": 0,
            "mutations_proposed": 0,
            "runtime_errors": 0,
        }

    def record_execution(self):
        self.metrics["glyphs_executed"] += 1

    def record_mutation(self):
        self.metrics["mutations_proposed"] += 1

    def record_error(self):
        self.metrics["runtime_errors"] += 1

    def dump(self):
        return self.metrics