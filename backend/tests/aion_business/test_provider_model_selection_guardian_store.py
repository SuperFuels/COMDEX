from __future__ import annotations

import base64

from backend.modules.aion_inference.lead_model_selection_store import (
    load_lead_model_selection,
    save_lead_model_selection,
)
from backend.modules.aion_inference.local_model_selection_store import (
    load_local_model_selection,
    save_local_model_selection,
)


def _enable_guardian(monkeypatch, tmp_path) -> None:
    monkeypatch.chdir(tmp_path)
    values = {
        "TESSARIS_BUSINESS_CONTAINER_BACKEND": "guardian",
        "TESSARIS_BUSINESS_VAULT_PATH": str(
            tmp_path / "customer-data" / "Acme-acme.business-vault"
        ),
        "TESSARIS_BUSINESS_NAME": "Acme",
        "TESSARIS_BUSINESS_STABLE_ID": "acme",
        "TESSARIS_BUSINESS_VAULT_KEY_B64": base64.urlsafe_b64encode(
            b"m" * 32
        ).decode("ascii"),
        "TESSARIS_APPLICATION_ROOT": str(tmp_path / "application"),
        "TESSARIS_UPDATE_ROOT": str(tmp_path / "updates"),
    }
    for name, value in values.items():
        monkeypatch.setenv(name, value)


def test_provider_model_selections_round_trip_inside_encrypted_guardian_store(
    monkeypatch, tmp_path
):
    _enable_guardian(monkeypatch, tmp_path)

    lead = save_lead_model_selection(
        "acme",
        provider_id="private-provider",
        model_id="confidential-boardroom-model",
    )
    local_uri = save_local_model_selection(
        "acme",
        {"provider": "ollama", "model": "private-local-model"},
    )

    assert lead["model_id"] == "confidential-boardroom-model"
    assert load_lead_model_selection("acme")["provider_id"] == "private-provider"
    assert load_local_model_selection("acme")["model"] == "private-local-model"
    assert local_uri == "guardian://provider.model_selections/acme/local-model"

    vault_bytes = b"".join(
        path.read_bytes()
        for path in (tmp_path / "customer-data").rglob("*")
        if path.is_file()
    )
    assert b"confidential-boardroom-model" not in vault_bytes
    assert b"private-local-model" not in vault_bytes
    assert not (tmp_path / ".runtime" / "AION_BUSINESS").exists()


def test_legacy_model_selection_reads_do_not_create_runtime_directories(
    monkeypatch, tmp_path
):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("TESSARIS_BUSINESS_CONTAINER_BACKEND", "legacy")

    assert load_lead_model_selection("missing-business") == {}
    assert load_local_model_selection("missing-business") == {}
    assert not (tmp_path / ".runtime" / "AION_BUSINESS").exists()
