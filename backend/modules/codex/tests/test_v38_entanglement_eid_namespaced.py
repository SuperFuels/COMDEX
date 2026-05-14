from backend.modules.codex.hardware.symbolic_qpu_isa import execute_qpu_opcode
from backend.modules.symbolic_spreadsheet.models.glyph_cell import GlyphCell

def test_namespaced_logic_eq_hits_op_eq_and_emits_eid():
    cell = GlyphCell(id="c1", logic="↔", position=[0,0])
    ctx = {"sheet_run_id": "runA"}

    execute_qpu_opcode("logic:↔", ["x", "y"], cell, ctx)

    beams = getattr(cell, "wave_beams", []) or []
    eids = [b.get("eid") for b in beams if b.get("token") == "↔" and b.get("eid")]
    assert eids, f"Expected EID beams for logic:↔, beams={beams}"
