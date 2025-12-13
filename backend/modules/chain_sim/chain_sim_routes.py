# backend/modules/chain_sim/chain_sim_routes.py

from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from backend.modules.chain_sim.chain_sim_model import (
    PHO,
    TESS,
    mint,
    burn,
    transfer,
    get_account_view,
    get_supply_view,
)

router = APIRouter(
    prefix="/chain_sim",
    tags=["chain-sim-dev"],
)


class DevMintBody(BaseModel):
    denom: str = PHO
    to: str
    amount: str


class DevBurnBody(BaseModel):
    denom: str = PHO
    from_addr: str
    amount: str


class DevTransferBody(BaseModel):
    denom: str = PHO
    from_addr: str
    to: str
    amount: str


@router.get("/dev/account")
async def chain_sim_get_account(
    address: str = Query(..., description="Account address (e.g. pho1- style)"),
) -> Dict[str, Any]:
    """
    Dev-only: inspect an account balances + nonce.
    """
    return get_account_view(address)


@router.get("/dev/supply")
async def chain_sim_get_supply() -> Dict[str, str]:
    """
    Dev-only: total supply per denom in this in-memory chain_sim.
    """
    return get_supply_view()


@router.post("/dev/mint")
async def chain_sim_dev_mint(body: DevMintBody) -> Dict[str, Any]:
    """
    Dev-only: mint PHO/TESS to an account.
    Real chain would gate this via GMA / governance.
    """
    try:
        return mint(body.denom, body.to, body.amount)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/dev/burn")
async def chain_sim_dev_burn(body: DevBurnBody) -> Dict[str, Any]:
    """
    Dev-only: burn PHO/TESS from an account.
    """
    try:
        return burn(body.denom, body.from_addr, body.amount)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/dev/transfer")
async def chain_sim_dev_transfer(body: DevTransferBody) -> Dict[str, Any]:
    """
    Dev-only: transfer PHO/TESS between accounts.
    """
    try:
        return transfer(body.denom, body.from_addr, body.to, body.amount)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))