from collections import defaultdict
import json
import logging
import time
from typing import Any, Dict, Optional, Union

from backend.modules.codex.codex_cost_estimator import CodexCostEstimator  # ✅ For cost integration

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# 🔢 Lightweight, safe execution-metrics shim
# ─────────────────────────────────────────────────────────────────────────────

def _size(obj: Any) -> Optional[int]:
    try:
        return len(obj)
    except Exception:
        return None

def record_execution_metrics(
    adapter: str = "glyphnet",
    op: str = "execute",
    payload: Any = None,
    result: Any = None,
    start_ts: Optional[float] = None,
    extra: Optional[Dict[str, Any]] = None,
    success: bool = True,
) -> Dict[str, Any]:
    now_perf = time.perf_counter()
    dur_ms = ((now_perf - start_ts) * 1000.0) if isinstance(start_ts, (int, float)) else None

    entry: Dict[str, Any] = {
        "ts": time.time(),
        "adapter": adapter,
        "op": op,
        "success": bool(success),
        "duration_ms": dur_ms,
        "payload_size": _size(payload),
        "result_size": _size(result),
    }
    if extra:
        entry.update(extra)

    try:
        logger.info("[codex_metrics] %s", json.dumps(entry, ensure_ascii=False))
    except Exception:
        logger.info("[codex_metrics] %r", entry)

    return entry

class CodexMetricsShim:
    @staticmethod
    def record_execution_metrics(**kwargs) -> Dict[str, Any]:
        return record_execution_metrics(**kwargs)

# ─────────────────────────────────────────────────────────────────────────────
# 📈 Full metrics class with cost estimation
# ─────────────────────────────────────────────────────────────────────────────

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
            "confidence_events": 0,
            "blindspot_events": 0,
        }
        self.by_source = defaultdict(int)
        self.by_operator = defaultdict(int)
        self.by_glyph = defaultdict(int)
        self.proof_operators = defaultdict(int)
        self.collapse_bias_scores = []
        self.confidence_scores = []
        self.recent_blindspots = []

    def record_execution(self, glyph=None, source=None, operator=None):
        self.metrics["glyphs_executed"] += 1
        if source:
            self.by_source[source] += 1
        if operator:
            self.by_operator[operator] += 1
        if glyph:
            self.by_glyph[glyph] += 1

    # ✅ FIXED: This is now a proper method, not nested in record_execution
    def estimate_cost(self, instruction_tree: Union[Dict[str, Any], list]) -> float:
        """
        Rough heuristic so the executor can proceed.
        Uses CodexCostEstimator if available, otherwise fallback heuristic.
        Cost ∈ [0, 1].
        """
        try:
            # Prefer structural complexity score
            struct_cost = score_glyph_tree(instruction_tree)
            est = CodexCostEstimator()
            glyph_symbol = None
            if isinstance(instruction_tree, dict):
                glyph_symbol = instruction_tree.get("glyph")
            runtime_cost = est.estimate_glyph_cost(glyph_symbol or str(instruction_tree), {}).total()
            cost = struct_cost + runtime_cost
            # Normalise into 0..1 range
            return min(1.0, cost / 100.0)
        except Exception:
            # Fallback: size + depth heuristic
            try:
                size = len(json.dumps(instruction_tree, ensure_ascii=False))
            except Exception:
                size = len(str(instruction_tree))
            depth = _tree_depth(instruction_tree)
            return min(1.0, 0.0005 * size + 0.02 * depth)

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

    def record_mutation_test(self, glyph: str, suggestion: Any, success: bool, context: Dict[str, Any]):
        try:
            self.record_event("mutation_test", {
                "glyph": glyph,
                "success": success,
                "suggestion": suggestion,
                "container": context.get("container_id"),
                "tags": ["mutation", "rewrite", "codex"]
            })
        except Exception as e:
            logger.warning(f"[CodexMetrics] Failed to record mutation test: {e}")

    def record_confidence_event(self, score: float):
        self.metrics["confidence_events"] += 1
        bounded = max(0.0, min(1.0, score))
        self.confidence_scores.append(bounded)
        if len(self.confidence_scores) > 100:
            self.confidence_scores = self.confidence_scores[-100:]

    def record_glyph_generated(self, glyph: dict, source: str = "creative_synthesis"):
        self.metrics["glyphs_generated"] = self.metrics.get("glyphs_generated", 0) + 1
        label = glyph.get("glyph") or glyph.get("label") or "unknown"
        self.by_glyph[label] += 1
        self.by_source[source] += 1

    def record_blindspot_event(self, reason: str, glyph: str, meta: dict = None):
        self.metrics["blindspot_events"] += 1
        entry = {"reason": reason, "glyph": glyph, "meta": meta or {}}
        self.recent_blindspots.append(entry)
        if len(self.recent_blindspots) > 50:
            self.recent_blindspots = self.recent_blindspots[-50:]

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
        if self.confidence_scores:
            avg = sum(self.confidence_scores) / len(self.confidence_scores)
            output["avg_confidence"] = round(avg, 4)
            output["confidence_scores"] = self.confidence_scores[-5:]
        if self.recent_blindspots:
            output["recent_blindspots"] = self.recent_blindspots[-5:]
        return self.metrics if not detailed else output

    def reset(self):
        for key in self.metrics:
            self.metrics[key] = 0
        self.by_source.clear()
        self.by_operator.clear()
        self.by_glyph.clear()
        self.proof_operators.clear()
        self.collapse_bias_scores.clear()
        self.confidence_scores.clear()
        self.recent_blindspots.clear()

    def record_execution_batch(self, instruction_tree, cost: float = None, source: str = None):
        """
        Compatibility method for batch execution logging.
        - Increments glyph count based on tree length.
        - Optionally records a cost estimate if provided.
        """
        try:
            # If it's a list/dict of glyphs, count them
            if isinstance(instruction_tree, list):
                for node in instruction_tree:
                    self.record_execution(glyph=node.get("glyph") if isinstance(node, dict) else None,
                                          source=source,
                                          operator=node.get("opcode") if isinstance(node, dict) else None)
            elif isinstance(instruction_tree, dict):
                self.record_execution(glyph=instruction_tree.get("glyph"),
                                      source=source,
                                      operator=instruction_tree.get("opcode"))

            # Optionally log cost
            if cost is not None:
                if "execution_costs" not in self.metrics:
                    self.metrics["execution_costs"] = []
                self.metrics["execution_costs"].append(cost)

        except Exception as e:
            # Never block execution on metrics failure
            import logging
            logging.getLogger(__name__).warning("record_execution_batch failed: %s", e)    

    @staticmethod
    def score_alignment(rewrite: dict, active_goals: list) -> float:
        """
        Estimate how well the suggested rewrite aligns with active goals.
        Heuristic: based on symbolic match, variable overlap, or tag alignment.
        """
        score = 0.0
        target = rewrite.get("target", "")
        replacement = rewrite.get("replacement", "")

        for goal in active_goals:
            goal_text = str(goal)
            if target in goal_text:
                score += 0.3
            if replacement in goal_text:
                score += 0.5

        return min(score, 1.0)

    @staticmethod
    def estimate_rewrite_success(rewrite: dict) -> float:
        """
        Estimate the probability that the rewrite will succeed in resolving contradiction or progressing logic.
        Heuristic: based on common symbolic patterns and replacement structure.
        """
        rep = rewrite.get("replacement", "")
        if "∧" in rep or "¬" in rep:
            return 0.9  # Strong logical form
        if "∀" in rep or "∃" in rep:
            return 0.7  # Quantifiers may be harder to validate
        return 0.6  # Default baseline
# ─────────────────────────────────────────────────────────────────────────────
# Utilities
# ─────────────────────────────────────────────────────────────────────────────
def record_mutation_event(event: dict) -> None:
    """
    Record a DNA mutation event into Codex metrics/logs.

    Args:
        event: A mutation dictionary with keys like original, mutated, metadata, etc.
    """
    if not isinstance(event, dict):
        return

    print(f"[CodexMetrics] Mutation recorded — reason: {event.get('metadata', {}).get('reason', 'unknown')}")

    entropy = event.get("metadata", {}).get("entropy_delta")
    success = event.get("metadata", {}).get("rewrite_success_prob")

    if entropy is not None:
        print(f"  ⤷ Entropy Δ: {entropy}")
    if success is not None:
        print(f"  ⤷ Success Prob: {success}")

def record_sqi_score_event(event: dict) -> None:
    """
    Record an SQI scoring event during glyph mutation analysis.

    Args:
        event: Dictionary with mutation_id, goal_match_score, entropy_delta, etc.
    """
    log_entry = {
        "type": "sqi_score",
        "timestamp": event.get("timestamp"),
        "mutation_id": event.get("mutation_id"),
        "container_id": event.get("container_id"),
        "goal_match_score": event.get("goal_match_score"),
        "rewrite_success_prob": event.get("rewrite_success_prob"),
        "entropy_delta": event.get("entropy_delta"),
    }

    # You can later route this to a metrics DB or .dc file
    print(f"[CodexMetrics] SQI Score Event → {log_entry}")

def score_glyph_tree(tree):
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

def calculate_glyph_cost(glyph_data: dict, context: dict = None) -> float:
    context = context or {}
    estimator = CodexCostEstimator()
    tree_cost = score_glyph_tree(glyph_data.get("tree", glyph_data))
    glyph_symbol = glyph_data.get("glyph") if isinstance(glyph_data, dict) else str(glyph_data)
    runtime_cost = estimator.estimate_glyph_cost(glyph_symbol, context).total()
    return tree_cost + runtime_cost

def _tree_depth(node) -> int:
    if node is None:
        return 0
    if isinstance(node, dict):
        children = node.get("children") or []
        return 1 + (max((_tree_depth(ch) for ch in children), default=0) if isinstance(children, list) else 0)
    if isinstance(node, list):
        return 1 + (max((_tree_depth(ch) for ch in node), default=0))
    return 1

def log_benchmark_result(result: dict):
    print(f"\n[Benchmark] {result['glyph']}")
    print(f"  ⏱️  Classical Time: {result['classical_time']}s")
    print(f"  🧬 QGlyph Time:    {result['qglyph_time']}s")
    print(f"  📏 Depths → Classical: {result['depth_classical']} | QGlyph: {result['depth_qglyph']}")
    print(f"  🔁 Compression Ratio: {result['compression_ratio']}×")
    print(f"  ⚡ Speedup Ratio:      {result['speedup_ratio']}×")
    print(f"  🧿 QGlyph ID: {result['qglyph_id']}")

__all__ = [
    "record_execution_metrics",
    "CodexMetricsShim",
    "CodexMetrics",
    "score_glyph_tree",
    "calculate_glyph_cost",
    "log_benchmark_result",
]
codex_metrics = CodexMetrics()