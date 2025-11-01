# ===============================
# 📁 backend/tests/test_qpu_cpu_phase7.py
# ===============================
import asyncio
import inspect
from time import perf_counter
from typing import List, Dict, Any

from backend.modules.symbolic_spreadsheet.models.glyph_cell import GlyphCell
from backend.modules.glyphos.glyph_tokenizer import tokenize_symbol_text_to_glyphs

# -------------------
# Lazy imports to avoid circular dependency
# -------------------
def import_cpus():
    from backend.modules.codex.virtual.codex_virtual_cpu import CodexVirtualCPU
    from backend.modules.codex.codex_virtual_qpu import CodexVirtualQPU
    return CodexVirtualCPU, CodexVirtualQPU

CONTAINER_ID = "phase7_test_container"

# Async-safe helper
async def maybe_await(val):
    return await val if inspect.isawaitable(val) else val

# Mock broadcast -> print to terminal
async def mock_broadcast(container_id: str, payload: dict):
    print(f"\n📡 Broadcast to {container_id}:")
    for k, v in payload.items():
        if k in ["token_metrics", "opcode_breakdown", "sheet_token_metrics", "sheet_opcode_metrics"]:
            size = len(v) if hasattr(v, "__len__") else "?"
            print(f"  {k}: <{size}> entries")
        else:
            print(f"  {k}: {v}")


def create_test_sheet(num_cells: int = 5, logic: str = "⊕ ∇ ↔ ⟲ -> ✦") -> List[GlyphCell]:
    sheet = []
    for i in range(num_cells):
        cell = GlyphCell(
            id=f"cell_{i}",
            logic=logic,  # << includes ∇ by default now
            position=[i, 0, 0, 0],
            emotion="curious",
            prediction=f"Pred_{i}",
        )
        sheet.append(cell)
    return sheet

def count_token_metrics_for_cell(qpu, cell: GlyphCell) -> int:
    """Sum token-metric entries for all token keys present in this cell's logic."""
    try:
        tokens = tokenize_symbol_text_to_glyphs(cell.logic)
        keys = {t.get("value") for t in tokens if "value" in t}
    except Exception:
        keys = set()
    return sum(len(qpu.token_metrics.get(k, [])) for k in keys)

async def test_phase7():
    print("🚀 Phase 7 Terminal Test: QPU vs CPU")

    # Lazy CPU/QPU import
    CodexVirtualCPU, CodexVirtualQPU = import_cpus()

    # Prepare sheet
    sheet = create_test_sheet(num_cells=5)

    # Properly monkey-patch the broadcast function inside the QPU module namespace
    import backend.modules.codex.codex_virtual_qpu as qpu_mod
    orig_broadcast = qpu_mod.broadcast_qfc_update
    qpu_mod.broadcast_qfc_update = mock_broadcast

    try:
        # -------------------
        # CPU Benchmark
        # -------------------
        print("\n💻 Running CPU Benchmark...")
        cpu = CodexVirtualCPU()
        cpu_start = perf_counter()
        cpu_results: Dict[str, Any] = {}
        for cell in sheet:
            cpu_results[cell.id] = await maybe_await(cpu.execute_cell(cell, context={"container_id": CONTAINER_ID}))
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
        qpu_results = await qpu.execute_sheet(
            sheet,
            context={
                "container_id": CONTAINER_ID,
                "benchmark_silent": True,   # (optional) disable HUD broadcasts during test
                "max_concurrency": 8        # (optional) bounded parallelism
            }
        )
        qpu_elapsed = perf_counter() - qpu_start
        print(f"✅ QPU elapsed: {qpu_elapsed:.6f}s")
        print("QPU SQI Scores:", [cell.sqi_score for cell in sheet])
        print("QPU Metrics:", qpu.dump_metrics())

        # --- NEW: Precision profile snapshot ---
        profile = qpu.get_precision_profile()
        print("\n🎯 Precision Profile (avg time & rel err per opcode):")
        for op, p in profile.items():
            t = p["avg_time"]; e = p["avg_rel_err"]
            print(
                f"  {op} -> rec:{p['recommendation']} | "
                f"time(fp4={t['fp4']:.6f}, fp8={t['fp8']:.6f}, int8={t['int8']:.6f}) | "
                f"rel_err(fp4={e['fp4']:.4f}, fp8={e['fp8']:.4f}, int8={e['int8']:.4f})"
            )

        # ✅ Assert that the numeric ∇ opcode was actually profiled
        assert "∇" in profile and profile["∇"]["count"] >= len(sheet), "∇ must be profiled"

        # -------------------
        # Comparison
        # -------------------
        speedup = cpu_elapsed / qpu_elapsed if qpu_elapsed > 0 else float("inf")
        avg_cpu_sqi = sum(cell.sqi_score for cell in sheet) / len(sheet)
        avg_qpu_sqi = sum(cell.sqi_score for cell in sheet) / len(sheet)

        print("\n📊 Comparison Summary:")
        print(f"Speedup (CPU/QPU): {speedup:.2f}x")
        print(f"Avg SQI (CPU vs QPU): {avg_cpu_sqi:.3f} vs {avg_qpu_sqi:.3f}")

        # -------------------
        # Sheet metrics verification
        # -------------------
        print("\n🔍 Verifying aggregate sheet metrics...")
        for cell in sheet:
            token_entries = count_token_metrics_for_cell(qpu, cell)
            opcode_entries = len(getattr(qpu, "opcode_metrics", {}).get(cell.id, {}))
            beam_count = len(getattr(cell, "wave_beams", []))
            print(f"Cell {cell.id} token metrics entries:", token_entries)
            print(f"Cell {cell.id} opcode metrics entries:", opcode_entries)
            print(f"Cell {cell.id} wave_beams emitted:", beam_count)

    finally:
        # Restore original broadcast
        qpu_mod.broadcast_qfc_update = orig_broadcast

if __name__ == "__main__":
    asyncio.run(test_phase7())