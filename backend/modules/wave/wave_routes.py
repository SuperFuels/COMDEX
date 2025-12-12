# backend/modules/wave/wave_routes.py

from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

router = APIRouter(
    prefix="/wave",
    tags=["wave-dev"],
)


# ───────────────────────────────────────────────
# Dev Wave identity registry
# ───────────────────────────────────────────────

@dataclass
class WaveContact:
    pho_account: str
    wave_addr: str
    wave_number: str
    display_name: str
    avatar_url: Optional[str] = None

    def to_dict(self) -> dict:
        return asdict(self)


# Same demo identities you saw from /api/wave/dev/demo_contacts
_DEMO_CONTACTS: List[WaveContact] = [
    WaveContact(
        pho_account="pho1-demo-offline",
        wave_addr="you@waves.glyph",
        wave_number="+wave-44-0000-0000",
        display_name="Demo You",
        avatar_url=None,
    ),
    WaveContact(
        pho_account="pho1-demo-merchant",
        wave_addr="cafe@glyph.local",
        wave_number="+wave-44-1000-0001",
        display_name="Demo Café",
        avatar_url=None,
    ),
    WaveContact(
        pho_account="pho1receiver",
        wave_addr="receiver@glyph.local",
        wave_number="+wave-44-1000-0002",
        display_name="Demo Receiver",
        avatar_url=None,
    ),
]


def _all_contacts() -> List[WaveContact]:
    # Later this becomes a real identity_registry lookup.
    return list(_DEMO_CONTACTS)


def _find_contact(
    *,
    wave_addr: Optional[str] = None,
    wave_number: Optional[str] = None,
    pho_account: Optional[str] = None,
) -> Optional[WaveContact]:
    contacts = _all_contacts()

    if wave_addr:
        wa = wave_addr.strip().lower()
        for c in contacts:
            if c.wave_addr.lower() == wa:
                return c

    if wave_number:
        wn = wave_number.strip()
        for c in contacts:
            if c.wave_number == wn:
                return c

    if pho_account:
        acc = pho_account.strip()
        for c in contacts:
            if c.pho_account == acc:
                return c

    return None


# ───────────────────────────────────────────────
# Existing dev contacts endpoint
# ───────────────────────────────────────────────

@router.get("/dev/demo_contacts")
async def wave_dev_demo_contacts():
    """
    Dev-only: return a small fixed set of demo contacts.
    """
    return {"contacts": [c.to_dict() for c in _all_contacts()]}


# ───────────────────────────────────────────────
# New: resolve Wave address/number → PHO account
# ───────────────────────────────────────────────

class WaveResolveResponse(BaseModel):
    contact: dict  # WaveContact as dict


@router.get("/dev/resolve", response_model=WaveResolveResponse)
async def wave_dev_resolve(
    wave_addr: Optional[str] = Query(None),
    wave_number: Optional[str] = Query(None),
    pho_account: Optional[str] = Query(None),
):
    """
    Dev-only Wave identity resolver.

    Accepts ANY of:
      - wave_addr     (e.g. 'cafe@glyph.local')
      - wave_number   (e.g. '+wave-44-1000-0001')
      - pho_account   (e.g. 'pho1-demo-merchant')

    Returns the matched contact, including the canonical PHO account
    to use for payments.
    """
    if not (wave_addr or wave_number or pho_account):
        raise HTTPException(
            status_code=400,
            detail="provide at least one of wave_addr, wave_number, pho_account",
        )

    contact = _find_contact(
        wave_addr=wave_addr,
        wave_number=wave_number,
        pho_account=pho_account,
    )

    if contact is None:
        raise HTTPException(status_code=404, detail="contact not found")

    return {"contact": contact.to_dict()}