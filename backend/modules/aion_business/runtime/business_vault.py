from __future__ import annotations

import json
import os
import platform
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping


VAULT_MANIFEST_SCHEMA = "tessaris.business-vault.v1"
VAULT_DIRECTORY_NAME = "Tessaris Business Vaults"


class VaultBoundaryError(ValueError):
    pass


def _resolved(path: str | Path) -> Path:
    return Path(path).expanduser().resolve(strict=False)


def _is_within(candidate: Path, parent: Path) -> bool:
    try:
        candidate.relative_to(parent)
        return True
    except ValueError:
        return False


def default_business_vault_root(
    *,
    system: str | None = None,
    environment: Mapping[str, str] | None = None,
    home: str | Path | None = None,
) -> Path:
    """Return an OS-appropriate user vault root, overridable for dedicated volumes."""

    env = dict(os.environ if environment is None else environment)
    override = env.get("TESSARIS_BUSINESS_VAULT_ROOT", "").strip()
    if override:
        return _resolved(override)

    os_name = (system or platform.system()).lower()
    user_home = _resolved(home or env.get("HOME") or Path.home())
    if os_name == "darwin":
        return user_home / "Library" / "Application Support" / VAULT_DIRECTORY_NAME
    if os_name == "windows":
        local_app_data = env.get("LOCALAPPDATA")
        if local_app_data:
            return _resolved(local_app_data) / "Tessaris" / "Business Vaults"
        return user_home / "AppData" / "Local" / "Tessaris" / "Business Vaults"

    xdg_data_home = env.get("XDG_DATA_HOME")
    if xdg_data_home:
        return _resolved(xdg_data_home) / "tessaris" / "business-vaults"
    return user_home / ".local" / "share" / "tessaris" / "business-vaults"


def validate_vault_separation(
    vault_root: str | Path,
    *,
    application_root: str | Path,
    update_root: str | Path,
) -> Path:
    """Fail closed when app, updater and customer vault boundaries overlap."""

    vault = _resolved(vault_root)
    application = _resolved(application_root)
    updates = _resolved(update_root)
    if vault == application or _is_within(vault, application) or _is_within(application, vault):
        raise VaultBoundaryError("vault_application_boundary_overlap")
    if vault == updates or _is_within(vault, updates) or _is_within(updates, vault):
        raise VaultBoundaryError("vault_update_boundary_overlap")
    return vault


def safe_business_slug(name: str, stable_id: str) -> str:
    cleaned = "-".join(part for part in "".join(c if c.isalnum() else " " for c in name).split() if part)
    cleaned = cleaned.strip("-")[:64] or "Business"
    stable = "".join(c for c in stable_id if c.isalnum() or c in "-_")[:48]
    if not stable:
        raise VaultBoundaryError("business_stable_id_invalid")
    return f"{cleaned}-{stable}.business-vault"


@dataclass(frozen=True)
class BusinessVaultLayout:
    root: Path
    manifest: Path
    records: Path
    files: Path
    indexes: Path
    receipts: Path
    snapshots: Path
    exports: Path

    @classmethod
    def for_root(cls, root: str | Path) -> "BusinessVaultLayout":
        vault = _resolved(root)
        return cls(
            root=vault,
            manifest=vault / "vault.manifest.json",
            records=vault / "records",
            files=vault / "files",
            indexes=vault / "derived" / "indexes",
            receipts=vault / "receipts",
            snapshots=vault / "snapshots",
            exports=vault / "exports",
        )


def _atomic_json_write(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temporary, 0o600)
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def provision_business_vault(
    vault_root: str | Path,
    *,
    business_name: str,
    business_stable_id: str,
    application_root: str | Path,
    update_root: str | Path,
) -> BusinessVaultLayout:
    """Provision the external format without placing secrets in its manifest."""

    root = validate_vault_separation(
        vault_root,
        application_root=application_root,
        update_root=update_root,
    )
    layout = BusinessVaultLayout.for_root(root)
    for directory in (
        layout.root,
        layout.records,
        layout.files,
        layout.indexes,
        layout.receipts,
        layout.snapshots,
        layout.exports,
    ):
        directory.mkdir(parents=True, exist_ok=True, mode=0o700)

    expected_manifest = {
        "schema_version": VAULT_MANIFEST_SCHEMA,
        "business_stable_id": business_stable_id,
        "business_name": business_name,
        "encryption": {
            "required": True,
            "key_storage": "platform_protected_or_external_secret_store",
            "key_material_in_manifest": False,
        },
        "authoritative_records": "records",
        "original_files": "files",
        "derived_rebuildable": "derived",
        "receipts": "receipts",
        "snapshots": "snapshots",
        "portable_exports": "exports",
    }
    if layout.manifest.exists():
        current = json.loads(layout.manifest.read_text(encoding="utf-8"))
        if current.get("schema_version") != VAULT_MANIFEST_SCHEMA:
            raise VaultBoundaryError("vault_manifest_schema_incompatible")
        if current.get("business_stable_id") != business_stable_id:
            raise VaultBoundaryError("vault_business_identity_mismatch")
    else:
        _atomic_json_write(layout.manifest, expected_manifest)
    return layout
