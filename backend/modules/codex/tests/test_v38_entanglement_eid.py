from backend.modules.codex.hardware.symbolic_qpu_isa import execute_qpu_opcode
from backend.modules.symbolic_spreadsheet.models.glyph_cell import GlyphCell

def _first_eid(cell: GlyphCell) -> str:
    beams = getattr(cell, "wave_beams", []) or []
    eids = [b.get("eid") for b in beams if b.get("token") == "↔" and b.get("eid")]
    assert eids, f"No EID beams found. beams={beams}"
    return eids[0]

def _stages(cell: GlyphCell) -> set[str]:
    beams = getattr(cell, "wave_beams", []) or []
    return {b.get("stage") for b in beams if b.get("token") == "↔"}

def test_eid_deterministic_same_run_same_logic():
    cell1 = GlyphCell(id="c1", logic="⊕ ↔ ⟲", position=[0,0])
    ctx1 = {"sheet_run_id": "runA"}
    execute_qpu_opcode("↔", ["x", "y"], cell1, ctx1)
    eid1 = _first_eid(cell1)

    cell2 = GlyphCell(id="c1", logic="⊕ ↔ ⟲", position=[0,0])
    ctx2 = {"sheet_run_id": "runA"}
    execute_qpu_opcode("↔", ["x", "y"], cell2, ctx2)
    eid2 = _first_eid(cell2)

    assert eid1 == eid2
    assert "entanglements_map" in ctx1
    assert eid1 in ctx1["entanglements_map"]
    assert "c1" in ctx1["entanglements_map"][eid1]

def test_eid_changes_with_run_id():
    cellA = GlyphCell(id="c1", logic="⊕ ↔ ⟲", position=[0,0])
    ctxA = {"sheet_run_id": "runA"}
    execute_qpu_opcode("↔", ["x", "y"], cellA, ctxA)
    eidA = _first_eid(cellA)

    cellB = GlyphCell(id="c1", logic="⊕ ↔ ⟲", position=[0,0])
    ctxB = {"sheet_run_id": "runB"}
    execute_qpu_opcode("↔", ["x", "y"], cellB, ctxB)
    eidB = _first_eid(cellB)

    assert eidA != eidB

def test_op_eq_emits_staged_beams():
    cell = GlyphCell(id="c1", logic="↔", position=[0,0])
    ctx = {"sheet_run_id": "runA"}
    execute_qpu_opcode("↔", ["x", "y"], cell, ctx)

    stages = _stages(cell)
    for s in ("entangle", "predict", "ingest", "collapse"):
        assert s in stages
