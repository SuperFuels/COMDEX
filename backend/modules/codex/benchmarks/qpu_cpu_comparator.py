# ===============================
# 📁 backend/modules/codex/benchmarks/qpu_cpu_comparator.py
# ===============================
"""
Phase 7 Benchmark: CodexVirtualCPU vs CodexVirtualQPU

- Executes a full .sqd.atom sheet on both symbolic CPU and QPU
- Collects execution metrics, SQI scores, mutation counts
- Broadcasts live traces to QFC / SCI for visualization
"""

import json
from time import perf_counter
from typing import List, Dict, Any

from backend.modules.codex.codex_virtual_cpu import CodexVirtualCPU
from backend.modules.codex.codex_virtual_qpu import CodexVirtualQPU
from backend.modules.symbolic_spreadsheet.models.glyph_cell import GlyphCell
from backend.modules.symbolic_spreadsheet.scoring.sqi_scorer import score_sqi
from backend.modules.visualization.qfc_websocket_bridge import broadcast_cpu_qpu_metrics

# -------------------
# Load a .sqd.atom sheet
# -------------------
def load_sqd_atom(path: str) -> List[GlyphCell]:
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

# -------------------
# CPU Benchmark with live metrics
# -------------------
def run_cpu_benchmark(cells: List[GlyphCell], container_id: str = "cpu_benchmark") -> Dict[str, Any]:
    cpu = CodexVirtualCPU()
    start_time = perf_counter()
    results = []

    for cell in cells:
        # Execute as instruction tree
        res = cpu.executor.execute_tree([{"op": "eval", "args": [cell.logic]}])
        cell.result = res
        cell.sqi_score = score_sqi(cell)
        results.append(res)

        # Broadcast live metrics to SCI / QFC
        metrics = getattr(cpu.executor, "dump_metrics", lambda: {})()
        broadcast_cpu_qpu_metrics(container_id, metrics, cpu=True)

    elapsed = perf_counter() - start_time
    metrics = getattr(cpu.executor, "dump_metrics", lambda: {})()
    return {
        "results": results,
        "sqi_scores": [cell.sqi_score for cell in cells],
        "elapsed": elapsed,
        "metrics": metrics
    }

# -------------------
# QPU Benchmark with live metrics
# -------------------
def run_qpu_benchmark(cells: List[GlyphCell], container_id: str = "qpu_benchmark") -> Dict[str, Any]:
    qpu = CodexVirtualQPU(use_qpu=True)
    start_time = perf_counter()

    results = qpu.execute_sheet(cells, context={"container_id": container_id})

    elapsed = perf_counter() - start_time

    # Update SQI scores and broadcast per-cell metrics
    for cell in cells:
        cell.sqi_score = score_sqi(cell)
        metrics = qpu.dump_metrics()
        broadcast_cpu_qpu_metrics(container_id, metrics, cpu=False)

    metrics = qpu.dump_metrics()
    return {
        "results": results,
        "sqi_scores": [cell.sqi_score for cell in cells],
        "elapsed": elapsed,
        "metrics": metrics
    }

# -------------------
# Compare CPU vs QPU
# -------------------
def compare_cpu_qpu(sheet_path: str):
    cells = load_sqd_atom(sheet_path)
    print(f"Loaded {len(cells)} cells from {sheet_path}")

    print("\n=== CPU Benchmark ===")
    cpu_data = run_cpu_benchmark(cells)
    print(f"CPU elapsed: {cpu_data['elapsed']:.6f}s")
    print(f"CPU SQI scores: {cpu_data['sqi_scores']}")
    print(f"CPU metrics: {cpu_data['metrics']}")

    print("\n=== QPU Benchmark ===")
    qpu_data = run_qpu_benchmark(cells)
    print(f"QPU elapsed: {qpu_data['elapsed']:.6f}s")
    print(f"QPU SQI scores: {qpu_data['sqi_scores']}")
    print(f"QPU metrics: {qpu_data['metrics']}")

    # Comparison summary
    print("\n=== Comparison ===")
    speedup = cpu_data['elapsed'] / qpu_data['elapsed'] if qpu_data['elapsed'] > 0 else float("inf")
    print(f"Speedup (CPU/QPU): {speedup:.2f}x")
    avg_cpu_sqi = sum(cpu_data['sqi_scores']) / len(cpu_data['sqi_scores'])
    avg_qpu_sqi = sum(qpu_data['sqi_scores']) / len(qpu_data['sqi_scores'])
    print(f"Avg SQI (CPU vs QPU): {avg_cpu_sqi:.3f} vs {avg_qpu_sqi:.3f}")

# -------------------
# CLI Entry
# -------------------
if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python qpu_cpu_comparator.py <path_to_sqd.atom>")
        sys.exit(1)

    path = sys.argv[1]
    compare_cpu_qpu(path)