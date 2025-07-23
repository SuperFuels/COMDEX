# File: backend/modules/codex/benchmark_runner.py

import time
import json
from backend.modules.codex.codex_executor import execute_codex_instruction_tree
from backend.modules.glyphos.glyph_logic import interpret_glyph
from backend.modules.sqi.qglyph_generator import QGlyphGenerator
from backend.modules.codex.codex_metrics import log_benchmark_result

# Instantiate the QGlyph generator once
generator = QGlyphGenerator()

def benchmark_execution(glyph_str: str, context: dict = None) -> dict:
    """
    Benchmarks execution time, depth, and compression of a glyph logic string
    using both classical and QGlyph (symbolic quantum) execution.
    """
    # Parse the classical instruction tree
    parsed_tree = interpret_glyph(glyph_str, context or {})

    # Classical execution
    start_classical = time.perf_counter()
    classical_result = execute_codex_instruction_tree(parsed_tree, context=context)
    end_classical = time.perf_counter()
    classical_time = end_classical - start_classical

    # QGlyph generation + execution
    qglyph = generator.generate_superposed_glyph(glyph_str)
    logic_tree = {
        "type": "qglyph",
        "depth": 1,
        "tree": qglyph["superposed"]
    }

    start_qglyph = time.perf_counter()
    qglyph_result = execute_codex_instruction_tree(logic_tree, context=context)
    end_qglyph = time.perf_counter()
    qglyph_time = end_qglyph - start_qglyph

    # Metrics
    classical_depth = parsed_tree.get("depth", 1)
    qglyph_depth = logic_tree.get("depth", 1)

    compression_ratio = classical_depth / qglyph_depth if qglyph_depth else 1.0
    speedup = classical_time / qglyph_time if qglyph_time else 1.0

    result = {
        "glyph": glyph_str,
        "classical_time": round(classical_time, 6),
        "qglyph_time": round(qglyph_time, 6),
        "depth_classical": classical_depth,
        "depth_qglyph": qglyph_depth,
        "compression_ratio": round(compression_ratio, 3),
        "speedup_ratio": round(speedup, 3),
        "qglyph_id": qglyph["id"]
    }

    log_benchmark_result(result)
    return result


def run_batch_benchmarks(glyph_list: list[str]) -> list[dict]:
    """Run a series of benchmarks and return results."""
    return [benchmark_execution(g) for g in glyph_list]


if __name__ == "__main__":
    sample_glyphs = ["A ⊕ B", "A → B", "[A:0 ↔ 1] → D", "(A ⟲ B) ⧖ C"]
    results = run_batch_benchmarks(sample_glyphs)
    print(json.dumps(results, indent=2))