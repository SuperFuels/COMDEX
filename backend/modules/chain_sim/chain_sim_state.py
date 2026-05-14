from __future__ import annotations

import hashlib
import json
import time
from dataclasses import is_dataclass
from typing import Any, Dict, List, Optional, Tuple

_DEFAULT_DENOMS = ("PHO", "TESS")


def _now_ms() -> int:
    return int(time.time() * 1000)


def _stable_json(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _sha256_hex(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def compute_state_root(state: Dict[str, Any]) -> str:
    """
    Deterministic root over the *entire* snapshot (config + bank + staking).
    """
    return _sha256_hex(_stable_json(state))


# ───────────────────────────────────────────────
# Small helpers
# ───────────────────────────────────────────────

def _get_attr(obj: Any, name: str) -> Any:
    return getattr(obj, name, None)


def _int0(x: Any) -> int:
    try:
        return int(str(x).strip() or "0")
    except Exception:
        return 0


def _clean_balances(bals: Any) -> Dict[str, str]:
    """
    Normalize balances:
      - ensure dict[str,str]
      - drop zero entries (stabilizes snapshots)
      - stable key order via sorted() at return site
    """
    if not isinstance(bals, dict):
        return {}
    out: Dict[str, str] = {}
    for denom, amt in bals.items():
        d = str(denom)
        n = _int0(amt)
        if n != 0:
            out[d] = str(n)
    # keep deterministic order
    return {k: out[k] for k in sorted(out.keys())}


# ───────────────────────────────────────────────
# Bank helpers (best-effort container discovery)
# ───────────────────────────────────────────────

def _locate_bank_containers(bank_mod: Any) -> Tuple[Optional[Any], Dict[str, Any], Dict[str, Any]]:
    """
    Returns: (lock_or_none, accounts_dict, supply_dict)
    Tries common container names.
    """
    lock = _get_attr(bank_mod, "_LOCK") or _get_attr(bank_mod, "LOCK")

    accounts = (
        _get_attr(bank_mod, "_ACCOUNTS")
        or _get_attr(bank_mod, "ACCOUNTS")
        or _get_attr(bank_mod, "accounts")
        or _get_attr(_get_attr(bank_mod, "STATE"), "accounts")
    )
    supply = (
        _get_attr(bank_mod, "_SUPPLY")
        or _get_attr(bank_mod, "SUPPLY")
        or _get_attr(bank_mod, "supply")
        or _get_attr(_get_attr(bank_mod, "STATE"), "supply")
    )

    if not isinstance(accounts, dict):
        accounts = {}
    if not isinstance(supply, dict):
        supply = {}

    return lock, accounts, supply


def _account_view_from_obj(addr: str, acc_obj: Any) -> Dict[str, Any]:
    bals_raw = getattr(acc_obj, "balances", None) or {}
    nonce = int(getattr(acc_obj, "nonce", 0) or 0)
    bals = _clean_balances(bals_raw)
    return {"balances": bals, "nonce": nonce}


def _compute_supply_from_accounts_dict(accounts_view: Dict[str, Dict[str, Any]]) -> Dict[str, str]:
    out: Dict[str, int] = {}
    for _addr, a in accounts_view.items():
        bals = (a or {}).get("balances") or {}
        if not isinstance(bals, dict):
            continue
        for denom, amt in bals.items():
            out[str(denom)] = out.get(str(denom), 0) + _int0(amt)

    # ensure default denoms always exist
    for d in _DEFAULT_DENOMS:
        out.setdefault(d, 0)

    # stable
    return {k: str(out[k]) for k in sorted(out.keys())}


def export_bank_state(bank_mod: Any) -> Dict[str, Any]:
    """
    Export a deterministic bank snapshot:
      - accounts is a dict {address: {balances, nonce}}
      - drops empty accounts (balances empty AND nonce==0)
      - supply is computed from exported accounts, and includes default denoms
      - recorded_supply is included for debugging
    """
    lock, accounts, supply = _locate_bank_containers(bank_mod)

    def _export() -> Dict[str, Any]:
        accounts_out: Dict[str, Dict[str, Any]] = {}

        for addr in sorted(accounts.keys()):
            acc_obj = accounts[addr]
            view = _account_view_from_obj(addr, acc_obj)
            # drop empty accounts (stabilizes state_root)
            if (not view["balances"]) and int(view["nonce"]) == 0:
                continue
            accounts_out[str(addr)] = view

        computed_supply = _compute_supply_from_accounts_dict(accounts_out)
        recorded_supply = {str(k): str(v) for k, v in sorted(supply.items(), key=lambda kv: str(kv[0]))}

        return {
            "accounts": accounts_out,
            "supply": computed_supply,
            "recorded_supply": recorded_supply,
        }

    if lock:
        with lock:
            return _export()
    return _export()


def _parse_accounts_in(bank_state: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    """
    Accept either:
      - accounts: [{address, balances, nonce}, ...]
      - accounts: {address: {balances, nonce}, ...}
    Normalize into dict form.
    """
    raw = (bank_state or {}).get("accounts")

    if isinstance(raw, dict):
        out: Dict[str, Dict[str, Any]] = {}
        for addr, v in raw.items():
            if not addr:
                continue
            if not isinstance(v, dict):
                v = {}
            out[str(addr)] = {
                "balances": _clean_balances(v.get("balances") or {}),
                "nonce": int(v.get("nonce", 0) or 0),
            }
        # stable keys
        return {k: out[k] for k in sorted(out.keys())}

    if isinstance(raw, list):
        out2: Dict[str, Dict[str, Any]] = {}
        for item in raw:
            if not isinstance(item, dict):
                continue
            addr = str(item.get("address") or "").strip()
            if not addr:
                continue
            out2[addr] = {
                "balances": _clean_balances(item.get("balances") or {}),
                "nonce": int(item.get("nonce", 0) or 0),
            }
        return {k: out2[k] for k in sorted(out2.keys())}

    return {}


def import_bank_state(bank_mod: Any, bank_state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Restore accounts + nonces + balances. Then recompute supply from balances and set supply container.
    """
    lock, accounts, supply = _locate_bank_containers(bank_mod)

    reset_fn = getattr(bank_mod, "reset_state", None)
    if callable(reset_fn):
        reset_fn()
        lock, accounts, supply = _locate_bank_containers(bank_mod)

    get_or_create = getattr(bank_mod, "get_or_create_account", None)
    if not callable(get_or_create):
        raise ValueError("bank.get_or_create_account is required to import state")

    accounts_in = _parse_accounts_in(bank_state)

    def _apply() -> Dict[str, Any]:
        accounts.clear()
        supply.clear()

        applied = 0
        for addr in sorted(accounts_in.keys()):
            a = accounts_in[addr]
            bals = _clean_balances(a.get("balances") or {})
            nonce = int(a.get("nonce", 0) or 0)

            # keep snapshot minimal: skip totally empty accounts
            if (not bals) and nonce == 0:
                continue

            acc = get_or_create(addr)
            if getattr(acc, "balances", None) is None:
                acc.balances = {}
            acc.balances.clear()
            for denom, amt in bals.items():
                acc.balances[str(denom)] = str(_int0(amt))
            acc.nonce = int(nonce)

            accounts[addr] = acc
            applied += 1

        computed_supply = _compute_supply_from_accounts_dict(
            {addr: _account_view_from_obj(addr, accounts[addr]) for addr in sorted(accounts.keys())}
        )
        for denom, amt in computed_supply.items():
            supply[denom] = amt

        return {"applied_accounts": applied, "supply": dict(supply)}

    if lock:
        with lock:
            return _apply()
    return _apply()


# ───────────────────────────────────────────────
# Staking helpers
# ───────────────────────────────────────────────

def export_staking_state(staking_mod: Any) -> Dict[str, Any]:
    list_vals = getattr(staking_mod, "list_validators", None)
    list_delegs = getattr(staking_mod, "list_delegations", None)

    validators = list_vals() if callable(list_vals) else []
    delegations = list_delegs(None) if callable(list_delegs) else []

    if not isinstance(validators, list):
        validators = []
    if not isinstance(delegations, list):
        delegations = []

    # stable ordering
    validators = sorted(validators, key=lambda v: str((v or {}).get("address", "")))
    delegations = sorted(delegations, key=lambda d: (str((d or {}).get("delegator", "")), str((d or {}).get("validator", ""))))

    return {"validators": validators, "delegations": delegations}


def import_staking_state(staking_mod: Any, staking_state: Dict[str, Any]) -> Dict[str, Any]:
    reset_fn = getattr(staking_mod, "reset_state", None)
    if callable(reset_fn):
        reset_fn()

    apply_fn = getattr(staking_mod, "apply_state", None)
    if callable(apply_fn):
        return apply_fn(staking_state)

    lock = getattr(staking_mod, "_LOCK", None)
    vals = getattr(staking_mod, "_VALIDATORS", None)
    delegs = getattr(staking_mod, "_DELEGATIONS", None)
    rewards = getattr(staking_mod, "_REWARDS", None)

    ValidatorCls = getattr(staking_mod, "Validator", None)
    DelegationCls = getattr(staking_mod, "Delegation", None)
    RewardsCls = getattr(staking_mod, "Rewards", None)

    validators_in = (staking_state or {}).get("validators") or []
    delegations_in = (staking_state or {}).get("delegations") or []

    def _mk_validator(v: Dict[str, Any]) -> Any:
        if callable(ValidatorCls):
            return ValidatorCls(
                address=str(v.get("address") or ""),
                power=str(v.get("power") or "0"),
                commission=str(v.get("commission") or "0"),
            )
        return v

    def _mk_delegation(d: Dict[str, Any]) -> Any:
        if callable(DelegationCls):
            return DelegationCls(
                delegator=str(d.get("delegator") or ""),
                validator=str(d.get("validator") or ""),
                amount_tess=str(d.get("amount_tess") or "0"),
            )
        return d

    def _apply() -> Dict[str, Any]:
        applied_v = 0
        applied_d = 0

        if isinstance(vals, dict):
            vals.clear()
        if isinstance(delegs, dict):
            delegs.clear()
        if isinstance(rewards, dict):
            rewards.clear()

        if isinstance(vals, dict) and isinstance(validators_in, list):
            for v in validators_in:
                if not isinstance(v, dict):
                    continue
                addr = str(v.get("address") or "").strip()
                if not addr:
                    continue
                vals[addr] = _mk_validator(v)
                applied_v += 1

        if isinstance(delegs, dict) and isinstance(delegations_in, list):
            for d in delegations_in:
                if not isinstance(d, dict):
                    continue
                delegator = str(d.get("delegator") or "").strip()
                validator = str(d.get("validator") or "").strip()
                if not delegator or not validator:
                    continue
                delegs[(delegator, validator)] = _mk_delegation(d)
                applied_d += 1

        # optional rewards (safe stub)
        if isinstance(rewards, dict) and callable(RewardsCls):
            for (delegator, _validator), _d in (delegs or {}).items():
                if delegator not in rewards:
                    rewards[delegator] = RewardsCls(delegator=delegator, accrued_tess="0")

        inv = getattr(staking_mod, "assert_invariants", None)
        if callable(inv):
            inv()

        return {"applied_validators": applied_v, "applied_delegations": applied_d}

    if lock:
        with lock:
            return _apply()
    return _apply()


# ───────────────────────────────────────────────
# Composite snapshot
# ───────────────────────────────────────────────

def export_chain_state(*, cfg_mod: Any, bank_mod: Any, staking_mod: Any) -> Dict[str, Any]:
    state = {
        "config": cfg_mod.get_config() if hasattr(cfg_mod, "get_config") else {},
        "bank": export_bank_state(bank_mod),
        "staking": export_staking_state(staking_mod),
    }
    return {
        "ok": True,
        "created_at_ms": _now_ms(),
        "state": state,
        "state_root": compute_state_root(state),
    }


def import_chain_state(*, cfg_mod: Any, bank_mod: Any, staking_mod: Any, state: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(state, dict):
        raise ValueError("state must be an object")

    cfg_reset = getattr(cfg_mod, "reset_config", None)
    if callable(cfg_reset):
        cfg_reset()

    cfg_set = getattr(cfg_mod, "set_config", None)
    if callable(cfg_set):
        c = state.get("config") or {}
        cfg_set(chain_id=c.get("chain_id"), network_id=c.get("network_id"))

    # Import bank first, then staking (staking may create system accounts deterministically)
    import_bank_state(bank_mod, state.get("bank") or {})
    import_staking_state(staking_mod, state.get("staking") or {})

    return export_chain_state(cfg_mod=cfg_mod, bank_mod=bank_mod, staking_mod=staking_mod)