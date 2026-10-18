from __future__ import annotations

from dataclasses import replace

import pytest

from backend.modules.aion_business.runtime.node_installation_layout import (
    NodeInstallationLayoutError,
    default_node_installation_layout,
    validate_node_installation_layout,
)


@pytest.mark.parametrize(
    ("system", "environment", "credential_store"),
    [
        ("darwin", {"HOME": "/Users/founder"}, "macos-keychain"),
        (
            "windows",
            {
                "ProgramFiles": r"C:\Program Files", "ProgramData": r"C:\ProgramData",
                "LOCALAPPDATA": r"C:\Users\Founder\AppData\Local",
            },
            "windows-credential-manager-dpapi",
        ),
        ("linux", {"HOME": "/home/founder"}, "linux-secret-service-or-systemd-credentials"),
    ],
)
def test_cross_platform_defaults_keep_app_updater_node_and_vault_separate(
    system, environment, credential_store
):
    layout = default_node_installation_layout(system=system, environment=environment)
    assert layout.credential_store == credential_store
    assert len({layout.application_identity, layout.updater_identity, layout.guardian_identity}) == 3
    assert layout.updater_can_open_vault is False
    assert layout.guardian_can_write_application is False


def test_customer_override_is_accepted_only_when_separate():
    layout = default_node_installation_layout(
        system="linux",
        environment={"HOME": "/home/founder", "TESSARIS_BUSINESS_VAULT_ROOT": "/mnt/private/acme-vault"},
    )
    assert layout.vault_root == "/mnt/private/acme-vault"


def test_overlap_and_collapsed_service_identity_fail_closed():
    layout = default_node_installation_layout(system="darwin", environment={"HOME": "/Users/founder"})
    with pytest.raises(NodeInstallationLayoutError, match="overlap"):
        validate_node_installation_layout(replace(layout, vault_root=layout.update_root + "/customer"))
    with pytest.raises(NodeInstallationLayoutError, match="identity_separation"):
        validate_node_installation_layout(
            replace(layout, guardian_identity=layout.updater_identity)
        )


def test_privilege_escalation_flags_are_never_permitted():
    layout = default_node_installation_layout(system="linux", environment={"HOME": "/home/founder"})
    with pytest.raises(NodeInstallationLayoutError, match="privilege_boundary"):
        validate_node_installation_layout(replace(layout, updater_can_open_vault=True))
