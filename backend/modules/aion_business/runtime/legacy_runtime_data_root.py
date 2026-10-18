from __future__ import annotations

import os
from pathlib import Path
import sys
from typing import Mapping

from backend.modules.aion_business.runtime.node_installation_layout import (
    default_node_installation_layout,
)


class LegacyRuntimeDataRootError(ValueError):
    """Raised when the transitional runtime root crosses a protected boundary."""


LEGACY_RUNTIME_DIRECTORIES = (
    "personality",
    "memory",
    "goals",
    "aion_field",
    "knowledge",
    "akg",
    "telemetry",
)


def _supported_system(value: str) -> str:
    name = str(value or "").strip().lower()
    if name in {"win32", "cygwin", "msys", "windows"}:
        return "windows"
    if name.startswith("linux"):
        return "linux"
    return name


def _overlaps(left: Path, right: Path) -> bool:
    left_value = left.resolve(strict=False)
    right_value = right.resolve(strict=False)
    try:
        left_value.relative_to(right_value)
        return True
    except ValueError:
        pass
    try:
        right_value.relative_to(left_value)
        return True
    except ValueError:
        return False


def resolve_legacy_runtime_data_root(
    *,
    application_root: str | Path,
    environment: Mapping[str, str] | None = None,
    system: str | None = None,
) -> Path:
    """Resolve transitional DATA_ROOT outside app, updater and customer Vault.

    This root is not a substitute for Guardian. It keeps still-unmigrated legacy
    runtime writers away from replaceable application files while their records
    are classified and moved to their final protected domains.
    """

    env = {str(key): str(value) for key, value in (environment or os.environ).items()}
    application = Path(application_root).expanduser().resolve(strict=False)
    configured = str(env.get("TESSARIS_DATA_ROOT") or env.get("DATA_ROOT") or "").strip()
    if configured:
        root = Path(configured).expanduser().resolve(strict=False)
    else:
        layout_env = dict(env)
        layout_env["TESSARIS_APPLICATION_ROOT"] = str(application)
        layout = default_node_installation_layout(
            system=_supported_system(str(system or sys.platform)),
            environment=layout_env,
        )
        root = Path(layout.node_state_root).expanduser().resolve(strict=False) / "legacy-runtime-data"

    protected = {
        "application": application,
        "update": Path(env["TESSARIS_UPDATE_ROOT"]).expanduser().resolve(strict=False)
        if str(env.get("TESSARIS_UPDATE_ROOT") or "").strip()
        else None,
        "vault": Path(env["TESSARIS_BUSINESS_VAULT_ROOT"]).expanduser().resolve(strict=False)
        if str(env.get("TESSARIS_BUSINESS_VAULT_ROOT") or "").strip()
        else None,
    }
    for label, protected_root in protected.items():
        if protected_root is not None and _overlaps(root, protected_root):
            raise LegacyRuntimeDataRootError(
                f"legacy_runtime_data_root_overlaps_{label}"
            )
    return root


def ensure_legacy_runtime_data_root(
    *,
    application_root: str | Path,
    environment: Mapping[str, str] | None = None,
    system: str | None = None,
) -> Path:
    root = resolve_legacy_runtime_data_root(
        application_root=application_root,
        environment=environment,
        system=system,
    )
    root.mkdir(parents=True, exist_ok=True, mode=0o700)
    for name in LEGACY_RUNTIME_DIRECTORIES:
        (root / name).mkdir(parents=True, exist_ok=True, mode=0o700)
    return root
