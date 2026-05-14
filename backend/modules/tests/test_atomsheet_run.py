# ===============================
# 📄 test_atomsheet_run.py
# ===============================
import asyncio
from backend.modules.atomsheets.atomsheet_engine import load_atom, execute_sheet, to_dc_json
from backend.modules.atomsheets.models import AtomSheet, GlyphCell

async def run_test():
    # --- Create a fake sheet in memory ---
    cells = {
        "c1": GlyphCell(id="c1", logic="Φ = ψ ⊕ 1", position=[0, 0, 0, 0]),
        "c2": GlyphCell(id="c2", logic="Φ = Φ ⊗ ψ", position=[1, 0, 0, 0]),
    }

    sheet = AtomSheet(id="test_sheet_001", title="Symatics Test", cells=cells)
    print(f"Loaded sheet: {sheet.id}, cells={list(sheet.cells.keys())}")

    # --- Execute sheet (SymaticQPU should activate automatically if available) ---
    ctx = {"expand_nested": False}
    results = await execute_sheet(sheet, ctx)

    print("\n✅ Execution Results:")
    for cid, res in results.items():
        print(f"  {cid}: {res}")

    # --- Inspect resonance metrics ---
    print("\n📡 Resonance Metrics:")
    for cid, c in sheet.cells.items():
        print(
            f"  Cell {cid}: Φ={getattr(c, 'Φ_mean', None)}, ψ={getattr(c, 'ψ_mean', None)}, coherence={getattr(c, 'coherence_energy', None)}"
        )

    # --- Export snapshot ---
    snapshot = to_dc_json(sheet)
    print("\n🧾 Export Snapshot:")
    print(snapshot)


# Run the async test
if __name__ == "__main__":
    asyncio.run(run_test())