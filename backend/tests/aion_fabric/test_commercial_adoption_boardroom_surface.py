from pathlib import Path


APP = (Path(__file__).resolve().parents[3] / "desktop" / "mac" / "src" / "app.js").read_text(encoding="utf-8")


def test_boardroom_exposes_customer_owned_department_and_value_controls():
    assert 'data-aion-commercial-adoption="true"' in APP
    assert "Departments, usage and value" in APP
    assert "Your brain, memory, local models, backup and export remain yours" in APP
    assert "Start 30-day trial" in APP
    assert "No automatic renewal is enabled here" in APP
    assert "Private value evidence" in APP


def test_boardroom_uses_mother_brain_api_and_requires_explicit_cancel_confirmation():
    assert "/api/aion/business/commercial/trials/start" in APP
    assert "/api/aion/business/commercial/trials/${encodeURIComponent(trialId)}/cancel" in APP
    assert 'window.confirm("Cancel this department service?' in APP
    assert "auto_renew: false" in APP
    assert 'actor_id: "boardroom_owner"' not in APP
    assert "getAionStage8Actor?.().person_id" in APP
