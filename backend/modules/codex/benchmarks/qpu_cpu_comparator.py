# ===============================
# 📁 backend/modules/codex/benchmarks/qpu_cpu_comparator.py
# ===============================
"""
Phase 7 Benchmark: CodexVirtualCPU vs CodexVirtualQPU

- Executes a full .sqd.atom sheet on both symbolic CPU and QPU
- Collects execution metrics, SQI scores, mutation counts
- Broadcasts traces to QFC / SCI for live visualization
- Supports per-instruction metrics and symbolic FP4/FP8/INT8 simulation
"""

import json
from time import perf_counter
from typing import List, Dict, Any

from backend.modules.codex.codex_virtual_cpu import CodexVirtualCPU
from backend.modules.codex.codex_virtual_qpu import CodexVirtualQPU
from backend.modules.symbolic_spreadsheet.models.glyph_cell import GlyphCell
from backend.modules.symbolic_spreadsheet.scoring.sqi_scorer import score_sqi
from backend.modules.visualization.qfc_websocket_bridge import broadcast_qfc_update
from backend.modules.patterns.pattern_trace_engine import record_trace


def load_sqd_atom(path: str) -> List[GlyphCell]:
    """Load a .sqd.atom sheet file and return a list of GlyphCells."""
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    cells: List[GlyphCell] = []
    for cell_data in data.get("cells", []):
        cell = GlyphCell(
            id=cell_data.get("id"),
            logic=cell_data.get("logic", ""),
            position=cell_data.get("position", [0, 0]),
            emotion=cell_data.get("emotion", "neutral"),
            prediction=cell_data.get("prediction", "")
        )
        cells.append(cell)
    return cells


def run_cpu_benchmark(cells: List[GlyphCell], container_id: str = "benchmark_container") -> Dict[str, Any]:
    """Run a full CPU benchmark on a list of GlyphCells with per-instruction metrics."""
    cpu = CodexVirtualCPU()
    start_time = perf_counter()
    results = []

    for cell in cells:
        # Wrap the cell logic into a pseudo instruction tree
        instruction_tree = [{"op": "eval", "args": [cell.logic]}]
        result = cpu.executor.execute_tree(instruction_tree, context={"cell": cell})
        results.append(result)
        cell.result = result
        cell.sqi_score = score_sqi(cell)

        # Broadcast per-cell CPU metrics live
        try:
            broadcast_qfc_update(container_id, {
                "type": "cpu_cell_update",
                "cell_id": cell.id,
                "sqi": cell.sqi_score,
                "last_result": result,
                "metrics": getattr(cpu.executor, "dump_metrics", lambda: {})()
            })
        except Exception:
            pass

    elapsed = perf_counter() - start_time
    metrics = getattr(cpu.executor, "dump_metrics", lambda: {})()
    record_trace("cpu_benchmark", f"[CPU Benchmark] elapsed={elapsed:.6f}s, metrics={metrics}")

    return {
        "results": results,
        "sqi_scores": [cell.sqi_score for cell in cells],
        "elapsed": elapsed,
        "metrics": metrics
    }


def run_qpu_benchmark(cells: List[GlyphCell], container_id: str = "benchmark_container") -> Dict[str, Any]:
    """Run a full QPU benchmark on a list of GlyphCells with per-instruction metrics and precision simulation."""
    qpu = CodexVirtualQPU(use_qpu=True)
    start_time = perf_counter()
    results = qpu.execute_sheet(cells, context={"container_id": container_id})

    # Post-process SQI and broadcast per-cell metrics
    for cell in cells:
        cell.sqi_score = score_sqi(cell)
        try:
            broadcast_qfc_update(container_id, {
                "type": "qpu_cell_update",
                "cell_id": cell.id,
                "sqi": cell.sqi_score,
                "metrics": qpu.dump_metrics()
            })
        except Exception:
            pass

    elapsed = perf_counter() - start_time
    metrics = qpu.dump_metrics()
    record_trace("qpu_benchmark", f"[QPU Benchmark] elapsed={elapsed:.6f}s, metrics={metrics}")

    return {
        "results": results,
        "sqi_scores": [cell.sqi_score for cell in cells],
        "elapsed": elapsed,
        "metrics": metrics
    }


def compare_cpu_qpu(sheet_path: str, container_id: str = "benchmark_container"):
    """Compare execution of a full .sqd.atom sheet on CPU and QPU."""
    cells = load_sqd_atom(sheet_path)
    print(f"Loaded {len(cells)} cells from {sheet_path}")

    # CPU Benchmark
    print("\n=== CPU Benchmark ===")
    cpu_data = run_cpu_benchmark(cells, container_id)
    print(f"CPU elapsed: {cpu_data['elapsed']:.6f}s")
    print(f"CPU SQI scores: {cpu_data['sqi_scores']}")
    print(f"CPU metrics: {cpu_data['metrics']}")

    # QPU Benchmark
    print("\n=== QPU Benchmark ===")
    qpu_data = run_qpu_benchmark(cells, container_id)
    print(f"QPU elapsed: {qpu_data['elapsed']:.6f}s")
    print(f"QPU SQI scores: {qpu_data['sqi_scores']}")
    print(f"QPU metrics: {qpu_data['metrics']}")

    # Comparison summary
    print("\n=== Comparison ===")
    speedup = cpu_data['elapsed'] / qpu_data['elapsed'] if qpu_data['elapsed'] > 0 else float("inf")
    avg_cpu_sqi = sum(cpu_data['sqi_scores']) / len(cpu_data['sqi_scores']) if cpu_data['sqi_scores'] else 0
    avg_qpu_sqi = sum(qpu_data['sqi_scores']) / len(qpu_data['sqi_scores']) if qpu_data['sqi_scores'] else 0
    print(f"Speedup (CPU/QPU): {speedup:.2f}x")
    print(f"Avg SQI (CPU vs QPU): {avg_cpu_sqi:.3f} vs {avg_qpu_sqi:.3f}")

    # Optional: Save benchmark to .dc.json for replay / SCI/QFC
    benchmark_output = {
        "timestamp": perf_counter(),
        "sheet_path": sheet_path,
        "cpu": cpu_data,
        "qpu": qpu_data
    }
    try:
        out_path = sheet_path.replace(".sqd.atom", ".benchmark.dc.json")
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(benchmark_output, f, ensure_ascii=False, indent=2)
        print(f"✅ Benchmark saved to {out_path}")
    except Exception as e:
        print(f"⚠️ Failed to save benchmark: {e}")


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python qpu_cpu_comparator.py <path_to_sqd.atom>")
        sys.exit(1)

    path = sys.argv[1]
    compare_cpu_qpu(path)