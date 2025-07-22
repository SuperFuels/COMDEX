# 📁 codex_metrics.py

from collections import defaultdict
import json

class CodexMetrics:
    def __init__(self):
        self.metrics = {
            "glyphs_executed": 0,
            "mutations_proposed": 0,
            "runtime_errors": 0,
        }
        self.by_source = defaultdict(int)
        self.by_operator = defaultdict(int)
        self.by_glyph = defaultdict(int)

    def record_execution(self, glyph=None, source=None, operator=None):
        self.metrics["glyphs_executed"] += 1

        if source:
            self.by_source[source] += 1
        if operator:
            self.by_operator[operator] += 1
        if glyph:
            self.by_glyph[glyph] += 1

    def record_mutation(self):
        self.metrics["mutations_proposed"] += 1

    def record_error(self):
        self.metrics["runtime_errors"] += 1

    def dump(self, detailed=False):
        if not detailed:
            return self.metrics
        return {
            "summary": self.metrics,
            "by_source": dict(self.by_source),
            "by_operator": dict(self.by_operator),
            "by_glyph": dict(self.by_glyph),
        }

    def reset(self):
        for key in self.metrics:
            self.metrics[key] = 0
        self.by_source.clear()
        self.by_operator.clear()
        self.by_glyph.clear()