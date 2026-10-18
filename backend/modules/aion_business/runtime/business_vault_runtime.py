from __future__ import annotations

import base64
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

from backend.modules.aion_business.runtime.business_vault import (
    BusinessVaultLayout,
    provision_business_vault,
)
from backend.modules.aion_business.runtime.vault_guardian import VaultGuardian
from backend.modules.aion_business.runtime.vault_object_store import VaultObjectStore


class BusinessVaultRuntimeConfigurationError(ValueError):
    pass


@dataclass(frozen=True)
class BusinessVaultRuntime:
    layout: BusinessVaultLayout
    guardian: VaultGuardian
    objects: VaultObjectStore


def _decode_key(value: str) -> bytes:
    try:
        key = base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))
    except (ValueError, TypeError) as exc:
        raise BusinessVaultRuntimeConfigurationError(
            "guardian_business_vault_key_invalid"
        ) from exc
    if len(key) != 32:
        raise BusinessVaultRuntimeConfigurationError(
            "guardian_business_vault_key_invalid"
        )
    return key


def guardian_mode_requested(*, environment: Mapping[str, str] | None = None) -> bool:
    env = os.environ if environment is None else environment
    return str(env.get("TESSARIS_BUSINESS_CONTAINER_BACKEND") or "legacy").strip().lower() == "guardian"


def configured_business_vault_runtime(
    *, environment: Mapping[str, str] | None = None
) -> BusinessVaultRuntime:
    """Build the one Guardian/object runtime used by every business-data domain.

    This deliberately shares the same key and external vault boundary with the
    semantic business containers.  It never falls back to legacy storage when
    Guardian mode was requested but is incomplete.
    """

    env = dict(os.environ if environment is None else environment)
    if not guardian_mode_requested(environment=env):
        raise BusinessVaultRuntimeConfigurationError(
            "guardian_business_vault_not_enabled"
        )
    required = {
        name: str(env.get(name) or "").strip()
        for name in (
            "TESSARIS_BUSINESS_VAULT_PATH",
            "TESSARIS_BUSINESS_NAME",
            "TESSARIS_BUSINESS_STABLE_ID",
            "TESSARIS_BUSINESS_VAULT_KEY_B64",
            "TESSARIS_APPLICATION_ROOT",
            "TESSARIS_UPDATE_ROOT",
        )
    }
    missing = sorted(name for name, value in required.items() if not value)
    if missing:
        raise BusinessVaultRuntimeConfigurationError(
            "guardian_business_vault_configuration_missing:" + ",".join(missing)
        )
    layout = provision_business_vault(
        required["TESSARIS_BUSINESS_VAULT_PATH"],
        business_name=required["TESSARIS_BUSINESS_NAME"],
        business_stable_id=required["TESSARIS_BUSINESS_STABLE_ID"],
        application_root=Path(required["TESSARIS_APPLICATION_ROOT"]),
        update_root=Path(required["TESSARIS_UPDATE_ROOT"]),
    )
    key = _decode_key(required["TESSARIS_BUSINESS_VAULT_KEY_B64"])
    guardian = VaultGuardian(
        layout,
        business_stable_id=required["TESSARIS_BUSINESS_STABLE_ID"],
        encryption_key=key,
    )
    return BusinessVaultRuntime(
        layout=layout,
        guardian=guardian,
        objects=VaultObjectStore(
            layout,
            guardian=guardian,
            business_stable_id=required["TESSARIS_BUSINESS_STABLE_ID"],
            encryption_key=key,
        ),
    )
