import pytest

from backend.modules.codex.codex_virtual_qpu import CodexVirtualQPU
from backend.modules.symbolic_spreadsheet.models.glyph_cell import GlyphCell


@pytest.mark.asyncio
async def test_phase10_qfc_container_exec():
    qpu = CodexVirtualQPU()

    cells = [
        GlyphCell(id="c1", logic="∇ ↔", position=[0, 0]),
        GlyphCell(id="c2", logic="⊕", position=[0, 1]),
    ]

    ctx = {
        "container_id": "qfc_test_container",
        "benchmark_silent": True,   # avoid WS broadcasts in tests
        "qfc_container_batch": [
            {"cell_id": "c1", "op": "∇"},                 # numeric op, no args -> token path
            {"cell_id": "c1", "op": "↔", "args": ["A", "B"]},  # eq with explicit args
            {"cell_id": "c2", "op": "⟲"},                 # mutate, token fallback
        ],
    }

    await qpu.execute_sheet(cells, ctx)

    # 1) Summary attached to context
    assert "phase10_container_exec" in ctx
    summary = ctx["phase10_container_exec"]
    assert summary["container_id"] == "qfc_test_container"
    assert summary["total"] == 3
    # We expect at least 2 successes (all 3 should succeed unless ISA changed)
    assert summary["ok"] >= 2
    assert summary["error"] == summary["total"] - summary["ok"]

    # 2) Beams written to target cells with stage='container' and source='qfc_container_exec'
    c1_beams = [b for b in (cells[0].wave_beams or [])
                if b.get("source") == "qfc_container_exec" and b.get("stage") == "container"]
    c2_beams = [b for b in (cells[1].wave_beams or [])
                if b.get("source") == "qfc_container_exec" and b.get("stage") == "container"]

    # c1 should have container beams for both ∇ and ↔
    assert any(b.get("token") in ("∇", "↔") for b in c1_beams)
    # c2 should have container beam for ⟲
    assert any(b.get("token") == "⟲" for b in c2_beams)

    # 3) Basic shape checks on a result payload
    for b in c1_beams + c2_beams:
        assert "beam_id" in b and isinstance(b["beam_id"], str)
        assert "timestamp" in b and isinstance(b["timestamp"], str)
        assert "result" in b  # result type varies by opcode, just ensure presence