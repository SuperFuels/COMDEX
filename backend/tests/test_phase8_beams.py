import asyncio
import pytest
from backend.modules.codex.codex_virtual_qpu import CodexVirtualQPU
from backend.modules.symbolic_spreadsheet.models.glyph_cell import GlyphCell

@pytest.mark.asyncio
async def test_phase8_beam_lineage_and_entanglement():
    qpu = CodexVirtualQPU()
    cells = [
        GlyphCell(id="c0", logic="⊕ ∇ ↔ ⟲ -> ✦", position=[0,0]),
        GlyphCell(id="c1", logic="⊕ ∇ ↔ ⟲ -> ✦", position=[1,0]),
    ]
    ctx = {
        "container_id": "phase8_test_container",
        "benchmark_silent": True,  # silence HUD
        "max_concurrency": 4
    }
    results = await qpu.execute_sheet(cells, ctx)

    # lineage present
    for c in cells:
        beams = getattr(c, "wave_beams", [])
        assert beams and any(b["stage"] == "predict" for b in beams), "predict beam missing"
        assert any(b["stage"] == "ingest" for b in beams), "ingest beam missing"
        assert any(b["stage"] == "collapse" for b in beams), "collapse beam missing"

    # entanglement map built
    ent_map = ctx.get("entanglements_map", {})
    # there should be at least one entanglement id with both cells if ↔ ran under same logic
    joined = set()
    for eid, members in ent_map.items():
        for m in members:
            joined.add(m)
    assert {"c0", "c1"}.issubset(joined), "cells must be grouped by at least one entanglement id"

    # precision profile still available
    prof = qpu.get_precision_profile()
    assert "∇" in prof and prof["∇"]["count"] >= len(cells), "∇ must be profiled in Phase 8 too"