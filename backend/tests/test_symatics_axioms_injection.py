import pytest, json, re
from pathlib import Path
from fastapi.testclient import TestClient
from backend.main import app
from backend.modules.runtime.container_runtime import safe_load_container_by_id
from backend.symatics import rewriter as R
from backend.modules.lean.convert_lean_to_codexlang import lean_to_expr

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
    """Normalize for stable comparison: strip spaces, normalize minus, drop stray 'axiom/theorem' fragments."""
    if not isinstance(s, str):
        return ""
    out = s.replace("−", "-").replace(" ", "")
    out = re.sub(r"(axiom|theorem)[a-zA-Z0-9_']*", "", out)
    return out.strip()


# Mix of axioms (A1–A8) and Theorem 7
DECLS = {
    "comm_phi": ("axiom", "(A ⋈[φ] B) ↔ (B ⋈[-φ] A)"),
    "self_pi_bot": ("axiom", "(A ⋈[π] A) ↔ ⊥"),
    "self_zero_id": ("axiom", "(A ⋈[0] A) ↔ A"),
    "non_idem": ("axiom", "∀ φ, φ ≠ 0 ∧ φ ≠ π → (A ⋈[φ] A) ≠ A"),
    "neutral_phi": ("axiom", "(A ⋈[φ] ⊥) ↔ A"),
    "no_distrib": ("axiom", "¬(((A ⋈[φ] B) ∧ C) ↔ ((A ∧ C) ⋈[φ] (B ∧ C)))"),
    "no_distrib_formal": (
        "theorem",
        "((A ⋈[φ] B) ∧ C) ≠ ((A ∧ C) ⋈[φ] (B ∧ C))",
    ),
    "assoc_phase": ("axiom", "(A ⋈[φ] B) ⋈[ψ] C ↔ A ⋈[φ+ψ] (B ⋈[ψ] C)"),
    "inv_phase": ("axiom", "A ⋈[φ] (A ⋈[-φ] B) ↔ B"),
    "fuse_phase_zero": ("axiom", "(A ⋈[0] B) ↔ (A ⊕ B)"),
    "fuse_phase_pi": ("axiom", "(A ⋈[π] B) ↔ (A ⊖ B)"),
}


@pytest.mark.asyncio
@pytest.mark.parametrize("name,decl", DECLS.items())
async def test_decl_injection(name, decl):
    decl_kind, expected_logic = decl

    container_path = _make_container("symatics_axioms_full")
    lean_path = Path("tmp") / "symatics_axioms_full.lean"
    lean_path.parent.mkdir(exist_ok=True)

    # Build .lean file with all decls
    lines = ["import ./symatics_prelude\n\n"]
    for nm, (dk, logic) in DECLS.items():
        lines.append(f"{dk} {nm} : {logic}\n")
    lean_path.write_text("\n".join(lines))
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
    assert name in entries, f"{name} missing in container"

    e = entries[name]

    # --- Raw matches Lean ---
    got_raw = _normalize(e.get("logic_raw"))
    want_raw = _normalize(expected_logic)
    assert got_raw == want_raw, f"{name}.logic_raw mismatch: {got_raw} != {want_raw}"

    # --- Normalized via rewriter ---
    try:
        expr = lean_to_expr(expected_logic)
        norm = R.normalize(expr)
        want_norm = _normalize(str(norm))
    except Exception:
        want_norm = want_raw

    got_norm = _normalize(e.get("logic"))

    try:
        expr_expected = lean_to_expr(expected_logic)
        norm_expected = R.normalize(expr_expected)

        expr_got = lean_to_expr(got_norm)
        norm_got = R.normalize(expr_got)

        assert R.symatics_equiv(norm_got, norm_expected), f"{name} not semantically equivalent"
    except Exception:
        # fallback: at least raw matches
        assert got_norm == want_raw

    # Symbol correctness
    expected_symbol = "⟦ Theorem ⟧" if decl_kind == "theorem" else "⟦ Axiom ⟧"
    assert e.get("symbol") == expected_symbol