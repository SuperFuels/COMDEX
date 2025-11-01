# backend/modules/dimensions/universal_container_system/ucs_soullaw.py
import os
import logging
from typing import Optional, Dict, Any

log = logging.getLogger("soullaw")

class SoulLawEnforcer:
    def validate_access(
        self,
        container: Optional[Dict[str, Any]],
        avatar_state: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Validate access to a container, optionally using avatar_state.
        Backward-compatible with older callers that only pass `container`.
        """
        name = (container or {}).get("name") or (container or {}).get("id") or "<unnamed>"

        # Dev/CI toggle to unblock experiments without changing container data
        mode = os.getenv("SOULLAW_MODE", "enforce").lower()
        if mode in ("permissive", "off"):
            log.info("🔑 SoulLaw (permissive) -> allowed: %s", name)
            return True

        if not isinstance(container, dict):
            raise PermissionError("🔒 SoulLaw: invalid container payload")

        # 1) Legacy restriction gate (kept exactly as before)
        if container.get("restricted", False):
            if container.get("access_key") != "GUARDIAN":
                raise PermissionError(f"🔒 SoulLaw: Access denied for {name} (access_key mismatch)")

        # 2) Optional structured gate (traits/roles), if present
        gate = container.get("gate") or container.get("soullaw") or {}
        if gate:
            # Roles check
            required_roles = set(gate.get("roles", []))
            if required_roles:
                roles = set((avatar_state or {}).get("roles", []))
                if not required_roles.issubset(roles):
                    raise PermissionError(
                        f"🔒 SoulLaw: Avatar missing required roles {sorted(required_roles)} for {name}"
                    )

            # Traits check
            required_traits: Dict[str, float] = gate.get("required_traits", {})
            if required_traits:
                traits = (avatar_state or {}).get("traits", {})
                missing = {
                    t: (float(traits.get(t, 0.0)), float(need))
                    for t, need in required_traits.items()
                    if float(traits.get(t, 0.0)) < float(need)
                }
                if missing:
                    detail = ", ".join([f"{k}={cur} < {need}" for k, (cur, need) in missing.items()])
                    raise PermissionError(f"🔒 SoulLaw: Trait threshold not met for {name} -> {detail}")

            # Optional boolean flags
            if gate.get("verified", False) and not (avatar_state or {}).get("verified", False):
                raise PermissionError(f"🔒 SoulLaw: Avatar not verified for {name}")

        log.info("🔑 SoulLaw validated for %s", name)
        return True