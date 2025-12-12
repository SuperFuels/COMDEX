# backend/modules/bonds/bond_state_routes.py

from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from backend.modules.bonds.bond_state_model import (
    get_bond_dev_store,
    BondDevStore,
)

router = APIRouter(
    prefix="/bonds/dev",
    tags=["bonds-dev"],
)


class CreateSeriesRequest(BaseModel):
    name: str
    currency: str = "PHO"
    coupon_rate_bps: int
    maturity_ms: int
    face_value_pho: str


class IssueBondsRequest(BaseModel):
    series_id: str
    owner_account: str
    principal_pho: str


@router.get("/series")
async def list_series():
    store: BondDevStore = get_bond_dev_store()
    return {"series": [s.to_dict() for s in store.list_series()]}


@router.post("/series")
async def create_series(req: CreateSeriesRequest):
    store: BondDevStore = get_bond_dev_store()
    try:
        # validate amount
        Decimal(req.face_value_pho)
    except (InvalidOperation, ValueError):
        raise HTTPException(status_code=400, detail="invalid face_value_pho")

    s = store.create_series(
        name=req.name,
        currency=req.currency,
        coupon_rate_bps=req.coupon_rate_bps,
        maturity_ms=req.maturity_ms,
        face_value_pho=req.face_value_pho,
    )
    return {"ok": True, "series": s.to_dict()}


@router.post("/issue")
async def issue_bonds(req: IssueBondsRequest):
    store: BondDevStore = get_bond_dev_store()
    try:
        Decimal(req.principal_pho)
    except (InvalidOperation, ValueError):
        raise HTTPException(status_code=400, detail="invalid principal_pho")

    try:
        pos = store.issue_bonds(
            series_id=req.series_id,
            owner_account=req.owner_account,
            principal_pho=req.principal_pho,
        )
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return {"ok": True, "position": pos.to_dict()}