import pytest
import json
from pathlib import Path
from fastapi.testclient import TestClient
from backend.main import app
from backend.modules.runtime.container_runtime import safe_load_container_by_id

client = TestClient(app)


def _make_container(container_id: str) -> Path:
    container_dir = Path("backend/modules/dimensions/containers")
    container_dir.mkdir(parents=True, exist_ok=True)
    container_path = container_dir / f"{container_id}.dc.json"

    container = {
        "id": container_id,
        "type": "dc",
        "glyphs": [],
        "symbolic_logic": [],
        "thought_tree": []
    }
    container_path.write_text(json.dumps(container, indent=2))
    return container_path


def _copy_prelude(lean_path: Path):
    prelude_src = Path("backend/modules/lean/symatics_prelude.lean")
    prelude_dst = lean_path.parent / "symatics_prelude.lean"
    prelude_dst.write_text(prelude_src.read_text())


# ---------------------------------------------------------------------
# Existing XOR and NAND tests
# ---------------------------------------------------------------------

@pytest.mark.asyncio
async def test_inject_xor_axiom_into_real_container():
    container_path = _make_container("xor_axiom")

    lean_path = Path("tmp") / "xor_axiom.lean"
    lean_path.parent.mkdir(exist_ok=True)
    lean_path.write_text(
        "import ./symatics_prelude\n\n"
        "axiom xor_axiom : (A ⊕ B) -> (B ⊕ A)\n"
    )
    _copy_prelude(lean_path)

    with open(lean_path, "rb") as f:
        resp = client.post(
            "/api/lean/inject",
            data={"container_path": str(container_path), "normalize": "true", "auto_clean": "true"},
            files={"lean_file": ("xor_axiom.lean", f, "text/plain")},
        )
    assert resp.status_code == 200, resp.text

    updated = safe_load_container_by_id(str(container_path))
    e = next(e for e in updated["symbolic_logic"] if e["name"] == "xor_axiom")
    expected_logic = "(A ⊕ B) -> (B ⊕ A)"

    # 🔒 regression checks
    assert e["logic"] == expected_logic
    assert e["logic_raw"] == expected_logic
    assert e["symbolicProof"] == expected_logic
    assert e["symbol"] == "⟦ Axiom ⟧"
    assert any("xor_axiom" in g for g in updated["glyphs"])


@pytest.mark.asyncio
async def test_inject_nand_axiom_into_real_container():
    container_path = _make_container("nand_axiom")

    lean_path = Path("tmp") / "nand_axiom.lean"
    lean_path.parent.mkdir(exist_ok=True)
    lean_path.write_text(
        "import ./symatics_prelude\n\n"
        "axiom nand_axiom : (A ↑ B) -> ¬(A ∧ B)\n"
    )
    _copy_prelude(lean_path)

    with open(lean_path, "rb") as f:
        resp = client.post(
            "/api/lean/inject",
            data={"container_path": str(container_path), "normalize": "true", "auto_clean": "true"},
            files={"lean_file": ("nand_axiom.lean", f, "text/plain")},
        )
    assert resp.status_code == 200, resp.text

    updated = safe_load_container_by_id(str(container_path))
    e = next(e for e in updated["symbolic_logic"] if e["name"] == "nand_axiom")
    expected_logic = "(A ↑ B) -> ¬(A ∧ B)"

    # 🔒 regression checks
    assert e["logic"] == expected_logic
    assert e["logic_raw"] == expected_logic
    assert e["symbolicProof"] == expected_logic
    assert e["symbol"] == "⟦ Axiom ⟧"
    assert any("nand_axiom" in g for g in updated["glyphs"])


@pytest.mark.asyncio
async def test_roundtrip_consistency():
    container_path = _make_container("xor_axiom_roundtrip")

    lean_path = Path("tmp") / "xor_axiom_roundtrip.lean"
    lean_path.parent.mkdir(exist_ok=True)
    lean_path.write_text(
        "import ./symatics_prelude\n\n"
        "axiom xor_axiom_roundtrip : (A ⊕ B) -> (B ⊕ A)\n"
    )
    _copy_prelude(lean_path)

    with open(lean_path, "rb") as f:
        resp = client.post(
            "/api/lean/inject",
            data={"container_path": str(container_path), "normalize": "true", "auto_clean": "true"},
            files={"lean_file": ("xor_axiom_roundtrip.lean", f, "text/plain")},
        )
    assert resp.status_code == 200, resp.text

    reloaded = safe_load_container_by_id(str(container_path))
    entry = next(e for e in reloaded["symbolic_logic"] if e["name"] == "xor_axiom_roundtrip")
    expected = "(A ⊕ B) -> (B ⊕ A)"

    assert entry["logic"] == expected
    assert entry["logic_raw"] == expected
    assert entry["symbolicProof"] == expected
    assert any("xor_axiom_roundtrip" in g for g in reloaded.get("glyphs", []))


@pytest.mark.asyncio
async def test_inject_nand_axiom_roundtrip():
    container_path = _make_container("nand_axiom_roundtrip")

    lean_path = Path("tmp") / "nand_axiom_roundtrip.lean"
    lean_path.parent.mkdir(exist_ok=True)
    lean_path.write_text(
        "import ./symatics_prelude\n\n"
        "axiom nand_axiom_roundtrip : (A ↑ B) -> ¬(A ∧ B)\n"
    )
    _copy_prelude(lean_path)

    with open(lean_path, "rb") as f:
        resp = client.post(
            "/api/lean/inject",
            data={"container_path": str(container_path), "normalize": "true", "auto_clean": "true"},
            files={"lean_file": ("nand_axiom_roundtrip.lean", f, "text/plain")},
        )
    assert resp.status_code == 200, resp.text

    updated = safe_load_container_by_id(str(container_path))
    e = next(e for e in updated["symbolic_logic"] if e["name"] == "nand_axiom_roundtrip")
    expected = "(A ↑ B) -> ¬(A ∧ B)"

    assert e["logic"] == expected
    assert e["logic_raw"] == expected
    assert e["symbolicProof"] == expected
    assert e["symbol"] == "⟦ Axiom ⟧"
    assert any("nand_axiom_roundtrip" in g for g in updated.get("glyphs", []))


# ---------------------------------------------------------------------
# 🔹 Parametrized tests for Symatics interference axioms
# ---------------------------------------------------------------------

@pytest.mark.asyncio
@pytest.mark.parametrize("name,axiom", [
    ("comm_phi",     "axiom comm_phi     : (A ⋈[φ] B) ↔ (B ⋈[-φ] A)"),
    ("self_pi_bot",  "axiom self_pi_bot  : (A ⋈[π] A) ↔ ⊥"),
    ("self_zero_id", "axiom self_zero_id : (A ⋈[0] A) ↔ A"),
    ("non_idem",     "axiom non_idem     : ∀ φ, φ != 0 ∧ φ != π -> (A ⋈[φ] A) != A"),
    ("neutral_phi",  "axiom neutral_phi  : (A ⋈[φ] ⊥) ↔ A"),
    ("no_distrib",   "axiom no_distrib   : ¬(((A ⋈[φ] B) ∧ C) ↔ ((A ∧ C) ⋈[φ] (B ∧ C)))"),
])
async def test_inject_each_symatics_axiom_roundtrip(name, axiom):
    container_path = _make_container(name)
    lean_path = Path("tmp") / f"{name}.lean"
    lean_path.parent.mkdir(exist_ok=True)
    lean_path.write_text(f"import ./symatics_prelude\n\n{axiom}\n")
    _copy_prelude(lean_path)

    with open(lean_path, "rb") as f:
        resp = client.post(
            "/api/lean/inject",
            data={"container_path": str(container_path), "normalize": "true", "auto_clean": "true"},
            files={"lean_file": (f"{name}.lean", f, "text/plain")},
        )
    assert resp.status_code == 200, resp.text

    updated = safe_load_container_by_id(str(container_path))
    e = next(e for e in updated["symbolic_logic"] if e["name"] == name)

    # 🔒 Full roundtrip checks
    expected_logic = axiom.split(":", 1)[1].strip()
    for k in ("logic", "logic_raw", "symbolicProof"):
        assert e.get(k) == expected_logic, f"{name}.{k} mismatch: {e.get(k)!r}"
    assert e.get("symbol") == "⟦ Axiom ⟧"
    assert any(name in g for g in updated.get("glyphs", []))


@pytest.mark.asyncio
async def test_inject_symatics_axioms_batch_roundtrip():
    """
    Stress test: inject all 6 Symatics axioms from one Lean file into one container.
    Ensures the system can handle composite Symatics theories in a single batch.
    """
    container_path = _make_container("symatics_axioms_batch")

    lean_path = Path("tmp") / "symatics_axioms_batch.lean"
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

    # Inject in one go
    with open(lean_path, "rb") as f:
        resp = client.post(
            "/api/lean/inject",
            data={"container_path": str(container_path), "normalize": "true", "auto_clean": "true"},
            files={"lean_file": ("symatics_axioms_batch.lean", f, "text/plain")},
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

    # 🔒 Check every axiom made it through
    for name, expected_logic in expected.items():
        assert name in entries, f"{name} missing from container"
        e = entries[name]
        for k in ("logic", "logic_raw", "symbolicProof"):
            assert e.get(k) == expected_logic, f"{name}.{k} != {expected_logic!r}: {e.get(k)!r}"
        assert e.get("symbol") == "⟦ Axiom ⟧"

    # Glyphs should mention every axiom name
    glyphs = " ".join(updated.get("glyphs", []))
    for name in expected.keys():
        assert name in glyphs, f"{name} missing from glyphs"