import pytest

from backend.modules.symbolic_spreadsheet.models.glyph_cell import GlyphCell
from backend.modules.codex.codex_virtual_qpu import CodexVirtualQPU

# Phase 9 helpers
from backend.modules.codex._4d_dreams import (
    project_dreams_for_cell,
    prune_dreams_by_sqi,
    build_timeline_snapshot,
    DreamConfig,
)


@pytest.mark.asyncio
async def test_phase9_projects_k_dreams_per_cell():
    """
    Integration: execute_sheet with phase9_enabled should attach exactly k dream beams per cell.
    """
    qpu = CodexVirtualQPU()
    cells = [GlyphCell(id="c0", logic="⊕ ↔ ✦", position=[0, 0])]
    ctx = {
        "container_id": "phase9_it",
        "benchmark_silent": True,     # don't broadcast
        "phase9_enabled": True,
        "phase9_k": 3,
        # keep default stage="dream"
    }

    await qpu.execute_sheet(cells, ctx)

    dreams = [b for b in getattr(cells[0], "wave_beams", []) if b.get("stage") == "dream"]
    assert len(dreams) == 3
    for d in dreams:
        assert d.get("beam_id")
        assert d.get("timestamp")
        assert d.get("stage") == "dream"


def test_phase9_pruning_marks_low_sqi_as_pruned():
    """
    Unit: project -> prune. If sqi_score < min_sqi, dream beams should be marked 'pruned'.
    """
    cell = GlyphCell(id="p0", logic="↔", position=[0, 0])
    cell.sqi_score = 0.40  # force low SQI
    ctx = {"entanglements_map": {"eid::t::1": {"p0"}}}

    # project k=2 to be quick
    cfg = DreamConfig(k_variants=2, min_sqi_keep=0.60, stage_name="dream")
    dreams = project_dreams_for_cell(cell, ctx, cfg)
    assert len(dreams) == 2

    prune_dreams_by_sqi(cell, min_sqi=0.60, stage_name="dream")
    dream_states = {b.get("state") for b in cell.wave_beams if b.get("stage") == "dream"}
    assert "pruned" in dream_states


def test_phase9_timeline_sorted_and_eids_propagate():
    """
    Unit: build_timeline_snapshot returns time-sorted stream and carries EIDs on dream beams.
    """
    c0 = GlyphCell(id="a0", logic="⊕ ↔", position=[0, 0])
    c1 = GlyphCell(id="a1", logic="⊕ ↔", position=[0, 1])

    # Inject entanglement membership so dreams get entanglement_ids
    ctx = {"entanglements_map": {"eid::run::X": {"a0", "a1"}}}

    # project some dreams
    project_dreams_for_cell(c0, ctx, DreamConfig(k_variants=2))
    project_dreams_for_cell(c1, ctx, DreamConfig(k_variants=2))

    timeline = build_timeline_snapshot([c0, c1], ctx)

    # Check it's already sorted by (timestamp, beam_id)
    sorted_copy = sorted(
        timeline,
        key=lambda x: (str(x.get("timestamp") or ""), str(x.get("beam_id") or "")),
    )
    assert timeline == sorted_copy

    # Ensure at least some entries have a non-None EID (dream beams should)
    dream_eids = [t.get("eid") for t in timeline if t.get("stage") == "dream"]
    assert any(eid is not None for eid in dream_eids)


@pytest.mark.asyncio
async def test_phase9_execute_sheet_respects_k_variants_flag():
    """
    Integration: override k via context and verify count.
    """
    qpu = CodexVirtualQPU()
    cells = [GlyphCell(id="v0", logic="⊕ ↔ ✦", position=[0, 0])]
    ctx = {
        "container_id": "phase9_k_override",
        "benchmark_silent": True,
        "phase9_enabled": True,
        "phase9_k": 4,  # override default
    }

    await qpu.execute_sheet(cells, ctx)

    dreams = [b for b in getattr(cells[0], "wave_beams", []) if b.get("stage") == "dream"]
    assert len(dreams) == 4