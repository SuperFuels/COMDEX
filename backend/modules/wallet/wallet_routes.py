# backend/modules/wallet/wallet_routes.py

from __future__ import annotations

from decimal import Decimal
from typing import Optional, Dict, Any

from fastapi import APIRouter, Header, Query   # 👈 add Query here

from backend.modules.photon_pay.photon_pay_routes import (
    list_dev_receipts_for_account,
)

from backend.modules.wallet.mesh_wallet_state import (
    get_or_init_local_state_for_api,
    _effective_spendable,  # dev helper: global + local_delta + credit - buffer
)

router = APIRouter(
    prefix="/wallet",
    tags=["wallet"],
)

def _derive_pho_account(owner_wa: Optional[str]) -> str:
    """
    Very simple demo mapping WA -> PHO account.
    Later this becomes a real identity_registry lookup.
    """
    if not owner_wa:
        return "pho1-demo-offline"

    suffix = owner_wa[-6:].replace(":", "").replace("/", "").lower()
    return f"pho1{suffix or 'demo-offline'}"


def _wallet_view(owner_wa: Optional[str]) -> Dict[str, Any]:
    """
    Build the wallet balances payload used by the browser.
    Now driven by mesh local_state (so PHO drops when mesh_pending > 0).

    Semantics:
      - pho_global              = on-chain-style confirmed PHO (demo)
      - mesh_pending_pho        = max(0, -local_net_delta_pho)
      - pho (displayed)         = global_confirmed + local_net_delta - safety_buffer,
                                  clamped so you can only draw down offline_credit_limit
                                  below (global_confirmed - safety_buffer)
      - pho_spendable_local     = global_confirmed + local_net_delta
                                  + offline_credit_limit - safety_buffer
                                  (dev view for “remaining offline spendable”)
    """
    pho_account = _derive_pho_account(owner_wa)

    # Pull mesh local state for this PHO account
    local_balance, _local_log = get_or_init_local_state_for_api(pho_account)

    g = Decimal(local_balance["global_confirmed_pho"])
    d = Decimal(local_balance["local_net_delta_pho"])
    lim = Decimal(local_balance["offline_credit_limit_pho"])
    buf = Decimal(local_balance["safety_buffer_pho"])

    # Mesh pending = how much you've spent offline and not reconciled yet
    mesh_pending = max(Decimal("0"), -d)

    # PHO "spendable" balance shown in the big card:
    #   global_confirmed + local_net_delta - safety_buffer
    # (so sending over mesh reduces it immediately)
    pho_available = g + d - buf

    # Clamp to a floor that respects offline credit:
    # you can draw down at most `offline_limit_pho` below global_confirmed - buffer
    min_avail = g - lim - buf
    if pho_available < min_avail:
        pho_available = min_avail

    # Remaining offline spendable using dev helper:
    #   global + local_delta + limit - buffer
    pho_spendable_local = _effective_spendable(local_balance)

    return {
        "owner_wa": owner_wa,
        "pho_account": pho_account,
        "balances": {
            "pho": str(pho_available),            # big PHO number in UI
            "pho_global": str(g),                 # on-chain confirmed (demo)
            "tess": "42.00",
            "bonds": "3.00",
            "mesh_offline_limit_pho": str(lim),
            "mesh_pending_pho": str(mesh_pending),
            "pho_spendable_local": str(pho_spendable_local),
        },
        # debug only – useful in curl / logs
        "debug_local_net_delta_pho": str(d),
    }


@router.get("/balances")
async def get_wallet_balances(
    x_owner_wa: Optional[str] = Header(default=None, alias="X-Owner-WA"),
) -> Dict[str, Any]:
    """
    Returns wallet balances for the current owner WA.

    - Derives a PHO account from WA (demo)
    - Reads mesh local_state for that account
    - Computes:
        • pho_global              – on-chain confirmed PHO
        • pho                     – spendable (global + local_net_delta - buffer,
                                      clamped by offline_credit_limit)
        • mesh_pending_pho        – offline mesh tx not yet reconciled
        • mesh_offline_limit_pho  – offline credit limit
        • pho_spendable_local     – remaining offline spendable
    """
    return _wallet_view(x_owner_wa)

@router.get("/dev/receipts")
async def wallet_dev_receipts(
    account: str = Query(..., description="PHO account to filter receipts by"),
):
    """
    Dev-only: Photon Pay receipts visible to a given wallet.
    """
    recs = list_dev_receipts_for_account(account)
    return {
        "account": account,
        "count": len(recs),
        "receipts": recs,
    }