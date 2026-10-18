from __future__ import annotations

import os
from typing import Mapping

from backend.modules.aion_business.runtime.business_container_repository import (
    BusinessContainerRepository,
)
from backend.modules.aion_business.runtime.business_vault_runtime import (
    BusinessVaultRuntimeConfigurationError,
    configured_business_vault_runtime,
)
from backend.modules.aion_business.runtime.guardian_business_container_repository import (
    GuardianBusinessContainerRepository,
)
from backend.modules.aion_business.runtime.paths import AIONBusinessPaths


class BusinessContainerRepositoryConfigurationError(ValueError):
    pass


def configured_business_container_repository(
    *, environment: Mapping[str, str] | None = None
) -> BusinessContainerRepository | GuardianBusinessContainerRepository:
    """Select the migration backend without ever silently weakening Guardian mode."""
    env = dict(os.environ if environment is None else environment)
    backend = str(env.get("TESSARIS_BUSINESS_CONTAINER_BACKEND") or "legacy").strip().lower()
    if backend == "legacy":
        base_dir = str(env.get("TESSARIS_LEGACY_BUSINESS_CONTAINER_DIR") or "").strip()
        return BusinessContainerRepository(
            base_dir=base_dir or (AIONBusinessPaths.ROOT / "business_containers")
        )
    if backend != "guardian":
        raise BusinessContainerRepositoryConfigurationError(
            "business_container_backend_invalid"
        )

    try:
        runtime = configured_business_vault_runtime(environment=env)
    except BusinessVaultRuntimeConfigurationError as exc:
        raise BusinessContainerRepositoryConfigurationError(str(exc)) from exc
    return GuardianBusinessContainerRepository(
        runtime.guardian, default_actor_id="department-pilot-runtime"
    )
