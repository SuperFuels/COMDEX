# backend/modules/gma/gma_mesh_policy.py

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Dict, Any

from backend.modules.mesh.mesh_types import AccountId


@dataclass
class OfflineCreditPolicy:
    """
    In-memory model of the GMA offline credit policy.

    This is a dev / prototype stand-in for what will later be:
      - fully on-chain (governance-controlled), or
      - stored in GMA state with proper proposals / votes.

    Fields:
      - default_limit_pho:
          Baseline offline credit limit per account in PHO.
      - emergency_mode_enabled:
          When true, we fall back to emergency_limit_pho for accounts
          without explicit overrides. Intended for prolonged outages.
      - emergency_limit_pho:
          High-water offline limit in emergency mode.
      - limit_pct_of_balance:
          Placeholder for future "fraction of on-chain balance" rules.
          Not yet used in this Python-only prototype.
      - per_account_overrides:
          Optional per-account limits, e.g. merchants / infra.
    """

    default_limit_pho: Decimal = Decimal("25.0")
    emergency_mode_enabled: bool = False
    emergency_limit_pho: Decimal = Decimal("50.0")
    limit_pct_of_balance: Decimal = Decimal("0.00")  # not enforced yet

    per_account_overrides: Dict[AccountId, Decimal] = field(
        default_factory=dict
    )

    def get_limit_for_account(
        self,
        account: AccountId,
        last_known_balance_pho: Decimal | None = None,
    ) -> Decimal:
        """
        Compute the offline credit limit for a given PHO account.

        For now, the logic is intentionally simple:

          1. If there is a per-account override, use that.
          2. Else if emergency_mode_enabled, use emergency_limit_pho.
          3. Else use default_limit_pho.

        The last_known_balance_pho argument is reserved for future
        "fraction of balance" rules, e.g.:

            limit = min(
                self.default_limit_pho
                + self.limit_pct_of_balance * last_known_balance_pho,
                self.emergency_limit_pho,
            )

        but we don't use it yet in this prototype.
        """
        # 1) Per-account override
        if account in self.per_account_overrides:
            return self.per_account_overrides[account]

        # 2) Emergency mode
        if self.emergency_mode_enabled:
            return self.emergency_limit_pho

        # 3) Normal default
        return self.default_limit_pho

    def snapshot_dict(self) -> Dict[str, Any]:
        """
        Return a JSON-ready snapshot of the policy for debug/admin UIs.
        """
        return {
            "default_limit_pho": str(self.default_limit_pho),
            "emergency_mode_enabled": self.emergency_mode_enabled,
            "emergency_limit_pho": str(self.emergency_limit_pho),
            "limit_pct_of_balance": str(self.limit_pct_of_balance),
            "per_account_overrides": {
                acct: str(limit) for acct, limit in self.per_account_overrides.items()
            },
        }


# ───────────────────────────────────────────────
# Global in-memory policy instance (dev only)
# ───────────────────────────────────────────────

# For now, we just spin up a single process-local policy.
# Later this will be driven by GMA state / governance.
_OFFLINE_POLICY = OfflineCreditPolicy(
    default_limit_pho=Decimal("25.0"),
    emergency_mode_enabled=False,
    emergency_limit_pho=Decimal("50.0"),
    limit_pct_of_balance=Decimal("0.00"),
    per_account_overrides={
        # Example: give a slightly higher offline limit to demo merchant
        # "pho1merchant": Decimal("75.0"),
    },
)


def get_offline_limit_pho(account: AccountId) -> Decimal:
    """
    Public helper used by mesh_wallet_state + reconcile routes.

    Returns the offline credit limit (in PHO) for a given PHO account
    under the current OfflineCreditPolicy.
    """
    return _OFFLINE_POLICY.get_limit_for_account(account)


# Backwards-compatible alias: older code imported get_offline_limit.
def get_offline_limit(account: AccountId) -> Decimal:
    return get_offline_limit_pho(account)


def get_policy_snapshot() -> Dict[str, Any]:
    """
    Return a JSON-serializable view of the current offline credit policy.

    Used by:
      - /api/mesh/policy/snapshot (dev/admin)
      - future GMA / governance dashboards
    """
    return _OFFLINE_POLICY.snapshot_dict()