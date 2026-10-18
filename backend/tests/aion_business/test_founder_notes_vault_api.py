from __future__ import annotations

from types import SimpleNamespace

from backend.modules.aion_business.api import business_twin_data_api as api
from backend.modules.aion_business.runtime.business_vault import provision_business_vault
from backend.modules.aion_business.runtime.vault_guardian import VaultGuardian


def test_founder_notes_round_trip_through_encrypted_vault(monkeypatch, tmp_path):
    layout = provision_business_vault(
        tmp_path / "vault",
        business_name="Acme",
        business_stable_id="acme",
        application_root=tmp_path / "app",
        update_root=tmp_path / "updates",
    )
    guardian = VaultGuardian(
        layout, business_stable_id="acme", encryption_key=b"n" * 32
    )
    monkeypatch.setattr(api, "guardian_mode_requested", lambda: True)
    monkeypatch.setattr(
        api,
        "configured_business_vault_runtime",
        lambda: SimpleNamespace(guardian=guardian),
    )

    notes = [{"id": "note-1", "title": "Private plan", "body": "Acquire supplier"}]
    saved = api.put_founder_notes(
        "acme", api.FounderNotesWriteRequest(notes=notes, actor_id="person:founder")
    )
    assert saved["version"] == 1
    assert api.get_founder_notes("acme")["notes"] == notes
    assert b"Acquire supplier" not in guardian.database.read_bytes()
