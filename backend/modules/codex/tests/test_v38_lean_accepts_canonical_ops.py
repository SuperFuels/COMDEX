from backend.modules.lean.lean_utils import validate_logic_trees, normalize_validation_errors

def test_lean_accepts_logic_equiv_canonical():
    container_stub = {
        "symbolic_logic": [
            {"op": "logic:↔", "args": ["A", "B"]}
        ]
    }
    errs = normalize_validation_errors(validate_logic_trees(container_stub))
    assert not errs, f"Lean rejected canonical logic:↔ form: {errs}"
