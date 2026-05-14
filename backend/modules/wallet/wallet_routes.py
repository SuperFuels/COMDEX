# backend/modules/wallet/wallet_routes.py

from __future__ import annotations

import time
import uuid
from decimal import Decimal
from typing import Optional, Dict, Any

from fastapi import APIRouter, Header, Query, HTTPException
from pydantic import BaseModel

# GMA dev logging hooks (supply + reserves)
from backend.modules.gma.gma_state_dev import (
    record_mint_burn,
    record_reserve_move,
)

from backend.modules.photon_pay.photon_pay_routes import (
    list_dev_receipts_for_account,
    log_dev_refund_receipt,
)
from backend.modules.wallet.mesh_wallet_state import (
    get_or_init_local_state_for_api,
    _effective_spendable,  # dev helper: global + local_delta + credit - buffer
)

router = APIRouter(
    prefix="/wallet",
    tags=["wallet"],
)


# ───────────────────────────────────────────────
# Helpers
# ───────────────────────────────────────────────


def _now_ms() -> int:
    return int(time.time() * 1000)


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


# ───────────────────────────────────────────────
# Dev transfer + refund models
# ───────────────────────────────────────────────


class DevTransferRequest(BaseModel):
    from_account: str
    to_account: str
    amount_pho: str
    memo: Optional[str] = None


class DevRefundRequest(BaseModel):
    receipt_id: str
    from_account: str
    to_account: str
    amount_pho: str
    channel: str = "net"   # "net" | "mesh" etc.
    memo: Optional[str] = None
    invoice_id: Optional[str] = None


# ───────────────────────────────────────────────
# Dev transfer helper (used by docs + Photon Pay)
# ───────────────────────────────────────────────


async def dev_transfer_pho(
    from_account: str,
    to_account: str,
    amount_pho: str,
    memo: str = "",
) -> Dict[str, Any]:
    """
    Dev-only PHO transfer helper used by:
      • /wallet/dev/transfer
      • Transactable-docs PHO_TRANSFER legs
      • Photon Pay “net” payments

    Enforces a simple “no overspend past 0 after safety buffer” rule.
    """
    try:
        amt = Decimal(str(amount_pho))
    except Exception:
        raise HTTPException(status_code=400, detail="invalid amount_pho")

    if amt <= 0:
        raise HTTPException(status_code=400, detail="amount_pho must be positive")

    # Load balance views for from/to accounts
    from_state, _ = get_or_init_local_state_for_api(from_account)
    to_state, _ = get_or_init_local_state_for_api(to_account)

    g_from = Decimal(from_state["global_confirmed_pho"])
    buf_from = Decimal(from_state["safety_buffer_pho"])

    # Available = global_confirmed - safety_buffer
    # (mesh credit is for mesh, not net transfers)
    available = g_from - buf_from
    if amt > available:
        raise HTTPException(
            status_code=400,
            detail=f"insufficient PHO balance: need {amt}, have {available} after buffer",
        )

    # Apply transfer to global_confirmed balances
    from_state["global_confirmed_pho"] = str(g_from - amt)

    g_to = Decimal(to_state["global_confirmed_pho"])
    to_state["global_confirmed_pho"] = str(g_to + amt)

    tx_id = f"DEV_PHO_TX_{uuid.uuid4().hex[:8]}"
    created = _now_ms()

    transfer = {
        "tx_id": tx_id,
        "from_account": from_account,
        "to_account": to_account,
        "amount_pho": str(amt),
        "memo": memo,
        "created_at_ms": created,
    }

    # NOTE: dev_transfer_pho itself does *not* change total PHO supply or reserves,
    # so we do NOT call record_mint_burn / record_reserve_move here.
    # Those should be called from mint/burn / bond / savings flows.

    # Shape is friendly to both wallet + transactable_docs callers
    return {
        "ok": True,
        "tx_id": tx_id,
        "transfer": transfer,
    }


# ───────────────────────────────────────────────
# Routes
# ───────────────────────────────────────────────


@router.get("/balances")
async def get_wallet_balances(
    x_owner_wa: Optional[str] = Header(default=None, alias="X-Owner-WA"),
) -> Dict[str, Any]:
    """
    Returns wallet balances for the current owner WA.
    """
    return _wallet_view(x_owner_wa)


@router.post("/dev/transfer")
async def wallet_dev_transfer(body: DevTransferRequest) -> Dict[str, Any]:
    """
    Dev-only: move PHO between accounts via wallet engine.

    Used by:
      • Photon Pay Buyer “online / net” payments
      • Any future dev tools that want a simple wallet transfer.
    """
    return await dev_transfer_pho(
        from_account=body.from_account,
        to_account=body.to_account,
        amount_pho=body.amount_pho,
        memo=body.memo or "",
    )


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


@router.post("/dev/refund")
async def wallet_dev_refund(body: DevRefundRequest) -> Dict[str, Any]:
    """
    Dev-only: refund a Photon Pay receipt.

    - Moves PHO back via dev_transfer_pho(...)
    - Logs a *negative* PhotonPay receipt linked to the original.
    """
    try:
        amt = Decimal(body.amount_pho)
        if amt <= 0:
            raise HTTPException(status_code=400, detail="amount_pho must be positive")
    except Exception:
        raise HTTPException(status_code=400, detail="invalid amount_pho")

    # Move PHO back (merchant → buyer)
    tx = await dev_transfer_pho(
        from_account=body.from_account,
        to_account=body.to_account,
        amount_pho=str(amt),
        memo=body.memo or f"Refund {body.receipt_id}",
    )

    # Log negative refund receipt in Photon Pay dev model
    refund_rcpt = log_dev_refund_receipt(
        from_account=body.from_account,
        to_account=body.to_account,
        amount_pho=str(amt),
        memo=body.memo or f"Refund {body.receipt_id}",
        channel=body.channel,
        invoice_id=body.invoice_id,
        refund_of=body.receipt_id,
    )

    return {
        "ok": True,
        "tx": tx,
        "refund_receipt": refund_rcpt,
    }