# backend/modules/staking/staking_routes.py
from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException, Query

from backend.modules.staking import staking_model as staking

router = APIRouter(prefix="/staking", tags=["staking-dev"])


@router.get("/dev/validators")
async def dev_validators() -> Dict[str, Any]:
    return {"ok": True, "validators": staking.list_validators()}


@router.get("/dev/delegations")
async def dev_delegations(
    delegator: Optional[str] = Query(None),
) -> Dict[str, Any]:
    return {"ok": True, "delegations": staking.list_delegations(delegator=delegator)}