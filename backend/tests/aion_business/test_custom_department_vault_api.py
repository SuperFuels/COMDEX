from __future__ import annotations

from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from backend.modules.aion_business.api import business_twin_data_api as api
from backend.modules.aion_business.runtime.business_vault import provision_business_vault
from backend.modules.aion_business.runtime.department_operational_store import (
    DepartmentOperationalStore,
)
from backend.modules.aion_business.runtime.guardian_business_container_repository import (
    GuardianBusinessContainerRepository,
)
from backend.modules.aion_business.runtime.vault_domain_store import VaultDomainStore
from backend.modules.aion_business.runtime.vault_guardian import VaultGuardian


def _foundation(monkeypatch, tmp_path):
    layout = provision_business_vault(
        tmp_path / "vault",
        business_name="Acme",
        business_stable_id="acme",
        application_root=tmp_path / "app",
        update_root=tmp_path / "updates",
    )
    guardian = VaultGuardian(
        layout, business_stable_id="acme", encryption_key=b"d" * 32
    )
    repository = GuardianBusinessContainerRepository(guardian)
    repository.save_dict(
        "acme",
        "business_identity",
        {
            "id": "acme.business_identity",
            "workspace_id": "acme",
            "kind": "business_identity",
            "meta": {"workspace_id": "acme", "container_key": "business_identity"},
            "trading_name": "Acme",
        },
    )
    repository.save_dict(
        "acme",
        "department_intelligence",
        {
            "id": "acme.department_intelligence",
            "workspace_id": "acme",
            "kind": "department_intelligence",
            "meta": {
                "workspace_id": "acme",
                "container_key": "department_intelligence",
            },
            "departments": {},
            "custom_departments": [],
            "revision": 1,
        },
    )
    operational = DepartmentOperationalStore(
        domain_store=VaultDomainStore(guardian, actor_id="test")
    )
    monkeypatch.setattr(api, "_repo", lambda: repository)
    monkeypatch.setattr(api, "guardian_mode_requested", lambda: True)
    monkeypatch.setattr(api, "DepartmentOperationalStore", lambda: operational)
    return guardian, repository, operational


def test_future_custom_department_survives_repository_restart_and_has_wildcard_audit(
    monkeypatch, tmp_path
):
    guardian, _repository, operational = _foundation(monkeypatch, tmp_path)

    created = api.create_custom_department(
        "acme",
        api.CustomDepartmentCreateRequest(
            name="Quantum Assurance",
            template="research",
            mandate="Review emerging quality evidence and report exceptions.",
            actor_id="person:founder",
            expected_revision=1,
            confirm_founder_authority=True,
        ),
    )
    assert created["department"]["id"] == "quantum_assurance"
    assert created["revision"] == 2

    restarted = GuardianBusinessContainerRepository(guardian)
    payload = restarted.load_department_intelligence("acme").model_dump(mode="json")
    assert payload["custom_departments"][0]["name"] == "Quantum Assurance"
    assert payload["departments"]["quantum_assurance"] == {
        "department": "quantum_assurance",
        "name": "Quantum Assurance",
        "mandate": "Review emerging quality evidence and report exceptions.",
        "template": "research",
        "pilot_title": "Research Director",
        "status": "configured",
        "map_schema_version": "aion.department_map.v1",
        "created_by": "person-founder",
        "created_at": created["department"]["created_at"],
    }
    audits = operational.list_audit(
        workspace_id="acme",
        department_id="quantum_assurance",
        feature_id="configuration",
    )
    assert audits[0]["payload"]["operation"] == "created"
    assert b"Quantum Assurance" not in guardian.database.read_bytes()


def test_custom_department_is_fail_closed_without_founder_confirmation(
    monkeypatch, tmp_path
):
    _foundation(monkeypatch, tmp_path)
    with pytest.raises(HTTPException) as denied:
        api.create_custom_department(
            "acme",
            api.CustomDepartmentCreateRequest(
                name="Future Department",
                template="innovation",
                mandate="Explore future work.",
            ),
        )
    assert denied.value.status_code == 403


def test_general_department_map_update_preserves_custom_department_register(
    monkeypatch, tmp_path
):
    _guardian, _repository, _operational = _foundation(monkeypatch, tmp_path)
    created = api.create_custom_department(
        "acme",
        api.CustomDepartmentCreateRequest(
            name="Continuity Lab",
            template="innovation",
            mandate="Exercise continuity plans.",
            actor_id="person:founder",
            expected_revision=1,
            confirm_founder_authority=True,
        ),
    )

    updated = api.put_department_intelligence(
        "acme",
        api.ContainerWriteRequest(
            payload={"departments": {"sales": {"map_status": "governed"}}},
            source="boardroom_map_governance",
            expected_revision=created["revision"],
        ),
    )

    assert updated["payload"]["custom_departments"][0]["id"] == "continuity_lab"
    assert updated["payload"]["departments"]["continuity_lab"]["map_schema_version"] == (
        "aion.department_map.v1"
    )


def test_business_identity_setting_is_written_to_guardian(monkeypatch, tmp_path):
    guardian, _repository, _operational = _foundation(monkeypatch, tmp_path)
    saved = api.put_business_identity_settings(
        "acme",
        api.BusinessIdentitySettingsRequest(
            trading_name="Acme Trading",
            actor_id="person:founder",
        ),
    )
    assert saved["payload"]["trading_name"] == "Acme Trading"
    assert api.get_business_identity("acme")["payload"]["trading_name"] == (
        "Acme Trading"
    )
    assert b"Acme Trading" not in guardian.database.read_bytes()
