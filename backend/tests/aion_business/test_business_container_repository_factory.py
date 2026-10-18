from __future__ import annotations

import base64

import pytest

from backend.modules.aion_business.runtime.business_container_repository import (
    BusinessContainerRepository,
)
from backend.modules.aion_business.runtime.business_container_repository_factory import (
    BusinessContainerRepositoryConfigurationError,
    configured_business_container_repository,
)
from backend.modules.aion_business.runtime.guardian_business_container_repository import (
    GuardianBusinessContainerRepository,
)
from backend.modules.aion_business.runtime.business_map_governance_service import (
    BusinessMapGovernanceService,
)


def guardian_environment(tmp_path):
    return {
        "TESSARIS_BUSINESS_CONTAINER_BACKEND": "guardian",
        "TESSARIS_BUSINESS_VAULT_PATH": str(tmp_path / "customer-data" / "Acme.business-vault"),
        "TESSARIS_BUSINESS_NAME": "Acme Limited",
        "TESSARIS_BUSINESS_STABLE_ID": "acme-limited",
        "TESSARIS_BUSINESS_VAULT_KEY_B64": base64.urlsafe_b64encode(b"k" * 32).decode().rstrip("="),
        "TESSARIS_APPLICATION_ROOT": str(tmp_path / "application"),
        "TESSARIS_UPDATE_ROOT": str(tmp_path / "updates"),
    }


def test_default_backend_remains_legacy_during_controlled_migration(tmp_path):
    repository = configured_business_container_repository(
        environment={"TESSARIS_LEGACY_BUSINESS_CONTAINER_DIR": str(tmp_path / "legacy")}
    )
    assert isinstance(repository, BusinessContainerRepository)
    repository.save_dict("workspace-1", "business_map", {"revision": 1})
    assert repository.load_dict("workspace-1", "business_map") == {"revision": 1}


def test_explicit_guardian_backend_writes_encrypted_external_record(tmp_path):
    repository = configured_business_container_repository(
        environment=guardian_environment(tmp_path)
    )
    assert isinstance(repository, GuardianBusinessContainerRepository)
    repository.save_dict(
        "workspace-1", "business_map", {"private_strategy": "Acquire Example Limited"},
        idempotency_key="factory-map-create",
    )
    assert repository.load_dict("workspace-1", "business_map")["private_strategy"] == "Acquire Example Limited"
    assert b"Acquire Example Limited" not in repository.guardian.database.read_bytes()


def test_guardian_mode_never_falls_back_when_configuration_is_missing_or_overlaps(tmp_path):
    with pytest.raises(BusinessContainerRepositoryConfigurationError, match="configuration_missing"):
        configured_business_container_repository(
            environment={"TESSARIS_BUSINESS_CONTAINER_BACKEND": "guardian"}
        )
    environment = guardian_environment(tmp_path)
    environment["TESSARIS_APPLICATION_ROOT"] = environment["TESSARIS_BUSINESS_VAULT_PATH"]
    with pytest.raises(ValueError, match="boundary_overlap"):
        configured_business_container_repository(environment=environment)


def test_unknown_backend_is_rejected(tmp_path):
    with pytest.raises(BusinessContainerRepositoryConfigurationError, match="backend_invalid"):
        configured_business_container_repository(
            environment={"TESSARIS_BUSINESS_CONTAINER_BACKEND": "automatic"}
        )


def test_default_constructor_cannot_bypass_enabled_guardian_and_map_receipts_are_encrypted(
    tmp_path, monkeypatch
):
    environment = guardian_environment(tmp_path)
    for key, value in environment.items():
        monkeypatch.setenv(key, value)
    repository = BusinessContainerRepository()
    assert isinstance(repository, GuardianBusinessContainerRepository)
    repository.save_dict(
        "workspace-1",
        "business_map",
        {
            "id": "workspace-1.business_map",
            "workspace_id": "workspace-1",
            "kind": "business_map",
            "meta": {"workspace_id": "workspace-1", "container_key": "business_map"},
            "facts": [], "relationships": [], "assumptions": [], "unknowns": [],
            "conflicts": [], "unanswered_fields": [], "department_discovery_gaps": [],
            "source_refs": [], "revision": 0,
        },
        idempotency_key="map-seed",
    )
    service = BusinessMapGovernanceService(repository)
    result = service.propose_fact(
        "workspace-1",
        field="private_strategy",
        value="Acquire Example Limited",
        source_ref="founder:interview",
        confidence=1.0,
        proposed_by="founder",
    )
    assert result["revision"] == 1
    receipts = repository.guardian.list_records(collection="business_map_governance")
    assert len(receipts) == 1
    assert b"Acquire Example Limited" not in repository.guardian.database.read_bytes()
