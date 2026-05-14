# backend/modules/wallet/mesh_wallet_state.py

from __future__ import annotations
from decimal import Decimal
from typing import Tuple

from backend.modules.mesh.mesh_types import LocalBalance
from backend.modules.mesh.mesh_tx import MeshTx


def _d(x: str | int | float) -> Decimal:
    return Decimal(str(x))


def apply_mesh_tx(balance: LocalBalance, tx: MeshTx) -> LocalBalance:
    """
    Pure function: apply a MeshTx to a LocalBalance and return updated copy.
    Does NOT enforce offline limits – that's for policy layer.
    """
    lb = balance.copy()

    amt = _d(tx["amount_pho"])
    net = _d(lb["local_net_delta_pho"])

    if tx["from_account"] == lb["account"]:
        net -= amt
    if tx["to_account"] == lb["account"]:
        net += amt

    lb["local_net_delta_pho"] = str(net)
    return lb


def effective_spendable_local(balance: LocalBalance) -> Tuple[Decimal, dict]:
    """
    Compute what the wallet is allowed to show as 'local spendable PHO'.

    effective = global_confirmed
                + max(local_net_delta, 0)
                - safety_buffer
                clamped so unbacked portion <= offline_credit_limit
    """
    global_conf = _d(balance["global_confirmed_pho"])
    local_delta = _d(balance["local_net_delta_pho"])
    offline_limit = _d(balance["offline_credit_limit_pho"])
    safety = _d(balance["safety_buffer_pho"])

    # Only positive local deltas increase spendable
    positive_local = max(local_delta, Decimal("0"))

    # How much of that is unbacked credit?
    unbacked = max(positive_local - global_conf, Decimal("0"))

    # Clamp unbacked part to offline_limit
    if unbacked > offline_limit:
        # reduce positive_local so unbacked == offline_limit
        excess = unbacked - offline_limit
        positive_local -= excess
        unbacked = offline_limit

    effective = global_conf + positive_local - safety
    if effective < 0:
        effective = Decimal("0")

    debug = {
        "global_confirmed_pho": str(global_conf),
        "local_net_delta_pho": str(local_delta),
        "offline_credit_limit_pho": str(offline_limit),
        "safety_buffer_pho": str(safety),
        "unbacked_local_pho": str(unbacked),
    }

    return effective, debug


__all__ = ["apply_mesh_tx", "effective_spendable_local"]