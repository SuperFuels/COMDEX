from __future__ import annotations

import ntpath
import posixpath
from dataclasses import asdict, dataclass
from typing import Any, Mapping


NODE_LAYOUT_SCHEMA = "tessaris.node-installation-layout.v1"


class NodeInstallationLayoutError(ValueError):
    pass


@dataclass(frozen=True)
class NodeInstallationLayout:
    schema_version: str
    system: str
    application_root: str
    update_root: str
    node_state_root: str
    vault_root: str
    credential_store: str
    application_identity: str
    updater_identity: str
    guardian_identity: str
    updater_can_open_vault: bool
    guardian_can_write_application: bool

    def payload(self) -> dict[str, Any]:
        return asdict(self)


def _join(system: str, *parts: str) -> str:
    module = ntpath if system == "windows" else posixpath
    return module.normpath(module.join(*parts))


def _normal(system: str, value: str) -> str:
    module = ntpath if system == "windows" else posixpath
    cleaned = module.normpath(str(value or "").strip())
    return module.normcase(cleaned) if system == "windows" else cleaned


def _contains(system: str, parent: str, child: str) -> bool:
    module = ntpath if system == "windows" else posixpath
    parent_value, child_value = _normal(system, parent), _normal(system, child)
    try:
        return module.commonpath([parent_value, child_value]) == parent_value
    except ValueError:
        return False


def validate_node_installation_layout(layout: NodeInstallationLayout) -> NodeInstallationLayout:
    if layout.schema_version != NODE_LAYOUT_SCHEMA or layout.system not in {"darwin", "windows", "linux"}:
        raise NodeInstallationLayoutError("node_layout_schema_or_system_invalid")
    roots = {
        "application": layout.application_root,
        "update": layout.update_root,
        "node_state": layout.node_state_root,
        "vault": layout.vault_root,
    }
    if any(not str(value).strip() for value in roots.values()):
        raise NodeInstallationLayoutError("node_layout_root_missing")
    names = tuple(roots)
    for index, left in enumerate(names):
        for right in names[index + 1:]:
            if _contains(layout.system, roots[left], roots[right]) or _contains(
                layout.system, roots[right], roots[left]
            ):
                raise NodeInstallationLayoutError(f"node_layout_overlap:{left}:{right}")
    identities = {
        layout.application_identity, layout.updater_identity, layout.guardian_identity
    }
    if len(identities) != 3 or any(not value for value in identities):
        raise NodeInstallationLayoutError("node_layout_identity_separation_required")
    if layout.updater_can_open_vault or layout.guardian_can_write_application:
        raise NodeInstallationLayoutError("node_layout_privilege_boundary_invalid")
    if not layout.credential_store:
        raise NodeInstallationLayoutError("node_layout_credential_store_missing")
    return layout


def default_node_installation_layout(
    *, system: str, environment: Mapping[str, str]
) -> NodeInstallationLayout:
    system_name = str(system or "").strip().lower()
    env = {str(key): str(value) for key, value in environment.items()}
    if system_name == "darwin":
        home = env.get("HOME", "").strip()
        if not home:
            raise NodeInstallationLayoutError("node_layout_home_missing")
        layout = NodeInstallationLayout(
            NODE_LAYOUT_SCHEMA, system_name,
            env.get("TESSARIS_APPLICATION_ROOT") or "/Applications/Tessaris.app",
            env.get("TESSARIS_UPDATE_ROOT") or _join(system_name, home, "Library/Application Support/Tessaris Updater"),
            env.get("TESSARIS_NODE_STATE_ROOT") or _join(system_name, home, "Library/Application Support/Tessaris Node"),
            env.get("TESSARIS_BUSINESS_VAULT_ROOT") or _join(system_name, home, "Library/Application Support/Tessaris Business Vaults"),
            "macos-keychain",
            "tessaris.desktop.user", "tessaris.updater.user", "tessaris.guardian.user",
            False, False,
        )
    elif system_name == "windows":
        required = {key: env.get(key, "").strip() for key in ("ProgramFiles", "ProgramData", "LOCALAPPDATA")}
        if any(not value for value in required.values()):
            raise NodeInstallationLayoutError("node_layout_windows_environment_missing")
        layout = NodeInstallationLayout(
            NODE_LAYOUT_SCHEMA, system_name,
            env.get("TESSARIS_APPLICATION_ROOT") or _join(system_name, required["ProgramFiles"], "Tessaris"),
            env.get("TESSARIS_UPDATE_ROOT") or _join(system_name, required["ProgramData"], "Tessaris Updater"),
            env.get("TESSARIS_NODE_STATE_ROOT") or _join(system_name, required["ProgramData"], "Tessaris Node"),
            env.get("TESSARIS_BUSINESS_VAULT_ROOT") or _join(system_name, required["LOCALAPPDATA"], "Tessaris", "Business Vaults"),
            "windows-credential-manager-dpapi",
            "interactive-user", "tessaris-updater-service", "tessaris-guardian-service",
            False, False,
        )
    elif system_name == "linux":
        home = env.get("HOME", "").strip()
        if not home:
            raise NodeInstallationLayoutError("node_layout_home_missing")
        xdg_data = env.get("XDG_DATA_HOME", "").strip() or _join(system_name, home, ".local/share")
        layout = NodeInstallationLayout(
            NODE_LAYOUT_SCHEMA, system_name,
            env.get("TESSARIS_APPLICATION_ROOT") or "/opt/tessaris",
            env.get("TESSARIS_UPDATE_ROOT") or "/var/lib/tessaris-updater",
            env.get("TESSARIS_NODE_STATE_ROOT") or "/var/lib/tessaris-node",
            env.get("TESSARIS_BUSINESS_VAULT_ROOT") or _join(system_name, xdg_data, "tessaris/business-vaults"),
            "linux-secret-service-or-systemd-credentials",
            "tessaris-desktop-user", "tessaris-updater", "tessaris-guardian",
            False, False,
        )
    else:
        raise NodeInstallationLayoutError("node_layout_system_unsupported")
    return validate_node_installation_layout(layout)
