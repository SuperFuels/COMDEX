from collections import defaultdict
import json


class CodexMetrics:
    def __init__(self):
        self.metrics = {
            "glyphs_executed": 0,
            "mutations_proposed": 0,
            "runtime_errors": 0,
            "qglyphs_generated": 0,
            "qglyphs_collapsed": 0,
            "entangled_pairs": 0,
            "theorems_used": 0,
            "theorem_failures": 0,
        }
        self.by_source = defaultdict(int)
        self.by_operator = defaultdict(int)
        self.by_glyph = defaultdict(int)
        self.proof_operators = defaultdict(int)
        self.collapse_bias_scores = []

    def record_execution(self, glyph=None, source=None, operator=None):
        self.metrics["glyphs_executed"] += 1
        if source:
            self.by_source[source] += 1
        if operator:
            self.by_operator[operator] += 1
        if glyph:
            self.by_glyph[glyph] += 1

    def record_theorem_usage(self, glyph: str, operator: str = None, success: bool = True):
        self.metrics["theorems_used"] += 1
        if operator:
            self.proof_operators[operator] += 1
        if not success:
            self.metrics["theorem_failures"] += 1

    def record_mutation(self):
        self.metrics["mutations_proposed"] += 1

    def record_error(self):
        self.metrics["runtime_errors"] += 1

    def record_qglyph_generation(self):
        self.metrics["qglyphs_generated"] += 1

    def record_qglyph_collapse(self, bias_score: float = None):
        self.metrics["qglyphs_collapsed"] += 1
        if bias_score is not None:
            self.collapse_bias_scores.append(bias_score)

    def record_entangled_pair(self):
        self.metrics["entangled_pairs"] += 1

    def dump(self, detailed=False):
        output = {
            "summary": self.metrics,
            "by_source": dict(self.by_source),
            "by_operator": dict(self.by_operator),
            "by_glyph": dict(self.by_glyph),
            "proof_operators": dict(self.proof_operators),
        }
        if self.collapse_bias_scores:
            avg = sum(self.collapse_bias_scores) / len(self.collapse_bias_scores)
            output["avg_collapse_bias"] = round(avg, 4)
            output["collapse_bias_scores"] = self.collapse_bias_scores[-5:]
        return self.metrics if not detailed else output

    def reset(self):
        for key in self.metrics:
            self.metrics[key] = 0
        self.by_source.clear()
        self.by_operator.clear()
        self.by_glyph.clear()
        self.proof_operators.clear()
        self.collapse_bias_scores.clear()


def score_glyph_tree(tree):
    """
    Returns a symbolic score for a CodexLang tree based on depth, branching, and operator complexity.
    Used for compression benchmarking or intent prioritization.
    """
    score = 0

    def traverse(node, depth=1):
        nonlocal score
        score += depth
        if isinstance(node, dict):
            for key, val in node.items():
                if key in ["↔", "⧖", "⟲", "⊕", "→"]:
                    score += 3
                traverse(val, depth + 1)
        elif isinstance(node, list):
            for item in node:
                traverse(item, depth + 1)

    traverse(tree)
    return score


# ✅ Logging utility for benchmark_runner.py
def log_benchmark_result(result: dict):
    print(f"\n[Benchmark] {result['glyph']}")
    print(f"  ⏱️  Classical Time: {result['classical_time']}s")
    print(f"  🧬 QGlyph Time:    {result['qglyph_time']}s")
    print(f"  📏 Depths → Classical: {result['depth_classical']} | QGlyph: {result['depth_qglyph']}")
    print(f"  🔁 Compression Ratio: {result['compression_ratio']}×")
    print(f"  ⚡ Speedup Ratio:      {result['speedup_ratio']}×")
    print(f"  🧿 QGlyph ID: {result['qglyph_id']}")