from __future__ import annotations

import importlib.util
from pathlib import Path
import sys

import pytest


SCRIPT = Path(__file__).resolve().parents[3] / "scripts" / "aion_sealed_repository_execution_battery.py"
sys.path.insert(0, str(SCRIPT.parent))
SPEC = importlib.util.spec_from_file_location("sealed_repository_battery", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_external_evidence_root_is_accepted(tmp_path):
    application = tmp_path / "application"
    update = tmp_path / "updates"
    vault = tmp_path / "vault"
    evidence = tmp_path / "engineering-evidence"
    assert MODULE.validate_execution_evidence_root(
        evidence,
        protected_roots=(application, update, vault),
    ) == evidence.resolve()


@pytest.mark.parametrize("location", ["inside", "parent"])
def test_application_update_vault_and_customer_overlap_fail_closed(tmp_path, location):
    for name in ("application", "updates", "vault", "customer-source"):
        protected = tmp_path / name
        candidate = protected / "evidence" if location == "inside" else tmp_path
        with pytest.raises(ValueError, match="overlaps_protected_root"):
            MODULE.validate_execution_evidence_root(
                candidate,
                protected_roots=(protected,),
            )


def test_cli_requires_explicit_external_output_root(monkeypatch):
    monkeypatch.setattr(sys, "argv", [str(SCRIPT)])
    with pytest.raises(SystemExit) as exc_info:
        MODULE.main()
    assert exc_info.value.code == 2


@pytest.mark.parametrize("value", ["../escape", "a/b", ".", "..", "", "with space"])
def test_run_id_cannot_escape_or_create_nested_paths(value):
    with pytest.raises(ValueError, match="run_id_invalid"):
        MODULE.safe_run_id(value)


def test_openai_key_is_never_loaded_from_repository_files(tmp_path, monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setattr(MODULE, "REPO", tmp_path)
    (tmp_path / ".env").write_text("OPENAI_API_KEY=sk-should-not-be-read-from-disk-123456789\n")
    assert MODULE._load_openai_key() == ""
