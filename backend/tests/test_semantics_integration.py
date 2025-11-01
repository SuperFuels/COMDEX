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
            data={
                "container_path": str(container_path),
                "normalize": "true",
                "auto_clean": "true",
            },
            files={"lean_file": ("xor_axiom.lean", f, "text/plain")},
        )
    assert resp.status_code == 200, resp.text

    updated = safe_load_container_by_id(str(container_path))
    entries = updated.get("symbolic_logic", [])

    print("\n[DEBUG] symbolic_logic entries:", json.dumps(entries, indent=2, ensure_ascii=False))

    e = next(e for e in entries if e.get("name") == "xor_axiom")
    logic_str = e.get("logic")

    print(f"[DEBUG] xor_axiom.logic = {logic_str!r}")

    assert logic_str, "Logic string is empty or missing"
    # ✅ exact match instead of just checking symbols
    assert logic_str == "(A ⊕ B) -> (B ⊕ A)", f"Unexpected logic: {logic_str}"
    assert e.get("symbol") == "⟦ Axiom ⟧"

    glyphs = updated.get("glyphs", [])
    assert any("xor_axiom" in g for g in glyphs)


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
            data={
                "container_path": str(container_path),
                "normalize": "true",
                "auto_clean": "true",
            },
            files={"lean_file": ("nand_axiom.lean", f, "text/plain")},
        )
    assert resp.status_code == 200, resp.text

    updated = safe_load_container_by_id(str(container_path))
    entries = updated.get("symbolic_logic", [])

    print("\n[DEBUG] symbolic_logic entries:", json.dumps(entries, indent=2, ensure_ascii=False))

    e = next(e for e in entries if e.get("name") == "nand_axiom")
    logic_str = e.get("logic")

    print(f"[DEBUG] nand_axiom.logic = {logic_str!r}")

    assert logic_str, "Logic string is empty or missing"
    # ✅ exact match
    assert logic_str == "(A ↑ B) -> ¬(A ∧ B)", f"Unexpected logic: {logic_str}"
    assert e.get("symbol") == "⟦ Axiom ⟧"

    glyphs = updated.get("glyphs", [])
    assert any("nand_axiom" in g for g in glyphs)