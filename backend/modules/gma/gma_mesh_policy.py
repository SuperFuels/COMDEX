# backend/modules/gma/gma_mesh_policy.py

from __future__ import annotations

from decimal import Decimal
from typing import Dict, Any

from backend.modules.mesh.mesh_types import AccountId

"""
GMA Mesh Offline Credit Policy (stub)

Eventually this will be driven by real on-chain GMAState:

  - default_limit_pho (global)
  - per-account overrides
  - governance controls

For now we keep everything in-memory with a fixed default so that
mesh_wallet_state and mesh_reconcile_service can safely call
get_offline_limit_pho(account) and get_policy_snapshot().
"""

# Global default offline credit limit (in PHO)
_DEFAULT_OFFLINE_LIMIT_PHO = Decimal("25.0")

# Optional in-memory per-account overrides (for future tests)
_ACCOUNT_OVERRIDES: Dict[AccountId, Decimal] = {}


def set_offline_limit(account: AccountId, limit_pho: Decimal | str) -> None:
  """
  Set an in-memory override for a specific account.

  This is only for dev/test; in production this will be backed
  by GMA module state on-chain.
  """
  _ACCOUNT_OVERRIDES[account] = Decimal(str(limit_pho))


def get_offline_limit(account: AccountId) -> Decimal:
  """
  Return the offline credit limit for a given account in PHO (Decimal).

  Internal generic name.
  """
  return _ACCOUNT_OVERRIDES.get(account, _DEFAULT_OFFLINE_LIMIT_PHO)


def get_offline_limit_pho(account: AccountId) -> Decimal:
  """
  Backwards-compatible export used by mesh_wallet_state / mesh_reconcile_service.
  """
  return get_offline_limit(account)


def get_policy_snapshot() -> Dict[str, Any]:
  """
  Lightweight view used by mesh_reconcile_routes and (later) GMA dashboards.

  Everything is stringified so it’s safe to JSON-serialize directly.
  """
  return {
    "default_limit_pho": str(_DEFAULT_OFFLINE_LIMIT_PHO),
    "overrides": {
      acc: str(limit) for acc, limit in _ACCOUNT_OVERRIDES.items()
    },
  }


__all__ = [
  "set_offline_limit",
  "get_offline_limit",
  "get_offline_limit_pho",
  "get_policy_snapshot",
]