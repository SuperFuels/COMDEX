import json
import pytest
from pathlib import Path

@pytest.mark.parametrize("axiom_name,lean_code,formula", [
    (
        "xor_axiom",
        """\
import ./symatics_prelude
axiom xor_axiom : (A ⊕ B) → (B ⊕ A)
""",
        "(A ⊕ B) → (B ⊕ A)"
    ),
    (
        "nand_axiom",
        """\
import ./symatics_prelude
axiom nand_axiom : (A ↑ B) → ¬(A ∧ B)
""",
        "(A ↑ B) → ¬(A ∧ B)"
    ),
])
def test_symatics_prelude_snapshot(tmp_path, client, axiom_name, lean_code, formula):
    # 1) Prepare minimal container file
    container_path = tmp_path / f"{axiom_name}_container.dc.json"
    container_dict = {
        "id": axiom_name,
        "type": "dc",
        "logic": [],
        "atoms": {},
        "glyphs": []
    }
    container_path.write_text(json.dumps(container_dict, indent=2))

    # 2) Write Lean file
    lean_path = tmp_path / f"{axiom_name}.lean"
    lean_path.write_text(lean_code)

    # 3) Inject axiom into container
    resp = client.post(
        "/api/lean/inject?report=json",
        data={"container_path": str(container_path)},
        files={"lean_file": (lean_path.name, lean_path.read_bytes(), "text/plain")},
    )
    assert resp.status_code == 200, resp.text

    # 4) Reload container via runtime
    from backend.modules.runtime.container_runtime import ContainerRuntime
    loaded = ContainerRuntime.load_container_from_path(str(container_path))

    # 5) Check snapshot: logic entry should contain the axiom
    logic_entries = loaded.get("logic", [])
    assert any(entry.get("name") == axiom_name for entry in logic_entries), (
        f"{axiom_name} not found in container logic: {logic_entries}"
    )
    assert any(formula in entry.get("formula", "") for entry in logic_entries), (
        f"Expected formula '{formula}' not found in logic entries"
    )