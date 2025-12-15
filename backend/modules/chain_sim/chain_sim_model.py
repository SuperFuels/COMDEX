# backend/modules/chain_sim/chain_sim_model.py
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from threading import RLock
from typing import Any, Dict, List, Optional

PHO = "PHO"
TESS = "TESS"
_DEFAULT_DENOMS = (PHO, TESS)

_LOCK = RLock()

# ───────────────────────────────────────────────
# Dev fee plumbing (P1_4 slice)
# ───────────────────────────────────────────────

FEE_DENOM = "PHO"
FEE_COLLECTOR = "pho1-dev-fee-collector"
FEE_AMOUNT = 1


@dataclass
class AccountState:
    address: str
    balances: Dict[str, str]
    nonce: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "address": self.address,
            "balances": dict(self.balances or {}),
            "nonce": int(self.nonce or 0),
        }


_ACCOUNTS: Dict[str, AccountState] = {}
_SUPPLY: Dict[str, str] = {PHO: "0", TESS: "0"}


# ───────────────────────────────────────────────
# Amount parsing (dev chain: integer-like amounts)
# ───────────────────────────────────────────────

def _parse_nonneg_int(x: Any, *, field: str, allow_zero: bool) -> int:
    """
    Accept int/Decimal/numeric-string. Must be integer-like.
    """
    if x is None:
        raise ValueError(f"{field} is required")

    if isinstance(x, int):
        if x < 0 or (x == 0 and not allow_zero):
            raise ValueError(f"{field} must be {'>= 0' if allow_zero else '> 0'}")
        return x

    s = str(x).strip()
    if s == "":
        raise ValueError(f"{field} is required")

    try:
        d = Decimal(s)
    except InvalidOperation:
        raise ValueError(f"{field} must be an integer-like value")

    if d != d.to_integral_value():
        raise ValueError(f"{field} must be an integer-like value")

    n = int(d)
    if n < 0 or (n == 0 and not allow_zero):
        raise ValueError(f"{field} must be {'>= 0' if allow_zero else '> 0'}")
    return n


def _parse_amount_pos(x: Any) -> int:
    return _parse_nonneg_int(x, field="amount", allow_zero=False)


def _ensure_supply_defaults_locked() -> None:
    for d in _DEFAULT_DENOMS:
        if d not in _SUPPLY:
            _SUPPLY[d] = "0"


# ───────────────────────────────────────────────
# Core getters
# ───────────────────────────────────────────────

def get_or_create_account(address: str) -> AccountState:
    addr = str(address).strip()
    if not addr:
        raise ValueError("address required")

    with _LOCK:
        acc = _ACCOUNTS.get(addr)
        if acc is None:
            acc = AccountState(address=addr, balances={}, nonce=0)
            _ACCOUNTS[addr] = acc
        if acc.balances is None:
            acc.balances = {}
        acc.nonce = int(acc.nonce or 0)
        return acc


def get_account_view(address: str) -> Dict[str, Any]:
    with _LOCK:
        return get_or_create_account(address).to_dict()


def get_supply_view() -> Dict[str, str]:
    with _LOCK:
        _ensure_supply_defaults_locked()
        return dict(_SUPPLY)


# ───────────────────────────────────────────────
# Balance/supply math
# ───────────────────────────────────────────────

def _get_balance_int(acc: AccountState, denom: str) -> int:
    raw = (acc.balances or {}).get(str(denom), "0")
    s = str(raw).strip()
    if s == "":
        return 0
    try:
        d = Decimal(s)
    except InvalidOperation:
        return 0
    if d != d.to_integral_value():
        return 0
    n = int(d)
    return n if n >= 0 else 0


def _set_balance_int(acc: AccountState, denom: str, value: int) -> None:
    if value < 0:
        raise ValueError("negative balance not allowed")
    if acc.balances is None:
        acc.balances = {}
    acc.balances[str(denom)] = str(int(value))


def _add_supply_int(denom: str, delta: int) -> None:
    _ensure_supply_defaults_locked()
    cur_s = str(_SUPPLY.get(str(denom), "0")).strip() or "0"
    cur = _parse_nonneg_int(cur_s, field="supply", allow_zero=True)
    new = cur + int(delta)
    if new < 0:
        raise ValueError("negative supply not allowed")
    _SUPPLY[str(denom)] = str(int(new))


def _move_no_nonce(denom: str, from_addr: str, to_addr: str, amt: int) -> None:
    """
    Move balance between accounts without touching nonces.
    Must be called under _LOCK by callers that need atomicity.
    """
    if amt <= 0:
        return

    from_acc = get_or_create_account(from_addr)
    to_acc = get_or_create_account(to_addr)

    bal = _get_balance_int(from_acc, denom)
    if amt > bal:
        raise ValueError(f"insufficient balance for fee: have {bal}, need {amt}")

    _set_balance_int(from_acc, denom, bal - amt)
    rbal = _get_balance_int(to_acc, denom)
    _set_balance_int(to_acc, denom, rbal + amt)


def charge_fee_if_needed(
    *,
    signer: str,
    op: str,
    mint_denom: Optional[str] = None,
    mint_amount: Optional[int] = None,
) -> Optional[Dict[str, Any]]:
    """
    Returns a fee dict for receipts/ledger, or None.

    Modes:
      - mint_carveout: BANK_MINT when minting PHO => carve fee out of minted amount
      - charge: BANK_SEND / BANK_BURN => transfer fixed PHO fee to collector
    """
    fee_amt = int(FEE_AMOUNT)
    fee_denom = str(FEE_DENOM)
    collector = str(FEE_COLLECTOR)

    if op == "BANK_MINT" and str(mint_denom or "") == fee_denom:
        if mint_amount is None or int(mint_amount) < fee_amt:
            raise ValueError(f"mint amount must be >= fee ({fee_amt} {fee_denom})")
        return {"denom": fee_denom, "amount": str(fee_amt), "collector": collector, "mode": "mint_carveout"}

    if op in ("BANK_SEND", "BANK_BURN"):
        return {"denom": fee_denom, "amount": str(fee_amt), "collector": collector, "mode": "charge"}

    return None


# ───────────────────────────────────────────────
# Tx-like operations (dev) + fees (atomic)
# ───────────────────────────────────────────────

def mint(
    denom: str,
    signer: str,
    to_addr: str,
    amount: Any,
    *,
    fee: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Dev-only mint. Nonce increments ONLY on signer.

    Fee rule:
      - If fee.mode == "mint_carveout" (only when denom==PHO), mint (amount-fee) to recipient
        and mint fee to collector, while incrementing signer nonce exactly once.
    """
    denom = str(denom)
    amt = _parse_amount_pos(amount)

    with _LOCK:
        if isinstance(fee, dict) and fee.get("mode") == "mint_carveout":
            fee_amt = int(fee.get("amount") or 0)
            fee_denom = str(fee.get("denom") or FEE_DENOM)
            collector = str(fee.get("collector") or FEE_COLLECTOR)

            if denom != fee_denom:
                raise ValueError("mint carve-out fee only valid when minting fee denom")
            if fee_amt <= 0:
                raise ValueError("invalid fee amount")
            if amt < fee_amt:
                raise ValueError(f"mint amount must be >= fee ({fee_amt} {fee_denom})")

            to_acc = get_or_create_account(to_addr)
            col_acc = get_or_create_account(collector)

            # mint (amt-fee) to recipient
            bal = _get_balance_int(to_acc, denom)
            _set_balance_int(to_acc, denom, bal + (amt - fee_amt))

            # mint fee to collector
            cbal = _get_balance_int(col_acc, denom)
            _set_balance_int(col_acc, denom, cbal + fee_amt)

            # total supply increases by full amt
            _add_supply_int(denom, amt)

            signer_acc = get_or_create_account(signer)
            signer_acc.nonce = int(signer_acc.nonce or 0) + 1

            return {
                "ok": True,
                "op": "MINT",
                "denom": denom,
                "amount": str(int(amt)),
                "signer": signer_acc.to_dict(),
                "to": to_acc.to_dict(),
                "supply": get_supply_view(),
                "fee": dict(fee),
            }

        # normal mint
        to_acc = get_or_create_account(to_addr)

        bal = _get_balance_int(to_acc, denom)
        _set_balance_int(to_acc, denom, bal + amt)
        _add_supply_int(denom, amt)

        signer_acc = get_or_create_account(signer)
        signer_acc.nonce = int(signer_acc.nonce or 0) + 1

        return {
            "ok": True,
            "op": "MINT",
            "denom": denom,
            "amount": str(int(amt)),
            "signer": signer_acc.to_dict(),
            "to": to_acc.to_dict(),
            "supply": get_supply_view(),
        }


def burn(
    denom: str,
    signer: str,
    from_addr: str,
    amount: Any,
    *,
    fee: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Dev-only burn. Nonce increments ONLY on signer.

    Fee rule:
      - If fee.mode == "charge": move fixed PHO fee from signer -> collector (no extra nonce)
      - Must be atomic: burn + fee must both succeed or neither.
    """
    denom = str(denom)
    amt = _parse_amount_pos(amount)

    with _LOCK:
        from_acc = get_or_create_account(from_addr)

        bal = _get_balance_int(from_acc, denom)
        if amt > bal:
            raise ValueError(f"insufficient balance: have {bal}, need {amt}")

        fee_used: Optional[Dict[str, Any]] = None
        if isinstance(fee, dict) and fee.get("mode") == "charge":
            fee_amt = int(fee.get("amount") or 0)
            fee_denom = str(fee.get("denom") or FEE_DENOM)
            collector = str(fee.get("collector") or FEE_COLLECTOR)
            if fee_amt > 0:
                signer_acc = get_or_create_account(signer)
                sfee_bal = _get_balance_int(signer_acc, fee_denom)
                if fee_amt > sfee_bal:
                    raise ValueError(f"insufficient balance for fee: have {sfee_bal}, need {fee_amt}")
                fee_used = {"denom": fee_denom, "amount": str(fee_amt), "collector": collector, "mode": "charge"}

        # apply burn
        _set_balance_int(from_acc, denom, bal - amt)
        _add_supply_int(denom, -amt)

        # apply fee move (no nonce bump)
        if fee_used:
            _move_no_nonce(str(fee_used["denom"]), signer, str(fee_used["collector"]), int(fee_used["amount"]))

        signer_acc = get_or_create_account(signer)
        signer_acc.nonce = int(signer_acc.nonce or 0) + 1

        out = {
            "ok": True,
            "op": "BURN",
            "denom": denom,
            "amount": str(int(amt)),
            "signer": signer_acc.to_dict(),
            "from": from_acc.to_dict(),
            "supply": get_supply_view(),
        }
        if fee_used:
            out["fee"] = dict(fee_used)
        return out


def transfer(
    denom: str,
    signer: str,
    to_addr: str,
    amount: Any,
    *,
    fee: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Dev-only send. signer == from_addr. Nonce increments ONLY on signer.

    Fee rule:
      - If fee.mode == "charge": move fixed PHO fee signer -> collector (no extra nonce)
      - Must be atomic: transfer + fee must both succeed or neither.
    """
    denom = str(denom)
    amt = _parse_amount_pos(amount)

    with _LOCK:
        sender = get_or_create_account(signer)
        receiver = get_or_create_account(to_addr)

        sbal = _get_balance_int(sender, denom)
        if amt > sbal:
            raise ValueError(f"insufficient balance: have {sbal}, need {amt}")

        fee_used: Optional[Dict[str, Any]] = None
        if isinstance(fee, dict) and fee.get("mode") == "charge":
            fee_amt = int(fee.get("amount") or 0)
            fee_denom = str(fee.get("denom") or FEE_DENOM)
            collector = str(fee.get("collector") or FEE_COLLECTOR)
            if fee_amt > 0:
                sfee_bal = _get_balance_int(sender, fee_denom)
                if fee_amt > sfee_bal:
                    raise ValueError(f"insufficient balance for fee: have {sfee_bal}, need {fee_amt}")
                fee_used = {"denom": fee_denom, "amount": str(fee_amt), "collector": collector, "mode": "charge"}

        # apply transfer
        _set_balance_int(sender, denom, sbal - amt)
        rbal = _get_balance_int(receiver, denom)
        _set_balance_int(receiver, denom, rbal + amt)

        # apply fee move (no nonce bump)
        if fee_used:
            _move_no_nonce(str(fee_used["denom"]), signer, str(fee_used["collector"]), int(fee_used["amount"]))

        sender.nonce = int(sender.nonce or 0) + 1

        out = {
            "ok": True,
            "op": "TRANSFER",
            "denom": denom,
            "amount": str(int(amt)),
            "from": sender.to_dict(),
            "to": receiver.to_dict(),
            "supply": get_supply_view(),
        }
        if fee_used:
            out["fee"] = dict(fee_used)
        return out


# ───────────────────────────────────────────────
# Genesis + supply recompute
# ───────────────────────────────────────────────

def recompute_supply() -> None:
    """
    Recompute _SUPPLY from all account balances.
    Always includes PHO/TESS keys (even if 0) for stability.
    """
    with _LOCK:
        totals: Dict[str, int] = {d: 0 for d in _DEFAULT_DENOMS}

        for acc in _ACCOUNTS.values():
            for denom, amt in (acc.balances or {}).items():
                ds = str(denom)
                s = str(amt).strip()
                if s == "":
                    n = 0
                else:
                    try:
                        d = Decimal(s)
                    except InvalidOperation:
                        n = 0
                    else:
                        if d != d.to_integral_value():
                            n = 0
                        else:
                            n = int(d)
                totals[ds] = totals.get(ds, 0) + n

        _SUPPLY.clear()
        for denom in sorted(totals.keys()):
            v = totals[denom]
            if v < 0:
                raise AssertionError(f"negative supply computed for {denom}: {v}")
            _SUPPLY[denom] = str(int(v))

        _ensure_supply_defaults_locked()


def apply_genesis_allocs(allocs: List[dict]) -> None:
    """
    Genesis seeding: set balances/nonces directly, then recompute supply.
    Skips 0 balances. Does NOT increment any nonces.
    Drops empty accounts for stable state_root.
    """
    with _LOCK:
        _ACCOUNTS.clear()
        _SUPPLY.clear()

        for a in allocs or []:
            if not isinstance(a, dict):
                continue

            addr = str(a.get("address") or "").strip()
            if not addr:
                continue

            bals_in = a.get("balances") or {}
            if not isinstance(bals_in, dict):
                continue

            acc = get_or_create_account(addr)
            acc.nonce = 0
            acc.balances.clear()

            for denom, amount in bals_in.items():
                ds = str(denom)
                n = _parse_nonneg_int(amount, field=f"balance[{ds}]", allow_zero=True)
                if n == 0:
                    continue
                acc.balances[ds] = str(int(n))

            if (not acc.balances) and acc.nonce == 0:
                _ACCOUNTS.pop(addr, None)

        recompute_supply()


# ───────────────────────────────────────────────
# Invariants + reset
# ───────────────────────────────────────────────

def assert_invariants() -> None:
    """
    Dev invariant hook:
      - No negative balances.
      - Balances are int-like strings.
      - Supply equals sum(accounts) per denom.
      - Supply always has default denoms present.
    """
    with _LOCK:
        _ensure_supply_defaults_locked()

        totals: Dict[str, int] = {}

        for acc in _ACCOUNTS.values():
            balances = acc.balances or {}
            for denom, amt in balances.items():
                s = str(amt).strip()
                if s == "":
                    n = 0
                else:
                    try:
                        d = Decimal(s)
                    except InvalidOperation:
                        raise AssertionError(f"non-int balance: {acc.address} {denom}={amt}")
                    if d != d.to_integral_value():
                        raise AssertionError(f"non-int balance: {acc.address} {denom}={amt}")
                    n = int(d)

                if n < 0:
                    raise AssertionError(f"negative balance: {acc.address} {denom}={n}")
                totals[str(denom)] = totals.get(str(denom), 0) + n

        denoms = set(totals.keys()) | set(_SUPPLY.keys()) | set(_DEFAULT_DENOMS)
        for denom in sorted(denoms):
            rec_s = str(_SUPPLY.get(denom, "0")).strip() or "0"
            try:
                d = Decimal(rec_s)
            except InvalidOperation:
                raise AssertionError(f"non-int supply: {denom}={_SUPPLY.get(denom)}")
            if d != d.to_integral_value():
                raise AssertionError(f"non-int supply: {denom}={_SUPPLY.get(denom)}")
            rec_n = int(d)

            calc_n = totals.get(denom, 0)
            if rec_n != calc_n:
                raise AssertionError(f"supply mismatch for {denom}: recorded={rec_n} computed={calc_n}")


def reset_state() -> None:
    """
    Dev/test helper: clear all in-memory bank state (accounts + supply)
    and restore canonical empty supply keys to prevent state_root drift.
    """
    with _LOCK:
        _ACCOUNTS.clear()
        _SUPPLY.clear()
        _SUPPLY[PHO] = "0"
        _SUPPLY[TESS] = "0"