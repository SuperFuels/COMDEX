# ===============================
# 📁 backend/tests/test_phase10_accel.py
# ===============================
import pytest
from backend.modules.codex.codex_virtual_qpu import CodexVirtualQPU
from backend.modules.symbolic_spreadsheet.models.glyph_cell import GlyphCell

@pytest.mark.asyncio
async def test_phase10_vector_beams_and_precision():
    qpu = CodexVirtualQPU()
    cells = [GlyphCell(id="p10a", logic="∇ ∇ ∇ ⊕ ⊕ ↔", position=[0,0])]
    ctx = {
        "container_id": "p10",
        "benchmark_silent": True,
        "phase10_enabled": True,
        "phase10_precision": "fp8",
    }
    await qpu.execute_sheet(cells, ctx)

    beams = getattr(cells[0], "wave_beams", [])
    vector_beams = [b for b in beams if b.get("stage") == "vector"]
    assert vector_beams, "expected at least one Phase 10 vector beam"
    assert any(b.get("precision") == "fp8" for b in vector_beams), "precision tag missing"
    # When ∇ is present we should see a quantization error summary field
    assert any("quant_error_mean" in b for b in vector_beams), "quant_error_mean not found"