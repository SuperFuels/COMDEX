from __future__ import annotations

import json

import pytest

from backend.modules.aion_business.runtime.business_vault import (
    VAULT_MANIFEST_SCHEMA,
    VaultBoundaryError,
    default_business_vault_root,
    provision_business_vault,
    safe_business_slug,
    validate_vault_separation,
)


def test_default_roots_are_cross_platform_and_overrideable(tmp_path):
    home = tmp_path / "home"
    assert default_business_vault_root(system="Darwin", environment={}, home=home) == (
        home / "Library" / "Application Support" / "Tessaris Business Vaults"
    )
    assert default_business_vault_root(
        system="Windows", environment={"LOCALAPPDATA": str(tmp_path / "local")}, home=home
    ) == tmp_path / "local" / "Tessaris" / "Business Vaults"
    assert default_business_vault_root(
        system="Linux", environment={"XDG_DATA_HOME": str(tmp_path / "xdg")}, home=home
    ) == tmp_path / "xdg" / "tessaris" / "business-vaults"
    assert default_business_vault_root(
        system="Linux",
        environment={"TESSARIS_BUSINESS_VAULT_ROOT": str(tmp_path / "dedicated")},
        home=home,
    ) == tmp_path / "dedicated"


def test_overlap_with_application_or_update_root_fails_closed(tmp_path):
    app = tmp_path / "Tessaris"
    updates = tmp_path / "updates"
    with pytest.raises(VaultBoundaryError, match="application_boundary_overlap"):
        validate_vault_separation(app / "business", application_root=app, update_root=updates)
    with pytest.raises(VaultBoundaryError, match="update_boundary_overlap"):
        validate_vault_separation(updates / "business", application_root=app, update_root=updates)
    assert validate_vault_separation(
        tmp_path / "customer-data", application_root=app, update_root=updates
    ) == tmp_path / "customer-data"


def test_provisioned_vault_has_stable_layout_and_no_key_material(tmp_path):
    vault = tmp_path / "customer-data" / safe_business_slug("Home Fixed Ltd", "biz_123")
    layout = provision_business_vault(
        vault,
        business_name="Home Fixed Ltd",
        business_stable_id="biz_123",
        application_root=tmp_path / "app",
        update_root=tmp_path / "updates",
    )
    manifest = json.loads(layout.manifest.read_text(encoding="utf-8"))
    assert manifest["schema_version"] == VAULT_MANIFEST_SCHEMA
    assert manifest["encryption"]["key_material_in_manifest"] is False
    assert all(
        path.is_dir()
        for path in (
            layout.records,
            layout.files,
            layout.indexes,
            layout.receipts,
            layout.snapshots,
            layout.exports,
        )
    )


def test_existing_vault_cannot_be_rebound_to_another_business(tmp_path):
    vault = tmp_path / "customer-data" / "shared.business-vault"
    kwargs = {"application_root": tmp_path / "app", "update_root": tmp_path / "updates"}
    provision_business_vault(
        vault, business_name="First", business_stable_id="first", **kwargs
    )
    with pytest.raises(VaultBoundaryError, match="identity_mismatch"):
        provision_business_vault(
            vault, business_name="Second", business_stable_id="second", **kwargs
        )
