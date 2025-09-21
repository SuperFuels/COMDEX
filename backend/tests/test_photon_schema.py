import json
import logging
import pytest
from backend.modules.photon.photon_to_codex import photon_to_codex

def test_schema_accepts_new_glyphs_format():
    capsule = {
        "name": "ok",
        "glyphs": [
            {"operator": "⊕", "args": ["a", "b"], "name": "superpose"}
        ]
    }
    out = photon_to_codex(capsule, capsule_id="t1")
    assert out["glyphs"] and out["scroll"].startswith("⊕(")

def test_schema_accepts_legacy_steps_and_warns(caplog):
    caplog.set_level(logging.WARNING)
    capsule = {
        "name": "legacy",
        "steps": [
            {"symbol": "μ", "value": "measure", "args": ["x"]}
        ]
    }
    out = photon_to_codex(capsule, capsule_id="t2")
    assert out["glyphs"]
    assert any("Legacy capsule format detected" in r.message for r in caplog.records)

def test_schema_rejects_bad_capsule_when_jsonschema_available(monkeypatch):
    # Force validator on if installed; otherwise skip
    try:
        import jsonschema  # noqa
    except Exception:
        pytest.skip("jsonschema not installed")

    bad = {"name": "oops", "glyphs": [{"args": ["a"]}]}  # missing 'operator'
    with pytest.raises(ValueError):
        photon_to_codex(bad, capsule_id="t3")