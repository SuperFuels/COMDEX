# backend/modules/codex/tests/test_v38_entanglement_eid.py

from backend.modules.codex.container_exec import execute_qfc_container_beams
from backend.modules.symbolic_spreadsheet.models.glyph_cell import GlyphCell

def _eid_from_cell_beams(cell: GlyphCell):
    # op_EQ appends beams containing "eid"
    beams = getattr(cell, "wave_beams", []) or []
    eids = [b.get("eid") for b in beams if b.get("token") == "↔" and b.get("eid")]
    return eids[-1] if eids else None

def test_v38_eid_deterministic_same_run_id():
    # Two cells, same logic signature => should compute same eid bucket for same sheet_run_id
    c1 = GlyphCell(id="c1", logic="⊕ ↔ ⟲ -> ✦ ∇ ∇c", position=[0, 0])
    c2 = GlyphCell(id="c2", logic="⊕ ↔ ⟲ -> ✦ ∇ ∇c", position=[0, 1])

    context = {"sheet_run_id": "run_001"}

    # Batch: run ↔ at container scope (no args is fine; op_EQ still emits beams + EID)
    batch = [
        {"cell_id": "c1", "op": "↔"},
        {"cell_id": "c2", "op": "↔"},
    ]

    summary = execute_qfc_container_beams("maxwell_core", [c1, c2], batch, context)

    eid1 = _eid_from_cell_beams(c1)
    eid2 = _eid_from_cell_beams(c2)

    assert summary["ok"] == 2
    assert eid1 is not None and eid2 is not None
    assert eid1 == eid2, (eid1, eid2)

    # entanglements_map should include both cell ids under the same eid
    ent_map = context.get("entanglements_map", {})
    assert eid1 in ent_map
    assert "c1" in ent_map[eid1]
    assert "c2" in ent_map[eid1]

def test_v38_eid_changes_with_run_id():
    c = GlyphCell(id="c1", logic="⊕ ↔ ⟲ -> ✦ ∇ ∇c", position=[0, 0])

    ctx_a = {"sheet_run_id": "run_A"}
    ctx_b = {"sheet_run_id": "run_B"}

    execute_qfc_container_beams("maxwell_core", [c], [{"cell_id": "c1", "op": "↔"}], ctx_a)
    eid_a = _eid_from_cell_beams(c)

    # clear beams so we don't read the previous eid
    c.wave_beams = []
    execute_qfc_container_beams("maxwell_core", [c], [{"cell_id": "c1", "op": "↔"}], ctx_b)
    eid_b = _eid_from_cell_beams(c)

    assert eid_a != eid_b