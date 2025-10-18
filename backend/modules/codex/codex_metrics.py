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

def log_metric(name: str, value: float | dict, tags: dict = None):
    """
    Generic metric logger for Codex subsystems.
    Can accept scalar values or dict payloads.

    Example:
        log_metric("observer_collapse_decision", {"selected_path": "A"}, {"context": "qglyph"})
    """
    import json
    try:
        if isinstance(value, dict):
            val_str = json.dumps(value, ensure_ascii=False)
        else:
            val_str = str(value)

        tag_str = ", ".join(f"{k}={v}" for k, v in (tags or {}).items())
        print(f"[CodexMetric] {name} = {val_str} {tag_str}")
    except Exception as e:
        print(f"[CodexMetric] Failed to log metric {name}: {e}")  

class CodexMetricsShim:
    @staticmethod
    def record_execution_metrics(**kwargs) -> Dict[str, Any]:
        return record_execution_metrics(**kwargs)
        
def log_collapse_metric(container_id: str, beam_id: str, score: float, state: str):
    """
    Lightweight logger for symbolic wave collapse metrics.
    Logs collapse outcome for Codex beams with SQI score.
    """
    try:
        print(f"[CodexMetric] Beam {beam_id} in {container_id} → SQI={score}, state={state}")
    except Exception as e:
        print(f"[CodexMetric] Failed to log collapse metric: {e}")
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
    def record_execution_metrics(self, *args, **kwargs):
        """Legacy alias for record_execution_batch()"""
        return self.record_execution_batch(*args, **kwargs)

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

    def record_execution_batch(self, *args, **kwargs):
        """
        Compatibility method for batch execution logging.
        Accepts both legacy (instruction_tree, cost, source)
        and modern flexible keyword usage (adapter, op, payload, result).
        """

        import logging
        logger = logging.getLogger(__name__)

        try:
            # --- Legacy form ---
            instruction_tree = kwargs.get("instruction_tree") or (args[0] if args else None)
            cost = kwargs.get("cost")
            source = kwargs.get("source")

            # --- Modern flexible form ---
            adapter = kwargs.get("adapter", "unknown")
            op = kwargs.get("op", "unknown")
            payload = kwargs.get("payload")
            result = kwargs.get("result")

            # Handle legacy tree logging
            if instruction_tree is not None:
                if isinstance(instruction_tree, list):
                    for node in instruction_tree:
                        self.record_execution(
                            glyph=node.get("glyph") if isinstance(node, dict) else None,
                            source=source or adapter,
                            operator=node.get("opcode") if isinstance(node, dict) else None,
                        )
                elif isinstance(instruction_tree, dict):
                    self.record_execution(
                        glyph=instruction_tree.get("glyph"),
                        source=source or adapter,
                        operator=instruction_tree.get("opcode"),
                    )

            # Handle modern form logging
            if payload is not None:
                self.metrics.setdefault("batches", []).append({
                    "adapter": adapter,
                    "op": op,
                    "result": result,
                    "timestamp": __import__("time").time(),
                })
                logger.info(f"[CodexMetrics] Batch recorded: adapter={adapter}, op={op}")

            # Optionally log cost
            if cost is not None:
                self.metrics.setdefault("execution_costs", []).append(cost)

        except Exception as e:
            logger.warning("record_execution_batch failed: %s", e)  

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

    @staticmethod
    def record_log_event(level: str, message: str, trace_id: Optional[str] = None):
        # You can expand this to emit to DB, file, HUD, etc.
        log_line = f"[METRIC][{level.upper()}] {message}"
        if trace_id:
            log_line += f" | trace_id={trace_id}"
        print(log_line)
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

def estimate_compression_stats(container: dict) -> dict:
    """
    Estimate compression stats from a container containing raw source,
    symbolic tree, and glyphs.
    """
    import json
    from math import log2

    # Use 'source' instead of 'code' for CodexLang containers
    raw_source = container.get("source", "")
    try:
        raw_size = len(raw_source.encode("utf-8"))
    except Exception:
        raw_size = 0

    tree = container.get("symbolic_tree", {})
    glyphs = container.get("glyphs", [])

    # Size of symbolic tree in bytes
    try:
        tree_bytes = json.dumps(tree).encode("utf-8")
        tree_size = len(tree_bytes)
    except Exception:
        tree_size = 0

    # Compression ratio: raw vs symbolic tree
    try:
        compression_ratio = round(raw_size / tree_size, 3) if tree_size else 0.0
    except Exception:
        compression_ratio = 0.0

    # Symbolic depth from tree metadata
    try:
        symbolic_depth = tree.get("depth", 0) if isinstance(tree, dict) else 0
        symbolic_depth = int(symbolic_depth) if symbolic_depth is not None else 0
    except Exception:
        symbolic_depth = 0

    # Entropy estimate based on unique glyph diversity
    try:
        unique_glyphs = set(str(g) for g in glyphs)
        p = 1 / len(unique_glyphs) if unique_glyphs else 1
        entropy = -len(glyphs) * p * log2(p) if p > 0 else 0.0
    except Exception:
        entropy = 0.0

    return {
        "raw_size": raw_size,
        "tree_size": tree_size,
        "compression_ratio": float(compression_ratio),
        "symbolic_depth": symbolic_depth,
        "container_id": container.get("id", "unknown"),
        "source_file": container.get("source_file", "N/A"),
        "entropy": float(round(entropy, 3)),
    }

import os, json

def load_last_benchmark_score(path: str = "./benchmarks") -> dict:
    """
    Loads the most recent benchmark score JSON file from the benchmarks directory.
    Returns an empty dict if none found or parse fails.
    """
    try:
        if not os.path.isdir(path):
            return {}
        files = [f for f in os.listdir(path) if f.startswith("last_benchmark_") and f.endswith(".json")]
        if not files:
            return {}
        files.sort(key=lambda f: os.path.getmtime(os.path.join(path, f)), reverse=True)
        latest_file = os.path.join(path, files[0])
        with open(latest_file, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

import json
import time
from pathlib import Path
from typing import Optional

# ─────────────────────────────────────────────
# 📊 Benchmark Logger
# ─────────────────────────────────────────────
def log_benchmark_result(result: dict, to_file: Optional[str] = None):
    """
    Log benchmark metrics for a CodexLang or glyph compression test.
    Optionally writes to a file in JSONL format.
    """
    print(f"\n[Benchmark] {result.get('glyph', '[unknown glyph]')}")

    classical_time = result.get("classical_time")
    qglyph_time = result.get("qglyph_time")
    depth_classical = result.get("depth_classical")
    depth_qglyph = result.get("depth_qglyph")
    compression_ratio = result.get("compression_ratio")
    speedup_ratio = result.get("speedup_ratio")
    qglyph_id = result.get("qglyph_id")

    # Safe float formatting
    def fmt_float(val, digits=4, suffix="s"):
        try:
            return f"{float(val):.{digits}f}{suffix}"
        except (TypeError, ValueError):
            return "N/A"

    def fmt_ratio(val, digits=2):
        try:
            return f"{float(val):.{digits}f}×"
        except (TypeError, ValueError):
            return "N/A"

    print(f"  ⏱️  Classical Time: {fmt_float(classical_time)}")
    print(f"  🧬 QGlyph Time:    {fmt_float(qglyph_time)}")
    print(f"  📏 Depths → Classical: {depth_classical or 'N/A'} | QGlyph: {depth_qglyph or 'N/A'}")
    print(f"  🔁 Compression Ratio: {fmt_ratio(compression_ratio)}")
    print(f"  ⚡ Speedup Ratio:      {fmt_ratio(speedup_ratio)}")
    print(f"  🧿 QGlyph ID: {qglyph_id or '[none]'}")

    # Save to JSONL
    if to_file:
        try:
            with open(to_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(result, indent=2) + "\n")
        except Exception as e:
            print(f"⚠️ Failed to write benchmark to file: {e}")


# ─────────────────────────────────────────────
# 🧠 GHX Awareness Listener
# ─────────────────────────────────────────────
from backend.RQC.src.photon_runtime.telemetry.ghx_awareness_feed import get_latest_awareness_frame
# Optional if utils.py exists
# from backend.RQC.src.photon_runtime.telemetry.utils import render_awareness_plot

# If codexmetrics doesn’t yet define record_event, use this inline fallback
try:
    from backend.modules.codex.codexmetrics import record_event
except ImportError:
    def record_event(event_name: str, payload: dict = None):
        payload = payload or {}
        print(f"[CodexMetrics] Event: {event_name} {json.dumps(payload, ensure_ascii=False)}")
        return {"timestamp": time.time(), "event": event_name, "payload": payload}

LEDGER_PATH = Path("data/ledger/rqc_live_telemetry.jsonl")
REFRESH_INTERVAL = 2.0  # seconds

def run_listener(duration: float = 60.0):
    print("🧠 GHX Awareness Listener — Streaming Φ(t), R(t), S …")
    t0 = time.time()
    while time.time() - t0 < duration:
        frame = get_latest_awareness_frame(LEDGER_PATH)
        if frame:
            phi = frame.get("Phi", 0.0)
            res = frame.get("resonance_index", 0.0)
            stab = frame.get("stability", 0.0)
            gain = frame.get("gain", 0.0)
            print(f"[Φ={phi:.6f}] [R={res:.6f}] [S={stab:.3f}] [g={gain:.2f}]")
            record_event("GHX::awareness_frame", frame)
        time.sleep(REFRESH_INTERVAL)

if __name__ == "__main__":
    run_listener()


# ─────────────────────────────────────────────
# 📦 Exports
# ─────────────────────────────────────────────
__all__ = [
    "log_benchmark_result",
    "run_listener",
    "record_event",
]