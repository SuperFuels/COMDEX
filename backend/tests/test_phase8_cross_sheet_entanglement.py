import pytest
from backend.modules.codex.codex_virtual_qpu import CodexVirtualQPU
from backend.modules.symbolic_spreadsheet.models.glyph_cell import GlyphCell  # adjust if your path differs

@pytest.mark.asyncio
async def test_phase8_cross_sheet_entanglement():
    qpu = CodexVirtualQPU()

    cells_a = [GlyphCell(id="a0", logic="⊕ ∇ ↔", position=[0,0])]
    cells_b = [GlyphCell(id="b0", logic="⊕ ∇ ↔", position=[0,1])]

    ctx_a = {"container_id": "phase8_ca", "sheet_run_id": "runX", "benchmark_silent": True}
    ctx_b = {"container_id": "phase8_cb", "sheet_run_id": "runX", "benchmark_silent": True}

    await qpu.execute_sheet(cells_a, ctx_a)
    await qpu.execute_sheet(cells_b, ctx_b)

    merged = qpu.merge_entanglement_context(ctx_a, ctx_b)
    ent_map = merged.get("entanglements_map", {})
    # at least one eid should contain both cells
    assert any({"a0","b0"}.issubset(set(members)) for members in ent_map.values())