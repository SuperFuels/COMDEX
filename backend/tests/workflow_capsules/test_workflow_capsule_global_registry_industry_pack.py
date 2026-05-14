from __future__ import annotations

import pytest

from backend.modules.workflow_capsules.global_registry.industry_pack_schema import (
    GlobalWorkflowPattern,
    IndustryWorkflowPack,
    make_electrician_gmail_pack,
)
from backend.modules.workflow_capsules.global_registry.local_binding_schema import (
    LocalWorkflowBinding,
    make_electrician_gmail_local_binding,
)


def test_electrician_industry_pack_declares_global_pattern_without_credentials() -> None:
    pack = make_electrician_gmail_pack()
    data = pack.to_dict()

    assert data["pack_key"] == "industry.electrician.core.v1"
    assert data["industry"] == "electrician"
    assert data["required_connectors"] == ["gmail"]
    assert data["required_vault_handles"] == ["vault.gmail.credentials"]
    assert data["patterns"][0]["pattern_key"] == "global.workflow.electrician.gmail_receptionist.v1"
    assert data["patterns"][0]["workflow_canonical_key"] == "workflow:electrician.gmail_receptionist.v1"
    assert data["patterns"][0]["display_glyph"] == "EL-001"
    assert data["meta"]["checksum"]

    lowered = str(data).lower()
    assert "access_token" not in lowered
    assert "refresh_token" not in lowered
    assert "client_secret" not in lowered
    assert "password" not in lowered


def test_local_binding_maps_global_pattern_to_business_vault_handles() -> None:
    binding = make_electrician_gmail_local_binding(
        workspace_id="costa-conexion",
        business_id="electrician-demo",
    )
    data = binding.to_dict()

    assert data["binding_key"] == "binding.costa-conexion.electrician.gmail_receptionist.v1"
    assert data["workspace_id"] == "costa-conexion"
    assert data["business_id"] == "electrician-demo"
    assert data["pattern_key"] == "global.workflow.electrician.gmail_receptionist.v1"
    assert data["workflow_canonical_key"] == "workflow:electrician.gmail_receptionist.v1"
    assert data["connector_bindings"]["gmail"] == "connector.gmail.default"
    assert data["vault_bindings"]["gmail_credentials"] == "vault.gmail.credentials"
    assert data["enabled"] is False
    assert data["meta"]["checksum"]


def test_global_pack_rejects_raw_credentials() -> None:
    pattern = GlobalWorkflowPattern(
        pattern_key="global.workflow.bad.v1",
        display_name="Bad",
        industry="bad",
        meaning="Should fail",
        workflow_canonical_key="workflow:bad.v1",
        required_connectors=["gmail"],
        required_vault_handles=["vault.gmail.credentials"],
        template={
            "access_token": "must-not-store",
        },
    )

    pack = IndustryWorkflowPack(
        pack_key="industry.bad.v1",
        industry="bad",
        display_name="Bad Pack",
        meaning="Should fail",
        patterns=[pattern],
    )

    with pytest.raises(ValueError, match="industry_pack_must_not_contain_secret_fields"):
        pack.finalize()


def test_local_binding_rejects_raw_credentials() -> None:
    binding = LocalWorkflowBinding(
        binding_key="binding.bad.v1",
        workspace_id="workspace",
        business_id="business",
        pattern_key="global.workflow.bad.v1",
        workflow_canonical_key="workflow:bad.v1",
        connector_bindings={"gmail": "connector.gmail.default"},
        vault_bindings={"gmail_credentials": "vault.gmail.credentials"},
        business_context={
            "client_secret": "must-not-store",
        },
    )

    with pytest.raises(ValueError, match="local_workflow_binding_must_not_contain_secret_fields"):
        binding.finalize()
