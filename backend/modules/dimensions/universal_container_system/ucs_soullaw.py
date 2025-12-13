# backend/modules/dimensions/universal_container_system/ucs_soullaw.py
import os
import logging
from typing import Optional, Dict, Any

log = logging.getLogger("soullaw")


class SoulLawEnforcer:
    def validate_access(
        self,
        container: Optional[Dict[str, Any]],
        avatar_state: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Validate access to a container, optionally using avatar_state.
        Backward-compatible with older callers that only pass `container`.

        Accepts:
          - dict container payload
          - UCSBaseContainer / objects with .to_dict() (best-effort)
        """

        # Dev/CI toggle to unblock experiments without changing container data
        mode = os.getenv("SOULLAW_MODE", "enforce").lower().strip()
        if mode in ("permissive", "off", "disabled", "0", "false"):
            name = (container or {}).get("name") if isinstance(container, dict) else getattr(container, "name", None)
            name = name or (container or {}).get("id") if isinstance(container, dict) else getattr(container, "id", None)
            name = name or "<unnamed>"
            log.info("🔑 SoulLaw (permissive) -> allowed: %s", name)
            return True

        # Normalize container payload (best-effort)
        if container is None:
            raise PermissionError("🔒 SoulLaw: invalid container payload (None)")

        if not isinstance(container, dict):
            # Try normalize via UCS utils (kept lazy to avoid circular imports)
            try:
                from backend.modules.dimensions.universal_container_system.ucs_utils import normalize_container_dict
                container = normalize_container_dict(container)
            except Exception:
                raise PermissionError("🔒 SoulLaw: invalid container payload (non-dict)")

        name = container.get("name") or container.get("id") or "<unnamed>"

        # 1) Legacy restriction gate (kept as-is)
        if container.get("restricted", False):
            if container.get("access_key") != "GUARDIAN":
                raise PermissionError(f"🔒 SoulLaw: Access denied for {name} (access_key mismatch)")

        # 2) Optional structured gate (traits/roles), if present
        gate = container.get("gate") or container.get("soullaw") or {}
        if not isinstance(gate, dict):
            gate = {}

        # Roles check
        required_roles = gate.get("roles", [])
        if required_roles and not isinstance(required_roles, (list, tuple, set)):
            required_roles = [required_roles]
        required_roles = set([str(r) for r in required_roles if r is not None])

        if required_roles:
            roles = (avatar_state or {}).get("roles", [])
            if roles and not isinstance(roles, (list, tuple, set)):
                roles = [roles]
            roles = set([str(r) for r in roles if r is not None])
            if not required_roles.issubset(roles):
                raise PermissionError(
                    f"🔒 SoulLaw: Avatar missing required roles {sorted(required_roles)} for {name}"
                )

        # Traits check
        required_traits = gate.get("required_traits", {}) or {}
        if not isinstance(required_traits, dict):
            required_traits = {}

        if required_traits:
            traits = (avatar_state or {}).get("traits", {}) or {}
            if not isinstance(traits, dict):
                traits = {}

            missing: Dict[str, tuple[float, float]] = {}
            for t, need in required_traits.items():
                try:
                    need_f = float(need)
                except Exception:
                    continue
                try:
                    cur_f = float(traits.get(t, 0.0))
                except Exception:
                    cur_f = 0.0
                if cur_f < need_f:
                    missing[str(t)] = (cur_f, need_f)

            if missing:
                detail = ", ".join([f"{k}={cur} < {need}" for k, (cur, need) in missing.items()])
                raise PermissionError(f"🔒 SoulLaw: Trait threshold not met for {name} -> {detail}")

        # Optional boolean flags
        if bool(gate.get("verified", False)) and not bool((avatar_state or {}).get("verified", False)):
            raise PermissionError(f"🔒 SoulLaw: Avatar not verified for {name}")

        log.info("🔑 SoulLaw validated for %s", name)
        return True