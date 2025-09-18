import pytest
from backend.modules.codex.codex_virtual_qpu import CodexVirtualQPU
from backend.modules.symbolic_spreadsheet.models.glyph_cell import GlyphCell

@pytest.mark.asyncio
async def test_phase8_beam_stages_present():
    qpu = CodexVirtualQPU()
    cells = [GlyphCell(id="s0", logic="⊕ ∇ ↔ ⟲ → ✦", position=[0,0])]
    ctx = {"container_id": "phase8_stages", "benchmark_silent": True, "batch_collapse": True}
    await qpu.execute_sheet(cells, ctx)
    beams = getattr(cells[0], "wave_beams", [])
    stages = {b.get("stage") for b in beams}
    assert {"ingest", "entangle", "collapse"}.issubset(stages)