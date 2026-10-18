from __future__ import annotations

import pytest
from fastapi import HTTPException

from backend.api import aion_proof_of_life


def test_proof_of_life_root_is_outside_application_by_default():
    application = aion_proof_of_life.Path(__file__).resolve().parents[3]
    with pytest.raises(ValueError):
        aion_proof_of_life.DATA_ROOT.relative_to(application)


def test_demo_mutations_are_disabled_without_explicit_enablement(monkeypatch):
    monkeypatch.setenv("TESSARIS_RUNTIME_MODE", "development")
    monkeypatch.delenv("TESSARIS_ENABLE_PROOF_OF_LIFE_MUTATIONS", raising=False)
    with pytest.raises(HTTPException) as exc_info:
        aion_proof_of_life._require_demo_mutation_authority()
    assert exc_info.value.status_code == 404


def test_demo_mutations_remain_disabled_in_production(monkeypatch):
    monkeypatch.setenv("TESSARIS_RUNTIME_MODE", "production")
    monkeypatch.setenv("TESSARIS_ENABLE_PROOF_OF_LIFE_MUTATIONS", "1")
    with pytest.raises(HTTPException, match="mutations_disabled"):
        aion_proof_of_life._require_demo_mutation_authority()


def test_demo_mutations_require_both_nonproduction_and_enablement(monkeypatch):
    monkeypatch.setenv("TESSARIS_RUNTIME_MODE", "development")
    monkeypatch.setenv("TESSARIS_ENABLE_PROOF_OF_LIFE_MUTATIONS", "true")
    aion_proof_of_life._require_demo_mutation_authority()


def test_homeostasis_reads_only_from_selected_runtime_root(tmp_path, monkeypatch):
    monkeypatch.setattr(aion_proof_of_life, "DATA_ROOT", tmp_path)
    source = tmp_path / "analysis" / "aion_live_dashboard.json"
    source.parent.mkdir(parents=True)
    source.write_text(
        '{"generated_at":"now","events":2,"homeostasis":{"last":"stable"}}',
        encoding="utf-8",
    )
    response = aion_proof_of_life.api_homeostasis()
    assert response["generated_at"] == "now"
    assert response["last"] == "stable"
