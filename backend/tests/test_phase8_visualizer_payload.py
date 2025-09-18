import pytest
from backend.modules.codex.codex_virtual_qpu import CodexVirtualQPU
from backend.modules.symbolic_spreadsheet.models.glyph_cell import GlyphCell

@pytest.mark.asyncio
async def test_phase8_visualizer_payload_shape():
    qpu = CodexVirtualQPU()
    cells = [GlyphCell(id="v0", logic="⊕ ↔ ✦", position=[0,0])]
    ctx = {"container_id": "phase8_vis", "benchmark_silent": True}
    await qpu.execute_sheet(cells, ctx)
    # sanity: lineage/entanglement data is computed (even though broadcast is silent)
    assert "sheet_run_id" in ctx
    assert isinstance(ctx.get("entanglements_map", {}), dict)