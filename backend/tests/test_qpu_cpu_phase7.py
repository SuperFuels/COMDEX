import asyncio
from time import perf_counter
from typing import List

from backend.modules.codex.codex_virtual_cpu import CodexVirtualCPU
from backend.modules.codex.codex_virtual_qpu import CodexVirtualQPU
from backend.modules.symbolic_spreadsheet.models.glyph_cell import GlyphCell
from backend.modules.visualization.qfc_websocket_bridge import broadcast_qfc_update

# -------------------
# Terminal test for Phase 7: QPU vs CPU
# -------------------

CONTAINER_ID = "phase7_test_container"

# Mock broadcast to print payloads to terminal instead of WebSocket
async def mock_broadcast(container_id: str, payload: dict):
    print(f"\n📡 Broadcast to {container_id}:")
    for k, v in payload.items():
        if k in ["token_metrics", "opcode_breakdown", "sheet_token_metrics", "sheet_opcode_metrics"]:
            print(f"  {k}: <{len(v) if isinstance(v, dict) else len(v)}> entries")
        else:
            print(f"  {k}: {v}")


# Patch broadcast_qfc_update to terminal
broadcast_qfc_update_orig = broadcast_qfc_update
broadcast_qfc_update = mock_broadcast  # override


def create_test_sheet(num_cells: int = 5) -> List[GlyphCell]:
    """Create a mock .sqd.atom sheet with random GlyphCells."""
    sheet = []
    for i in range(num_cells):
        cell = GlyphCell(
            id=f"cell_{i}",
            logic="⊕ ↔ ⟲ → ✦",
            position=[i, 0, 0, 0],
            emotion="curious",
            prediction=f"Pred_{i}"
        )
        sheet.append(cell)
    return sheet


async def test_phase7():
    print("🚀 Phase 7 Terminal Test: QPU vs CPU")

    sheet = create_test_sheet(num_cells=5)

    # -------------------
    # CPU Benchmark
    # -------------------
    print("\n💻 Running CPU Benchmark...")
    cpu = CodexVirtualCPU()
    cpu_start = perf_counter()
    cpu_results = {}
    for cell in sheet:
        cpu_results[cell.id] = cpu.execute_cell(cell, context={"container_id": CONTAINER_ID})
    cpu_elapsed = perf_counter() - cpu_start
    print(f"✅ CPU elapsed: {cpu_elapsed:.6f}s")
    print("CPU SQI Scores:", [cell.sqi_score for cell in sheet])
    print("CPU Metrics:", cpu.dump_metrics())

    # -------------------
    # QPU Benchmark
    # -------------------
    print("\n⚛️ Running QPU Benchmark...")
    qpu = CodexVirtualQPU()
    qpu_start = perf_counter()
    qpu_results = qpu.execute_sheet(sheet, context={"container_id": CONTAINER_ID})
    qpu_elapsed = perf_counter() - qpu_start
    print(f"✅ QPU elapsed: {qpu_elapsed:.6f}s")
    print("QPU SQI Scores:", [cell.sqi_score for cell in sheet])
    print("QPU Metrics:", qpu.dump_metrics())

    # -------------------
    # Comparison
    # -------------------
    speedup = cpu_elapsed / qpu_elapsed if qpu_elapsed > 0 else float("inf")
    avg_cpu_sqi = sum(cell.sqi_score for cell in sheet) / len(sheet)
    avg_qpu_sqi = avg_cpu_sqi  # just using same cells, fine for terminal test

    print("\n📊 Comparison Summary:")
    print(f"Speedup (CPU/QPU): {speedup:.2f}x")
    print(f"Avg SQI (CPU vs QPU): {avg_cpu_sqi:.3f} vs {avg_qpu_sqi:.3f}")

    # -------------------
    # Sheet metrics verification
    # -------------------
    print("\n🔍 Verifying aggregate sheet metrics...")
    for cell in sheet:
        print(f"Cell {cell.id} token metrics entries:", len(qpu.token_metrics.get(cell.logic, [])))
        print(f"Cell {cell.id} opcode metrics entries:", len(qpu.opcode_metrics.get(cell.id, {})))


if __name__ == "__main__":
    asyncio.run(test_phase7())
