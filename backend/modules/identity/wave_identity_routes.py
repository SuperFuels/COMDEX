# backend/modules/identity/wave_identity_routes.py

from __future__ import annotations

from typing import Optional, Dict, Any, List

from fastapi import APIRouter, HTTPException, Query

from backend.modules.identity.wave_identity_model import (
    WaveIdentity,
    lookup_identity,
    list_demo_identities,
)

router = APIRouter(
    prefix="/wave",
    tags=["wave-dev"],
)

# existing /dev/lookup and /dev/demo_contacts stay as-is ...


@router.get("/dev/resolve")
async def wave_identity_resolve(
    wave_addr: Optional[str] = Query(
        default=None,
        description="WaveAddress like alice@waves.glyph",
    ),
    wave_number: Optional[str] = Query(
        default=None,
        description="WaveNumber like +wave-44-1234-5678",
    ),
    pho_account: Optional[str] = Query(
        default=None,
        description="Optional raw PHO account fallback",
    ),
) -> Dict[str, Any]:
    """
    Dev-only: resolve Wave address / number / PHO account
    into a single 'contact' object.

    This is what WaveSendPanel.tsx calls.
    """
    # 1) Try wave_addr / wave_number via the shared helper
    ident: Optional[WaveIdentity] = None
    if wave_addr or wave_number:
        ident = lookup_identity(
            wave_addr=wave_addr,
            wave_number=wave_number,
        )

    # 2) If not found and pho_account is set, synthesize a minimal identity
    if not ident and pho_account:
        ident = WaveIdentity(
            pho_account=pho_account,
            display_name=pho_account,
        )

    if not ident:
        raise HTTPException(
            status_code=404,
            detail="Wave identity not found (dev resolve).",
        )

    return {"contact": ident.to_dict()}