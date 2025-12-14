# backend/modules/staking/staking_model.py
from __future__ import annotations

from dataclasses import dataclass, asdict
from threading import Lock
from typing import Any, Dict, List, Optional, Tuple

from backend.modules.chain_sim import chain_sim_model as bank

_LOCK = Lock()

BONDED_POOL_ADDR = "pho1-dev-staking-bonded"


# Minimal structs
@dataclass
class Delegation:
    delegator: str
    validator: str
    amount_tess: str  # int-like string


@dataclass
class Validator:
    address: str
    power: str  # sum delegated TESS (int-like string)
    commission: str = "0"  # stub


@dataclass
class Rewards:
    delegator: str
    accrued_tess: str = "0"  # stub


# In-memory staking state
_VALIDATORS: Dict[str, Validator] = {}
_DELEGATIONS: Dict[Tuple[str, str], Delegation] = {}  # (delegator, validator) -> Delegation
_REWARDS: Dict[str, Rewards] = {}  # delegator -> Rewards


def reset_state() -> None:
    """Dev/test helper: clear staking state (does NOT reset bank state)."""
    with _LOCK:
        _VALIDATORS.clear()
        _DELEGATIONS.clear()
        _REWARDS.clear()


def _as_int(x: Any, field: str) -> int:
    if isinstance(x, int):
        if x < 0:
            raise ValueError(f"{field} cannot be negative")
        return x
    if isinstance(x, str):
        s = x.strip()
        if s.isdigit():
            return int(s)
    raise ValueError(f"{field} must be an int-like string (e.g. '10')")


def _int_str(n: int) -> str:
    if n < 0:
        raise ValueError("negative amount not allowed")
    return str(int(n))


def _get_balance_int(addr: str, denom: str) -> int:
    acc = bank.get_or_create_account(addr)
    bal = (acc.balances or {}).get(denom, "0")
    return _as_int(bal, f"balances.{denom}")


def _set_balance_int(addr: str, denom: str, n: int) -> None:
    acc = bank.get_or_create_account(addr)
    if acc.balances is None:
        acc.balances = {}
    acc.balances[denom] = _int_str(n)


def _bonded_pool_balance_int() -> int:
    return _get_balance_int(BONDED_POOL_ADDR, "TESS")


def _recompute_validator_power_locked(vaddr: str) -> None:
    total = 0
    for (_, validator), d in _DELEGATIONS.items():
        if validator == vaddr:
            total += _as_int(d.amount_tess, "delegation.amount_tess")
    v = _VALIDATORS.get(vaddr) or Validator(address=vaddr, power="0")
    v.power = _int_str(total)
    _VALIDATORS[vaddr] = v


def list_validators() -> List[Dict[str, Any]]:
    with _LOCK:
        vals = sorted(_VALIDATORS.values(), key=lambda v: _as_int(v.power, "power"), reverse=True)
        return [asdict(v) for v in vals]


def list_delegations(delegator: Optional[str] = None) -> List[Dict[str, Any]]:
    with _LOCK:
        items = list(_DELEGATIONS.values())
        if delegator:
            items = [d for d in items if d.delegator == delegator]
        return [asdict(d) for d in items]


def apply_genesis_validators(validators: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Genesis helper:
      validators: [{address, self_delegation_tess, commission?}, ...]
    Requires allocs already applied to bank so validators have spendable TESS.
    """
    applied = 0
    for v in validators or []:
        addr = (v or {}).get("address")
        if not isinstance(addr, str) or not addr:
            continue
        commission = str((v or {}).get("commission", "0"))
        self_del = str((v or {}).get("self_delegation_tess", "0"))

        # ensure validator exists w/ commission
        with _LOCK:
            existing = _VALIDATORS.get(addr)
            if existing:
                existing.commission = commission
            else:
                _VALIDATORS[addr] = Validator(address=addr, power="0", commission=commission)

        # self-delegate (locks TESS into bonded pool, increases power)
        if _as_int(self_del, "self_delegation_tess") > 0:
            delegate(delegator=addr, validator=addr, amount_tess=self_del)
        applied += 1

    return {"ok": True, "applied_validators": applied}


def delegate(*, delegator: str, validator: str, amount_tess: str) -> Dict[str, Any]:
    amt = _as_int(amount_tess, "amount_tess")
    if amt <= 0:
        raise ValueError("amount_tess must be > 0")
    if not delegator or not validator:
        raise ValueError("delegator and validator required")

    with _LOCK:
        bal = _get_balance_int(delegator, "TESS")
        if bal < amt:
            raise ValueError("insufficient TESS balance to delegate")

        # lock model: move from delegator spendable → bonded pool
        _set_balance_int(delegator, "TESS", bal - amt)
        _set_balance_int(BONDED_POOL_ADDR, "TESS", _bonded_pool_balance_int() + amt)

        key = (delegator, validator)
        prev = _DELEGATIONS.get(key)
        prev_amt = _as_int(prev.amount_tess, "amount_tess") if prev else 0
        _DELEGATIONS[key] = Delegation(delegator=delegator, validator=validator, amount_tess=_int_str(prev_amt + amt))

        # ensure validator exists + recompute power
        if validator not in _VALIDATORS:
            _VALIDATORS[validator] = Validator(address=validator, power="0")
        _recompute_validator_power_locked(validator)

        # stub rewards record
        if delegator not in _REWARDS:
            _REWARDS[delegator] = Rewards(delegator=delegator, accrued_tess="0")

        return {
            "ok": True,
            "op": "DELEGATE",
            "delegator": delegator,
            "validator": validator,
            "amount_tess": _int_str(amt),
            "new_delegation_tess": _DELEGATIONS[key].amount_tess,
            "delegator_balance_tess": _int_str(_get_balance_int(delegator, "TESS")),
            "bonded_pool_balance_tess": _int_str(_bonded_pool_balance_int()),
            "validator_power": _VALIDATORS[validator].power,
        }


def undelegate(*, delegator: str, validator: str, amount_tess: str) -> Dict[str, Any]:
    amt = _as_int(amount_tess, "amount_tess")
    if amt <= 0:
        raise ValueError("amount_tess must be > 0")
    if not delegator or not validator:
        raise ValueError("delegator and validator required")

    with _LOCK:
        key = (delegator, validator)
        existing = _DELEGATIONS.get(key)
        if not existing:
            raise ValueError("no existing delegation to undelegate")

        cur = _as_int(existing.amount_tess, "delegation.amount_tess")
        if cur < amt:
            raise ValueError("undelegate amount exceeds current delegation")

        # return from bonded pool → delegator spendable
        bonded = _bonded_pool_balance_int()
        if bonded < amt:
            raise ValueError("bonded pool insufficient (invariant broken)")

        _set_balance_int(BONDED_POOL_ADDR, "TESS", bonded - amt)

        bal = _get_balance_int(delegator, "TESS")
        _set_balance_int(delegator, "TESS", bal + amt)

        new_amt = cur - amt
        if new_amt == 0:
            _DELEGATIONS.pop(key, None)
        else:
            _DELEGATIONS[key] = Delegation(delegator=delegator, validator=validator, amount_tess=_int_str(new_amt))

        _recompute_validator_power_locked(validator)

        return {
            "ok": True,
            "op": "UNDELEGATE",
            "delegator": delegator,
            "validator": validator,
            "amount_tess": _int_str(amt),
            "remaining_delegation_tess": _int_str(new_amt),
            "delegator_balance_tess": _int_str(_get_balance_int(delegator, "TESS")),
            "bonded_pool_balance_tess": _int_str(_bonded_pool_balance_int()),
            "validator_power": _VALIDATORS.get(validator, Validator(address=validator, power="0")).power,
        }


def assert_invariants() -> None:
    with _LOCK:
        for d in _DELEGATIONS.values():
            if _as_int(d.amount_tess, "amount_tess") < 0:
                raise AssertionError("negative delegation")

        for v in _VALIDATORS.values():
            if _as_int(v.power, "power") < 0:
                raise AssertionError("negative validator power")

        # power == sum(delegations)
        for vaddr in list(_VALIDATORS.keys()):
            before = _VALIDATORS[vaddr].power
            _recompute_validator_power_locked(vaddr)
            after = _VALIDATORS[vaddr].power
            if before != after:
                raise AssertionError(f"validator power mismatch for {vaddr}: {before} != {after}")

        # no negative balances for delegators and bonded pool
        touched = {d.delegator for d in _DELEGATIONS.values()}
        touched.add(BONDED_POOL_ADDR)
        for addr in touched:
            if _get_balance_int(addr, "TESS") < 0:
                raise AssertionError("negative TESS balance")