import json
from backend.modules.lean import lean_audit, lean_report

def test_audit_event_includes_validation_errors():
    errors = [{"code": "E001", "message": "Logic inconsistency"}]
    evt = lean_audit.build_inject_event(
        container_path="c.json",
        container_id="c1",
        lean_path="dummy.lean",
        num_items=1,
        previews=["⊢ A -> B"],
        validation_errors=errors,
    )
    assert "validation_errors" in evt
    assert evt["validation_errors"][0]["code"] == "E001"


def test_report_includes_validation_errors():
    container = {
        "id": "c1",
        "type": "dc",
        "counts": {"logic": 1},
        "validation_errors": [{"code": "E002", "message": "Broken axiom"}],
        "previews": ["⊢ trivial"],
    }
    md = lean_report.render_report(container, fmt="md")
    assert "Validation Errors" in md
    assert "E002" in md
    j = lean_report.render_report(container, fmt="json")
    parsed = json.loads(j)
    assert parsed["validation_errors"][0]["code"] == "E002"