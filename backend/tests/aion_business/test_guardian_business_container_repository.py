from __future__ import annotations

import pytest

from backend.modules.aion_business.runtime.business_vault import provision_business_vault
from backend.modules.aion_business.runtime.guardian_business_container_repository import (
    GuardianBusinessContainerRepository,
)
from backend.modules.aion_business.runtime.vault_guardian import VaultGuardian, VaultGuardianError


def repository(tmp_path):
    layout = provision_business_vault(
        tmp_path / "customer-data" / "Home-Fixed.business-vault",
        business_name="Home Fixed", business_stable_id="home-fixed",
        application_root=tmp_path / "app", update_root=tmp_path / "updates",
    )
    guardian = VaultGuardian(layout, business_stable_id="home-fixed", encryption_key=b"c" * 32)
    return GuardianBusinessContainerRepository(guardian), guardian


def test_business_container_round_trip_is_encrypted(tmp_path):
    repo, guardian = repository(tmp_path)
    uri = repo.save_dict(
        "workspace-1", "business_map", {"private_strategy": "Acquire Example Limited"},
        actor_id="founder-1", idempotency_key="map-create", expected_version=None,
    )
    assert uri == "guardian://business_containers/workspace-1--business_map?version=1"
    assert repo.exists("workspace-1", "business_map") is True
    assert repo.load_dict("workspace-1", "business_map")["private_strategy"] == "Acquire Example Limited"
    assert b"Acquire Example Limited" not in guardian.database.read_bytes()


def test_container_update_preserves_history_and_replay(tmp_path):
    repo, guardian = repository(tmp_path)
    repo.save_dict(
        "workspace-1", "business_map", {"revision": 1},
        actor_id="founder-1", idempotency_key="map-create", expected_version=None,
    )
    uri = repo.save_dict(
        "workspace-1", "business_map", {"revision": 2},
        actor_id="founder-1", idempotency_key="map-update", expected_version=1,
    )
    replay = repo.save_dict(
        "workspace-1", "business_map", {"revision": 2},
        actor_id="founder-1", idempotency_key="map-update", expected_version=1,
    )
    assert uri == replay
    assert repo.load_dict("workspace-1", "business_map") == {"revision": 2}
    old = guardian.get_record(
        collection="business_containers", record_id="workspace-1--business_map", version=1
    )
    assert old["payload"]["container"] == {"revision": 1}


def test_stale_container_update_is_rejected(tmp_path):
    repo, _ = repository(tmp_path)
    repo.save_dict(
        "workspace-1", "business_map", {"revision": 1},
        actor_id="founder-1", idempotency_key="map-create", expected_version=None,
    )
    with pytest.raises(VaultGuardianError, match="version_conflict"):
        repo.save_dict(
            "workspace-1", "business_map", {"revision": 2},
            actor_id="founder-1", idempotency_key="map-stale", expected_version=0,
        )


def test_optional_load_does_not_create_data(tmp_path):
    repo, guardian = repository(tmp_path)
    assert repo.load_optional_dict("workspace-1", "business_map") is None
    assert guardian.verify_audit_chain()["receipt_count"] == 0


def test_container_operations_announce_registered_vault_domains(tmp_path, monkeypatch):
    repo, _ = repository(tmp_path)
    events: list[tuple[object, ...]] = []
    monkeypatch.setattr("sys.audit", lambda *items: events.append(items))

    repo.save_dict(
        "workspace-1",
        "business_structure",
        {"functions": [{"department_key": "operations"}]},
        actor_id="founder-1",
        idempotency_key="structure-create",
    )
    repo.load_dict("workspace-1", "business_structure")

    assert ("tessaris.vault_domain_access", "business.structure", "put") in events
    assert ("tessaris.vault_domain_access", "departments.map", "put") in events
    assert ("tessaris.vault_domain_access", "business.structure", "get") in events
    assert ("tessaris.vault_domain_access", "departments.map", "get") in events


def test_organization_authority_announces_security_and_operational_domains(tmp_path, monkeypatch):
    repo, _ = repository(tmp_path)
    events: list[tuple[object, ...]] = []
    monkeypatch.setattr("sys.audit", lambda *items: events.append(items))

    repo.save_dict(
        "workspace-1",
        "organization_authority",
        {"people": [], "roles": []},
        actor_id="founder-1",
        idempotency_key="authority-create",
    )
    repo.load_dict("workspace-1", "organization_authority")

    for operation in ("put", "get"):
        assert ("tessaris.vault_domain_access", "security.records", operation) in events
        assert (
            "tessaris.vault_domain_access",
            "departments.operational_records",
            operation,
        ) in events
