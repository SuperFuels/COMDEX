import pytest, json
from pathlib import Path
from fastapi.testclient import TestClient
from backend.main import app
from backend.modules.runtime.container_runtime import safe_load_container_by_id

client = TestClient(app)

def _make_container(cid: str) -> Path:
    pdir = Path("backend/modules/dimensions/containers"); pdir.mkdir(parents=True, exist_ok=True)
    cpath = pdir / f"{cid}.dc.json"
    cpath.write_text(json.dumps({"id": cid, "type":"dc","glyphs":[],"symbolic_logic":[],"thought_tree":[]}, indent=2))
    return cpath

def _copy_prelude(dst_lean: Path):
    prelude_src = Path("backend/modules/lean/symatics_prelude.lean")
    (dst_lean.parent / "symatics_prelude.lean").write_text(prelude_src.read_text())

@pytest.mark.asyncio
async def test_inject_symatics_interference_axioms_roundtrip():
    container_path = _make_container("symatics_axioms")
    lean_path = Path("tmp") / "symatics_axioms.lean"
    lean_path.parent.mkdir(exist_ok=True)
    lean_path.write_text(
        "import ./symatics_prelude\n\n"
        "axiom comm_phi     : (A ⋈[φ] B) ↔ (B ⋈[-φ] A)\n"
        "axiom self_pi_bot  : (A ⋈[π] A) ↔ ⊥\n"
        "axiom self_zero_id : (A ⋈[0] A) ↔ A\n"
        "axiom non_idem     : ∀ φ, φ != 0 ∧ φ != π -> (A ⋈[φ] A) != A\n"
        "axiom neutral_phi  : (A ⋈[φ] ⊥) ↔ A\n"
        "axiom no_distrib   : ¬(((A ⋈[φ] B) ∧ C) ↔ ((A ∧ C) ⋈[φ] (B ∧ C)))\n"
    )
    _copy_prelude(lean_path)

    with open(lean_path, "rb") as f:
        resp = client.post(
            "/api/lean/inject",
            data={"container_path": str(container_path), "normalize":"true","auto_clean":"true"},
            files={"lean_file": ("symatics_axioms.lean", f, "text/plain")},
        )
    assert resp.status_code == 200, resp.text

    updated = safe_load_container_by_id(str(container_path))
    entries = {e["name"]: e for e in updated.get("symbolic_logic", [])}

    expected = {
        "comm_phi":     "(A ⋈[φ] B) ↔ (B ⋈[-φ] A)",
        "self_pi_bot":  "(A ⋈[π] A) ↔ ⊥",
        "self_zero_id": "(A ⋈[0] A) ↔ A",
        "non_idem":     "∀ φ, φ != 0 ∧ φ != π -> (A ⋈[φ] A) != A",
        "neutral_phi":  "(A ⋈[φ] ⊥) ↔ A",
        "no_distrib":   "¬(((A ⋈[φ] B) ∧ C) ↔ ((A ∧ C) ⋈[φ] (B ∧ C)))",
    }

    # Exact roundtrip on logic, logic_raw, symbolicProof
    for name, expected_logic in expected.items():
        e = entries[name]
        for k in ("logic", "logic_raw", "symbolicProof"):
            assert e.get(k) == expected_logic, f"{name}.{k} != {expected_logic!r}: {e.get(k)!r}"
        assert e.get("symbol") == "⟦ Axiom ⟧"

lean_path = Path("tmp") / "symatics_axioms.lean"
lean_path.parent.mkdir(exist_ok=True)
lean_path.write_text(
    "import ./symatics_prelude\n\n"
    "axiom comm_phi     : (A ⋈[φ] B) ↔ (B ⋈[-φ] A)\n"
    ...
)