# backend/modules/chain_sim/chain_sim_model.py

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Dict, Any

PHO = "PHO"
TESS = "TESS"

@dataclass
class AccountState:
    address: str
    balances: Dict[str, str]
    nonce: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {"address": self.address, "balances": dict(self.balances), "nonce": self.nonce}

_ACCOUNTS: Dict[str, AccountState] = {}
_SUPPLY: Dict[str, str] = {PHO: "0", TESS: "0"}

def _parse_amount(amt: str) -> Decimal:
    try:
        v = Decimal(str(amt))
        if v <= 0:
            raise ValueError("amount must be positive")
        return v
    except (InvalidOperation, ValueError):
        raise ValueError("invalid amount")

def get_or_create_account(address: str) -> AccountState:
    if address not in _ACCOUNTS:
        _ACCOUNTS[address] = AccountState(address=address, balances={})
    return _ACCOUNTS[address]

def get_account_view(address: str) -> Dict[str, Any]:
    return get_or_create_account(address).to_dict()

def get_supply_view() -> Dict[str, str]:
    return dict(_SUPPLY)

def _get_balance(acc: AccountState, denom: str) -> Decimal:
    raw = acc.balances.get(denom, "0")
    try:
        return Decimal(raw)
    except InvalidOperation:
        return Decimal("0")

def _set_balance(acc: AccountState, denom: str, value: Decimal) -> None:
    if value < 0:
        raise ValueError("negative balance not allowed")
    acc.balances[denom] = str(value)

def _add_supply(denom: str, delta: Decimal) -> None:
    cur = Decimal(_SUPPLY.get(denom, "0"))
    new = cur + delta
    if new < 0:
        raise ValueError("negative supply not allowed")
    _SUPPLY[denom] = str(new)

def mint(denom: str, signer: str, to_addr: str, amount: str) -> Dict[str, Any]:
    """
    Dev-only mint. Nonce increments ONLY on signer.
    """
    amt = _parse_amount(amount)
    to_acc = get_or_create_account(to_addr)

    bal = _get_balance(to_acc, denom)
    _set_balance(to_acc, denom, bal + amt)
    _add_supply(denom, amt)

    signer_acc = get_or_create_account(signer)
    signer_acc.nonce += 1

    return {
        "ok": True,
        "op": "MINT",
        "denom": denom,
        "amount": str(amt),
        "signer": signer_acc.to_dict(),
        "to": to_acc.to_dict(),
        "supply": get_supply_view(),
    }

def burn(denom: str, signer: str, from_addr: str, amount: str) -> Dict[str, Any]:
    """
    Dev-only burn. Nonce increments ONLY on signer.
    """
    amt = _parse_amount(amount)
    from_acc = get_or_create_account(from_addr)

    bal = _get_balance(from_acc, denom)
    if amt > bal:
        raise ValueError(f"insufficient balance: have {bal}, need {amt}")

    _set_balance(from_acc, denom, bal - amt)
    _add_supply(denom, -amt)

    signer_acc = get_or_create_account(signer)
    signer_acc.nonce += 1

    return {
        "ok": True,
        "op": "BURN",
        "denom": denom,
        "amount": str(amt),
        "signer": signer_acc.to_dict(),
        "from": from_acc.to_dict(),
        "supply": get_supply_view(),
    }

def transfer(denom: str, signer: str, to_addr: str, amount: str) -> Dict[str, Any]:
    """
    Dev-only send. signer == from_addr. Nonce increments ONLY on signer.
    """
    amt = _parse_amount(amount)
    sender = get_or_create_account(signer)
    receiver = get_or_create_account(to_addr)

    sbal = _get_balance(sender, denom)
    if amt > sbal:
        raise ValueError(f"insufficient balance: have {sbal}, need {amt}")

    _set_balance(sender, denom, sbal - amt)
    rbal = _get_balance(receiver, denom)
    _set_balance(receiver, denom, rbal + amt)

    sender.nonce += 1

    return {
        "ok": True,
        "op": "TRANSFER",
        "denom": denom,
        "amount": str(amt),
        "from": sender.to_dict(),
        "to": receiver.to_dict(),
        "supply": get_supply_view(),
    }