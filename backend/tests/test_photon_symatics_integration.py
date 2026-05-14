# 📁 backend/tests/test_photon_symatics_integration.py
import json
import pytest
from pathlib import Path
from backend.modules.codex.codex_executor import execute_photon_capsule

# 🚀 Symatics capsule (algebraic, schema-valid)
SYM_CAPSULE = {
    "name": "sym_capsule",
    "glyphs": [
        {"operator": "⊕", "args": ["a", "b"], "name": "superpose"},
        {"operator": "μ", "args": ["x"], "name": "measure"},
    ],
}

# 🚀 Codex fallback capsule (no algebra, schema-valid)
CODEX_CAPSULE = {
    "name": "codex_capsule",
    "glyphs": [
        {"operator": "+", "args": ["1", "2"], "name": "add"},
    ],
}

# 🚀 Legacy capsule with "steps" field (pre-schema format)
LEGACY_STEPS_CAPSULE = {
    "name": "legacy_steps_capsule",
    "steps": [
        {"symbol": "⊕", "value": "a", "args": ["a", "b"]},
        {"symbol": "μ", "value": "x", "args": ["x"]},
    ],
}


# ──────────────────────────────
# Tests
# ──────────────────────────────

def test_body_capsule_migration(caplog):
    caplog.set_level("WARNING")
    capsule = {
        "name": "body_capsule",
        "body": [{"operator": "+", "args": ["2", "3"], "name": "add"}],
    }
    result = execute_photon_capsule(capsule, context={"capsule_id": "body_test"})
    assert result["status"] == "success"
    assert any(g["operator"] == "+" for g in result["glyphs"])
    # ✅ Check correct warning was logged
    assert any("Legacy capsule with 'body'" in rec.message for rec in caplog.records)

def test_symatics_execution_dict(tmp_path):
    result = execute_photon_capsule(SYM_CAPSULE, context={"capsule_id": "sym_test"})
    assert result["status"] == "success"
    assert result["engine"] == "symatics"
    assert any(g["operator"] in {"⊕", "μ"} for g in result["glyphs"])
    assert isinstance(result["execution"], list)


def test_codex_execution_dict(tmp_path):
    result = execute_photon_capsule(CODEX_CAPSULE, context={"capsule_id": "codex_test"})
    assert result["status"] == "success"
    assert result["engine"] == "codex"
    assert any(g["operator"] == "+" for g in result["glyphs"])
    assert "execution" in result


def test_symatics_execution_file(tmp_path):
    path = tmp_path / "sym_capsule.phn"
    path.write_text(json.dumps(SYM_CAPSULE, indent=2))

    result = execute_photon_capsule(str(path), context={"capsule_id": "sym_file"})
    assert result["status"] == "success"
    assert result["engine"] == "symatics"


def test_legacy_capsule_auto_upgrade(caplog):
    caplog.set_level("WARNING")
    result = execute_photon_capsule(LEGACY_STEPS_CAPSULE, context={"capsule_id": "legacy_test"})
    assert result["status"] == "success"
    assert result["engine"] == "symatics"
    assert any(g["operator"] in {"⊕", "μ"} for g in result["glyphs"])
    # ✅ Ensure upgrade warning was logged
    assert any("auto-converted" in msg or "migrated" in msg or "Legacy capsule" in msg
               for msg in caplog.messages)