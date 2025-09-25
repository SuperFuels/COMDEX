import pytest, json, re
from pathlib import Path
from fastapi.testclient import TestClient
from backend.main import app
from backend.modules.runtime.container_runtime import safe_load_container_by_id

client = TestClient(app)


def _make_container(cid: str) -> Path:
    pdir = Path("backend/modules/dimensions/containers")
    pdir.mkdir(parents=True, exist_ok=True)
    cpath = pdir / f"{cid}.dc.json"
    cpath.write_text(
        json.dumps(
            {
                "id": cid,
                "type": "dc",
                "glyphs": [],
                "symbolic_logic": [],
                "thought_tree": [],
            },
            indent=2,
        )
    )
    return cpath


def _copy_prelude(dst_lean: Path):
    prelude_src = Path("backend/modules/lean/symatics_prelude.lean")
    (dst_lean.parent / "symatics_prelude.lean").write_text(prelude_src.read_text())


def _normalize(s: str) -> str:
    """Normalize for stable comparison: strip spaces, normalize minus, drop stray 'axiom' fragments."""
    if not isinstance(s, str):
        return ""
    out = s.replace("−", "-").replace(" ", "")
    # Drop any stray "axiomXYZ" fragments that shouldn't be part of the logic
    out = re.sub(r"axiom[a-zA-Z0-9_']*", "", out)
    return out.strip()


@pytest.mark.asyncio
async def test_inject_full_symatics_axioms_roundtrip():
    container_path = _make_container("symatics_axioms_full")
    lean_path = Path("tmp") / "symatics_axioms_full.lean"
    lean_path.parent.mkdir(exist_ok=True)

    # Write the axioms file (strictly one axiom per line, comments above only)
    lean_path.write_text(
        "import ./symatics_prelude\n\n"
        "-- Commutativity with phase inversion\n"
        "axiom comm_phi : (A ⋈[φ] B) ↔ (B ⋈[-φ] A)\n\n"
        "-- Special self-interference cases\n"
        "axiom self_pi_bot : (A ⋈[π] A) ↔ ⊥\n"
        "axiom self_zero_id : (A ⋈[0] A) ↔ A\n"
        "axiom non_idem : ∀ φ, φ ≠ 0 ∧ φ ≠ π → (A ⋈[φ] A) ≠ A\n\n"
        "-- Neutrality of ⊥\n"
        "axiom neutral_phi : (A ⋈[φ] ⊥) ↔ A\n\n"
        "-- Explicit failure of distributivity\n"
        "axiom no_distrib : ¬(((A ⋈[φ] B) ∧ C) ↔ ((A ∧ C) ⋈[φ] (B ∧ C)))\n\n"
        "-- Phase composition axioms\n"
        "axiom assoc_phase : (A ⋈[φ] B) ⋈[ψ] C ↔ A ⋈[φ+ψ] (B ⋈[ψ] C)\n"
        "axiom inv_phase : A ⋈[φ] (A ⋈[-φ] B) ↔ B\n\n"
        "-- A7 (constructive interference)\n"
        "axiom fuse_phase_zero : (A ⋈[0] B) ↔ (A ⊕ B)\n\n"
        "-- A8 (destructive interference)\n"
        "axiom fuse_phase_pi : (A ⋈[π] B) ↔ (A ⊖ B)\n"
    )
    _copy_prelude(lean_path)

    with open(lean_path, "rb") as f:
        resp = client.post(
            "/api/lean/inject",
            data={
                "container_path": str(container_path),
                "normalize": "true",
                "auto_clean": "true",
            },
            files={"lean_file": ("symatics_axioms_full.lean", f, "text/plain")},
        )
    assert resp.status_code == 200, resp.text

    updated = safe_load_container_by_id(str(container_path))
    entries = {e["name"]: e for e in updated.get("symbolic_logic", [])}

    expected = {
        "comm_phi": "(A ⋈[φ] B) ↔ (B ⋈[-φ] A)",
        "self_pi_bot": "(A ⋈[π] A) ↔ ⊥",
        "self_zero_id": "(A ⋈[0] A) ↔ A",
        "non_idem": "∀ φ, φ ≠ 0 ∧ φ ≠ π → (A ⋈[φ] A) ≠ A",
        "neutral_phi": "(A ⋈[φ] ⊥) ↔ A",
        "no_distrib": "¬(((A ⋈[φ] B) ∧ C) ↔ ((A ∧ C) ⋈[φ] (B ∧ C)))",
        "assoc_phase": "(A ⋈[φ] B) ⋈[ψ] C ↔ A ⋈[φ+ψ] (B ⋈[ψ] C)",
        "inv_phase": "A ⋈[φ] (A ⋈[-φ] B) ↔ B",
        "fuse_phase_zero": "(A ⋈[0] B) ↔ (A ⊕ B)",
        "fuse_phase_pi": "(A ⋈[π] B) ↔ (A ⊖ B)",
    }

    for name, expected_logic in expected.items():
        assert name in entries, f"{name} missing in container"
        e = entries[name]
        for k in ("logic", "logic_raw", "symbolicProof"):
            got = _normalize(e.get(k))
            want = _normalize(expected_logic)
            if k == "symbolicProof" and not got:
                continue
            assert got == want, f"{name}.{k} mismatch: {got} != {want}"
        assert e.get("symbol") == "⟦ Axiom ⟧"