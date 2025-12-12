# backend/modules/wallet/wallet_receipts_routes.py

from __future__ import annotations

from typing import Optional, List

from fastapi import APIRouter, Query

from backend.modules.photon_pay.photon_receipt import (
    PhotonPayReceipt,
    dev_all_receipts,
)

router = APIRouter(
    prefix="/wallet",
    tags=["wallet-dev"],
)


def _matches_account(rcpt: PhotonPayReceipt, account: str) -> bool:
    """
    Simple helper: a receipt is relevant to `account` if it is either:
      - from_account == account, or
      - to_account   == account.
    """
    return rcpt.from_account == account or rcpt.to_account == account


@router.get("/dev/receipts")
async def wallet_dev_receipts(
    account: Optional[str] = Query(
        None,
        description="PHO account to filter by (from_account or to_account). "
        "If omitted, returns all dev receipts.",
    ),
    limit: int = Query(50, ge=1, le=500),
):
    """
    Dev-only wallet receipts stub.

    For now this just:
      - reads from the in-memory Photon Pay dev receipts,
      - optionally filters by `account`,
      - returns newest → oldest up to `limit`.
    """
    all_rcpts: List[PhotonPayReceipt] = dev_all_receipts()

    if account:
      filtered = [r for r in all_rcpts if _matches_account(r, account)]
    else:
      filtered = all_rcpts

    # newest first
    filtered = list(reversed(filtered))[:limit]

    return {
        "account": account,
        "count": len(filtered),
        "receipts": [r.to_dict() for r in filtered],
    }