# backend/modules/identity/wave_identity_model.py

from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Optional, Dict, List


@dataclass
class WaveIdentity:
    """
    Dev-only Wave identity record.

    This is the runtime cousin of the P7_8 WaveAddress / WaveNumber spec:
      - wave_addr: alice@waves.glyph-style handle
      - wave_number: +wave-cc-xxxx-xxxx phone-ish identifier
      - pho_account: the PHO account to receive funds / messages
    """
    pho_account: str
    wave_addr: Optional[str] = None
    wave_number: Optional[str] = None
    display_name: Optional[str] = None
    avatar_url: Optional[str] = None

    def to_dict(self) -> Dict[str, object]:
        return asdict(self)


# --- dev in-memory directory -------------------------------------------------

_DEMO_IDENTITIES: List[WaveIdentity] = [
    WaveIdentity(
        pho_account="pho1-demo-offline",
        wave_addr="you@waves.glyph",
        wave_number="+wave-44-0000-0000",
        display_name="Demo You",
    ),
    WaveIdentity(
        pho_account="pho1-demo-merchant",
        wave_addr="cafe@glyph.local",
        wave_number="+wave-44-1000-0001",
        display_name="Demo Café",
    ),
    WaveIdentity(
        pho_account="pho1receiver",
        wave_addr="receiver@glyph.local",
        wave_number="+wave-44-1000-0002",
        display_name="Demo Receiver",
    ),
]


_WAVE_ADDR_INDEX: Dict[str, WaveIdentity] = {
    ident.wave_addr: ident
    for ident in _DEMO_IDENTITIES
    if ident.wave_addr
}

_WAVE_NUMBER_INDEX: Dict[str, WaveIdentity] = {
    ident.wave_number: ident
    for ident in _DEMO_IDENTITIES
    if ident.wave_number
}


def lookup_identity(
    *,
    wave_addr: Optional[str] = None,
    wave_number: Optional[str] = None,
) -> Optional[WaveIdentity]:
    """
    Dev lookup helper:
      - if wave_addr is provided, try that first
      - otherwise, try wave_number
    """
    if wave_addr:
        ident = _WAVE_ADDR_INDEX.get(wave_addr)
        if ident:
            return ident

    if wave_number:
        return _WAVE_NUMBER_INDEX.get(wave_number)

    return None


def list_demo_identities() -> List[WaveIdentity]:
    """Return all dev identities (for /dev/demo_contacts)."""
    return list(_DEMO_IDENTITIES)