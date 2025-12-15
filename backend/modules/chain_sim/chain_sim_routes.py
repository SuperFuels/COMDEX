# backend/modules/chain_sim/chain_sim_routes.py
from __future__ import annotations

import hashlib
import json
from dataclasses import asdict
from typing import Any, Dict, Optional, Literal, List, Tuple
from pathlib import Path

from fastapi.responses import JSONResponse
from fastapi import APIRouter, HTTPException, Query, Body
from pydantic import BaseModel
from fastapi.encoders import jsonable_encoder
from backend.modules.chain_sim.tx_executor import apply_tx_receipt as apply_tx_executor
from backend.modules.chain_sim.chain_sim_merkle import (
    hash_leaf,
    merkle_root,
    merkle_proof,
    verify_proof,
)

from backend.modules.chain_sim import chain_sim_model as bank
from backend.modules.chain_sim import chain_sim_engine as engine
from backend.modules.chain_sim import chain_sim_config as cfg
from backend.modules.staking import staking_model as staking
from backend.modules.chain_sim.chain_sim_ledger import (
    record_applied_tx,
    reset_ledger,
    list_blocks,
    get_block,
    list_txs,
    get_tx,
)

router = APIRouter(prefix="/chain_sim", tags=["chain-sim-dev"])

class _AttrDict(dict):
    """dict that also supports attribute access (tx.tx_type)"""
    def __getattr__(self, k):
        try:
            return self[k]
        except KeyError as e:
            raise AttributeError(k) from e

    def __setattr__(self, k, v):
        self[k] = v

# ───────────────────────────────────────────────
# Helpers: stable json + hashing
# ───────────────────────────────────────────────

def _stable_json(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)

def _sha256_hex(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()

def _compute_state_root(state_obj: Dict[str, Any]) -> str:
    # Only hash the actual state payload (not "ok"/"state_root" wrapper)
    return _sha256_hex(_stable_json(state_obj))

# ───────────────────────────────────────────────
# Helpers: bank snapshot/import (avoid deadlocks)
# ───────────────────────────────────────────────

def _get_bank_lock():
    return getattr(bank, "_LOCK", None)

def _get_bank_accounts_dict() -> Dict[str, Any]:
    # expected in your codebase: _ACCOUNTS is dict[address] -> AccountState
    d = getattr(bank, "_ACCOUNTS", None)
    if isinstance(d, dict):
        return d
    # fallback patterns
    d = getattr(bank, "ACCOUNTS", None)
    if isinstance(d, dict):
        return d
    d = getattr(bank, "accounts", None)
    if isinstance(d, dict):
        return d
    return {}

def _get_bank_supply_dict() -> Dict[str, Any]:
    d = getattr(bank, "_SUPPLY", None)
    if isinstance(d, dict):
        return d
    d = getattr(bank, "SUPPLY", None)
    if isinstance(d, dict):
        return d
    d = getattr(bank, "supply", None)
    if isinstance(d, dict):
        return d
    return {}

def _bank_export() -> Dict[str, Any]:
    lock = _get_bank_lock()
    accounts = _get_bank_accounts_dict()

    def _export() -> Dict[str, Any]:
        acc_view: Dict[str, Any] = {}
        totals: Dict[str, int] = {}

        for addr, acc in accounts.items():
            a = getattr(acc, "address", addr) or addr
            bals = getattr(acc, "balances", None) or {}
            nonce = int(getattr(acc, "nonce", 0))

            bals_out: Dict[str, str] = {}
            for k, v in dict(bals).items():
                dk = str(k)
                sv = str(v)
                bals_out[dk] = sv
                s = sv.strip()
                if s.isdigit():
                    totals[dk] = totals.get(dk, 0) + int(s)

            acc_view[str(a)] = {"balances": bals_out, "nonce": nonce}

        sup_view = {k: str(v) for k, v in sorted(totals.items(), key=lambda kv: kv[0])}
        return {"accounts": acc_view, "supply": sup_view}

    if lock is not None:
        with lock:
            return _export()
    return _export()

def _bank_import(bank_state: Dict[str, Any]) -> None:
    # Clear + set accounts/balances/nonces; recompute supply from balances to ensure consistency.
    if hasattr(bank, "reset_state") and callable(getattr(bank, "reset_state")):
        bank.reset_state()
    else:
        # hard fail: you already rely on reset_state for /dev/reset
        raise ValueError("bank.reset_state() missing")

    accounts_in = (bank_state or {}).get("accounts") or {}
    if not isinstance(accounts_in, dict):
        raise ValueError("state.bank.accounts must be an object")

    # Populate accounts
    for addr, rec in accounts_in.items():
        if not isinstance(rec, dict):
            continue
        acc = bank.get_or_create_account(str(addr))
        bals = rec.get("balances") or {}
        if acc.balances is None:
            acc.balances = {}
        # overwrite balances
        acc.balances.clear()
        if isinstance(bals, dict):
            for denom, amt in bals.items():
                acc.balances[str(denom)] = str(amt)
        acc.nonce = int(rec.get("nonce", 0))

    # Recompute supply = sum(all account balances) by denom
    totals: Dict[str, int] = {}
    for addr, rec in accounts_in.items():
        if not isinstance(rec, dict):
            continue
        bals = rec.get("balances") or {}
        if not isinstance(bals, dict):
            continue
        for denom, amt in bals.items():
            s = str(amt).strip()
            n = int(s) if s.isdigit() else 0
            totals[str(denom)] = totals.get(str(denom), 0) + n

    # Write supply container
    lock = _get_bank_lock()
    supply = _get_bank_supply_dict()
    if lock is not None:
        with lock:
            supply.clear()
            for denom, n in totals.items():
                supply[str(denom)] = str(int(n))
    else:
        supply.clear()
        for denom, n in totals.items():
            supply[str(denom)] = str(int(n))

    # Bank invariants (if present)
    fn = getattr(bank, "assert_invariants", None)
    if callable(fn):
        fn()


def _compute_staking_delegations_root_from_snapshot(state: Dict[str, Any]) -> str:
    """
    Deterministically compute delegations root:
      - sort by (delegator, validator)
      - leaf payload: {"delegator","validator","amount_tess"} (stable json)
    """
    st_view = (state or {}).get("staking") or {}
    dels = st_view.get("delegations") or []
    if not isinstance(dels, list):
        dels = []

    def _key(d: Any) -> Tuple[str, str]:
        dd = d or {}
        return (str(dd.get("delegator") or ""), str(dd.get("validator") or ""))

    leaves: List[bytes] = []
    for d in sorted(dels, key=_key):
        if not isinstance(d, dict):
            continue
        payload_obj = {
            "delegator": str(d.get("delegator") or ""),
            "validator": str(d.get("validator") or ""),
            "amount_tess": str(d.get("amount_tess") or "0"),
        }
        if not payload_obj["delegator"] or not payload_obj["validator"]:
            continue
        leaves.append(hash_leaf(_stable_json(payload_obj).encode("utf-8")))

    return merkle_root(leaves).hex()

def _compute_staking_validators_root_from_snapshot(state: Dict[str, Any]) -> str:
    """
    Deterministically compute validators root from state["staking"]["validators"].
    Order: sorted by validator address.
    Leaf payload: {"address","power","commission"}
    """
    st_view = (state or {}).get("staking") or {}
    vals = st_view.get("validators") or []
    if not isinstance(vals, list):
        vals = []

    by_addr: Dict[str, Dict[str, Any]] = {}
    for v in vals:
        if not isinstance(v, dict):
            continue
        addr = str(v.get("address") or "").strip()
        if not addr:
            continue
        by_addr[addr] = v

    addrs = sorted(by_addr.keys())
    leaves: List[bytes] = []
    for a in addrs:
        v = by_addr[a] or {}
        payload_obj = {
            "address": a,
            "power": str(v.get("power") or "0"),
            "commission": str(v.get("commission") or "0"),
        }
        leaves.append(hash_leaf(_stable_json(payload_obj).encode("utf-8")))

    return merkle_root(leaves).hex()


def _compute_staking_delegations_root_from_snapshot(state: Dict[str, Any]) -> str:
    """
    Deterministically compute delegations root from state["staking"]["delegations"].
    Order: sorted by (delegator, validator).
    Leaf payload: {"delegator","validator","amount_tess"}
    """
    st_view = (state or {}).get("staking") or {}
    dels = st_view.get("delegations") or []
    if not isinstance(dels, list):
        dels = []

    items: List[Tuple[str, str, Dict[str, Any]]] = []
    for d in dels:
        if not isinstance(d, dict):
            continue
        delegator = str(d.get("delegator") or "").strip()
        validator = str(d.get("validator") or "").strip()
        if not delegator or not validator:
            continue
        items.append((delegator, validator, d))

    items.sort(key=lambda x: (x[0], x[1]))

    leaves: List[bytes] = []
    for delegator, validator, d in items:
        payload_obj = {
            "delegator": delegator,
            "validator": validator,
            "amount_tess": str(d.get("amount_tess") or "0"),
        }
        leaves.append(hash_leaf(_stable_json(payload_obj).encode("utf-8")))

    return merkle_root(leaves).hex()

def _compute_bank_accounts_root_from_snapshot(state: Dict[str, Any]) -> str:
    """
    Deterministically compute the same root as /dev/proof/account:
      - addresses sorted
      - leaf payload: {address, balances, nonce}
      - leaf bytes: hash_leaf(stable_json(payload).utf-8)
    """
    bank_view = (state or {}).get("bank") or {}
    accounts: Dict[str, Any] = bank_view.get("accounts") or {}
    if not isinstance(accounts, dict):
        accounts = {}

    addrs = sorted(accounts.keys())
    leaves: List[bytes] = []
    for a in addrs:
        r = accounts.get(a) or {}
        payload_obj = {
            "address": a,
            "balances": (r.get("balances") or {}) if isinstance(r.get("balances") or {}, dict) else {},
            "nonce": int(r.get("nonce") or 0),
        }
        leaves.append(hash_leaf(_stable_json(payload_obj).encode("utf-8")))

    # canonical: empty tree => root of empty list (your merkle_root should define this deterministically)
    return merkle_root(leaves).hex()

# ───────────────────────────────────────────────
# Helpers: staking snapshot/import
# ───────────────────────────────────────────────

def _get_staking_lock():
    return getattr(staking, "_LOCK", None)

def _staking_export() -> Dict[str, Any]:
    lock = _get_staking_lock()
    vals = getattr(staking, "_VALIDATORS", {}) or {}
    dels = getattr(staking, "_DELEGATIONS", {}) or {}
    rwd = getattr(staking, "_REWARDS", {}) or {}

    def _to_dict(x: Any) -> Dict[str, Any]:
        try:
            return asdict(x)
        except Exception:
            return dict(x) if isinstance(x, dict) else {}

    if lock is not None:
        with lock:
            validators = [_to_dict(v) for v in vals.values()]
            delegations = [_to_dict(d) for d in dels.values()]
            rewards = [_to_dict(rr) for rr in rwd.values()]
            return {"validators": validators, "delegations": delegations, "rewards": rewards}

    validators = [_to_dict(v) for v in vals.values()]
    delegations = [_to_dict(d) for d in dels.values()]
    rewards = [_to_dict(rr) for rr in rwd.values()]
    return {"validators": validators, "delegations": delegations, "rewards": rewards}

def _staking_import(st_state: Dict[str, Any]) -> None:
    if hasattr(staking, "reset_state") and callable(getattr(staking, "reset_state")):
        staking.reset_state()
    else:
        # If reset_state ever goes missing, at least clear containers
        lock = _get_staking_lock()
        if lock is not None:
            with lock:
                getattr(staking, "_VALIDATORS", {}).clear()
                getattr(staking, "_DELEGATIONS", {}).clear()
                getattr(staking, "_REWARDS", {}).clear()

    ValidatorCls = getattr(staking, "Validator", None)
    DelegationCls = getattr(staking, "Delegation", None)
    RewardsCls = getattr(staking, "Rewards", None)

    validators_in = (st_state or {}).get("validators") or []
    delegations_in = (st_state or {}).get("delegations") or []
    rewards_in = (st_state or {}).get("rewards") or []

    if not isinstance(validators_in, list) or not isinstance(delegations_in, list) or not isinstance(rewards_in, list):
        raise ValueError("state.staking validators/delegations/rewards must be lists")

    lock = _get_staking_lock()
    vals = getattr(staking, "_VALIDATORS", None)
    dels = getattr(staking, "_DELEGATIONS", None)
    rwd = getattr(staking, "_REWARDS", None)

    if not isinstance(vals, dict) or not isinstance(dels, dict) or not isinstance(rwd, dict):
        raise ValueError("staking in-memory containers not found")

    def _mk_validator(d: Dict[str, Any]):
        if callable(ValidatorCls):
            return ValidatorCls(
                address=str(d.get("address", "")),
                power=str(d.get("power", "0")),
                commission=str(d.get("commission", "0")),
            )
        return d

    def _mk_delegation(d: Dict[str, Any]):
        if callable(DelegationCls):
            return DelegationCls(
                delegator=str(d.get("delegator", "")),
                validator=str(d.get("validator", "")),
                amount_tess=str(d.get("amount_tess", "0")),
            )
        return d

    def _mk_rewards(d: Dict[str, Any]):
        if callable(RewardsCls):
            return RewardsCls(
                delegator=str(d.get("delegator", "")),
                accrued_tess=str(d.get("accrued_tess", "0")),
            )
        return d

    def _apply():
        vals.clear()
        dels.clear()
        rwd.clear()

        for v in validators_in:
            if not isinstance(v, dict):
                continue
            addr = str(v.get("address", "")).strip()
            if not addr:
                continue
            vals[addr] = _mk_validator(v)

        for d in delegations_in:
            if not isinstance(d, dict):
                continue
            delegator = str(d.get("delegator", "")).strip()
            validator = str(d.get("validator", "")).strip()
            if not delegator or not validator:
                continue
            key: Tuple[str, str] = (delegator, validator)
            dels[key] = _mk_delegation(d)

        for rr in rewards_in:
            if not isinstance(rr, dict):
                continue
            delegator = str(rr.get("delegator", "")).strip()
            if not delegator:
                continue
            rwd[delegator] = _mk_rewards(rr)

    if lock is not None:
        with lock:
            _apply()
    else:
        _apply()

    # staking invariants (if present)
    fn = getattr(staking, "assert_invariants", None)
    if callable(fn):
        fn()

# ───────────────────────────────────────────────
# Helpers: unified ChainState snapshot (single source of truth)
# ───────────────────────────────────────────────

def _get_chain_state_snapshot() -> Dict[str, Any]:
    """
    Prefer engine snapshot helper if present (keeps /dev/state aligned with any other callers).
    Fallback to local export (bank/staking/config) to avoid import cycles/hangs.

    NOTE:
      - This helper is the single source of truth for committing sub-roots
        (bank + staking) into the returned snapshot.
      - Callers should NOT re-call _commit_subroots_into_state unless they
        intentionally want redundancy (it is idempotent either way).
    """
    fn = getattr(engine, "get_chain_state_snapshot", None)
    if callable(fn):
        out = fn()
        if isinstance(out, dict) and "config" in out and "bank" in out and "staking" in out:
            _commit_subroots_into_state(out)
            return out

    state_obj: Dict[str, Any] = {
        "config": cfg.get_config(),
        "bank": _bank_export(),
        "staking": _staking_export(),
    }
    _commit_subroots_into_state(state_obj)
    return state_obj

def _commit_subroots_into_state(state_obj: Dict[str, Any]) -> None:
    """
    Mutates state_obj in-place to add committed sub-roots under state_root.
    Safe to call multiple times.
    """
    if not isinstance(state_obj, dict):
        return

    # bank root
    try:
        bank_root = _compute_bank_accounts_root_from_snapshot(state_obj)
        bank_view = state_obj.get("bank")
        if isinstance(bank_view, dict):
            bank_view["root"] = bank_root
    except Exception:
        pass

    # staking roots
    try:
        st_view = state_obj.get("staking")
        if isinstance(st_view, dict):
            st_view["validators_root"] = _compute_staking_validators_root_from_snapshot(state_obj)
            st_view["delegations_root"] = _compute_staking_delegations_root_from_snapshot(state_obj)
    except Exception:
        pass

# ───────────────────────────────────────────────
# Request models
# ───────────────────────────────────────────────

class DevMintRequest(BaseModel):
    denom: str
    to: str
    amount: str

class DevTransferRequest(BaseModel):
    denom: str
    from_addr: str
    to: str
    amount: str

class DevBurnRequest(BaseModel):
    denom: str
    from_addr: str
    amount: str

class DevSubmitTx(BaseModel):
    tx_id: Optional[str] = None
    from_addr: str
    nonce: int
    tx_type: Literal[
        "BANK_MINT",
        "BANK_SEND",
        "BANK_TRANSFER",  # alias (maps to BANK_SEND)
        "BANK_BURN",
        "STAKING_DELEGATE",
        "STAKING_UNDELEGATE",
    ]
    payload: Dict[str, Any]

class DevGenesisAlloc(BaseModel):
    address: str
    balances: Dict[str, str]

class DevGenesisValidator(BaseModel):
    address: str
    self_delegation_tess: str = "0"
    commission: str = "0"

class DevResetRequest(BaseModel):
    chain_id: Optional[str] = None
    network_id: Optional[str] = None
    allocs: Optional[List[DevGenesisAlloc]] = None
    validators: Optional[List[DevGenesisValidator]] = None

# ───────────────────────────────────────────────
# Genesis / reset (P1_6 dev slice)
# ───────────────────────────────────────────────

@router.get("/dev/perf_latest")
async def chain_sim_dev_perf_latest() -> Dict[str, Any]:
    """
    Returns latest perf artifact emitted by pytest:
      backend/tests/artifacts/chain_sim_perf_latest.json
    """
    root = Path(__file__).resolve().parents[3]  # /workspaces/COMDEX/backend
    p1 = root / "tests" / "artifacts" / "chain_sim_perf_latest.json"
    p2 = root / "tests" / "artifacts" / "glyphchain_perf_latest.json"

    p = p2 if p2.exists() else p1
    if not p.exists():
        return JSONResponse(content={"ok": False, "error": "perf artifact not found"}, status_code=404)

    try:
        data = json.loads(p.read_text())
    except Exception as e:
        return JSONResponse(content={"ok": False, "error": f"failed to read perf artifact: {e}"}, status_code=500)

    data["ok"] = True
    return JSONResponse(content=data)

@router.post("/dev/reset")
async def chain_sim_dev_reset(body: Optional[DevResetRequest] = None) -> Dict[str, Any]:
    reset_ledger()

    # 1) reset staking
    try:
        staking.reset_state()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"staking reset failed: {e}")

    # 2) reset bank
    if not (hasattr(bank, "reset_state") and callable(getattr(bank, "reset_state"))):
        raise HTTPException(status_code=500, detail="bank.reset_state() is missing")
    try:
        bank.reset_state()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"bank reset failed: {e}")

    # 3) reset config + apply optional overrides
    cfg.reset_config()
    if body:
        cfg.set_config(chain_id=body.chain_id, network_id=body.network_id)

    applied_allocs = 0
    applied_validators = 0

    # 4) Apply allocs by setting state directly (genesis seeding)
    if body and body.allocs:
        if hasattr(bank, "apply_genesis_allocs") and callable(getattr(bank, "apply_genesis_allocs")):
            allocs = [a.model_dump() for a in body.allocs]
            try:
                bank.apply_genesis_allocs(allocs)
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"bank genesis allocs failed: {e}")
            applied_allocs = len(body.allocs)
        else:
            # Fallback for older bank module: do mint loop (kept for compatibility)
            for a in body.allocs:
                addr = a.address
                if not addr:
                    continue
                for denom, amount in (a.balances or {}).items():
                    if amount is None:
                        continue
                    amt_s = str(amount).strip()
                    if amt_s in ("", "0", "0.0"):
                        continue
                    bank.mint(
                        denom=str(denom),
                        signer=engine.DEV_MINT_AUTHORITY,
                        to_addr=str(addr),
                        amount=amt_s,
                    )
                applied_allocs += 1
    else:
        # Still ensure deterministic defaults exist in supply (PHO/TESS keys)
        if hasattr(bank, "recompute_supply") and callable(getattr(bank, "recompute_supply")):
            try:
                bank.recompute_supply()
            except Exception:
                pass

    # 5) Apply validators (staking genesis)
    if body and body.validators:
        vdicts = [v.model_dump() for v in body.validators]
        staking.apply_genesis_validators(vdicts)
        applied_validators = len(body.validators)

    return JSONResponse(
        content=jsonable_encoder(
            {
                "ok": True,
                "config": cfg.get_config(),
                "applied_allocs": applied_allocs,
                "applied_validators": applied_validators,
                "supply": bank.get_supply_view(),
                "validators": staking.list_validators(),
                "blocks": [],
            }
        )
    )

@router.get("/dev/config")
async def chain_sim_dev_config() -> Dict[str, Any]:
    return {"ok": True, "config": cfg.get_config()}

# ───────────────────────────────────────────────
# P1_2 dev slice: ChainState snapshot + state_root
# ───────────────────────────────────────────────


@router.post("/dev/state")
async def chain_sim_dev_state_apply(body: Dict[str, Any] = Body(...)) -> Dict[str, Any]:
    """
    POST /api/chain_sim/dev/state
      - accepts either {"state": {...}} or direct {...}
      - resets ledger + imports config/bank/staking
      - returns fresh snapshot + recomputed state_root

    NOTE: _get_chain_state_snapshot() already commits bank/staking sub-roots
    (bank.root, staking.validators_root, staking.delegations_root).
    """
    incoming = body.get("state") if isinstance(body, dict) else None
    if not isinstance(incoming, dict):
        incoming = body
    if not isinstance(incoming, dict):
        raise HTTPException(status_code=400, detail="body must be an object")

    reset_ledger()

    try:
        # config
        cfg.reset_config()
        cfg_in = incoming.get("config") or {}
        if isinstance(cfg_in, dict):
            cfg.set_config(chain_id=cfg_in.get("chain_id"), network_id=cfg_in.get("network_id"))

        # staking + bank
        _staking_import(incoming.get("staking") or {})
        _bank_import(incoming.get("bank") or {})

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"state import failed: {e}")

    state_obj = _get_chain_state_snapshot()  # roots already committed here
    root = _compute_state_root(state_obj)
    return JSONResponse(content=jsonable_encoder({"ok": True, "state": state_obj, "state_root": root}))

@router.get("/dev/state")
async def chain_sim_dev_state() -> Dict[str, Any]:
    """
    GET /api/chain_sim/dev/state
      - returns: { ok, state, state_root }
      - state = { config, bank, staking }

    NOTE: _get_chain_state_snapshot() already commits bank/staking sub-roots.
    """
    state_obj = _get_chain_state_snapshot()
    root = _compute_state_root(state_obj)
    return JSONResponse(content=jsonable_encoder({"ok": True, "state": state_obj, "state_root": root}))

@router.get("/dev/proof/tx")
async def chain_sim_dev_proof_tx(tx_id: str = Query(...)) -> Dict[str, Any]:
    """
    Merkle proof that tx_hash is included in block.txs_root.
    Uses the SAME merkle functions as chain_sim_merkle.py.
    """
    tx = get_tx(tx_id)
    if not tx:
        raise HTTPException(status_code=404, detail="tx not found")

    h = int(tx.get("block_height") or 0)
    if h <= 0:
        raise HTTPException(status_code=400, detail="tx has no block_height")

    blk = get_block(h)
    if not blk:
        raise HTTPException(status_code=404, detail="block not found")

    txs = blk.get("txs") or []
    if not isinstance(txs, list) or not txs:
        raise HTTPException(status_code=400, detail="block has no txs")

    # Build leaves from tx hashes in block order
    leaves: List[bytes] = []
    hashes: List[str] = []
    for t in txs:
        th = str((t or {}).get("tx_hash") or "")
        if not th:
            continue
        hashes.append(th)
        try:
            raw = bytes.fromhex(th)
        except Exception:
            raw = th.encode("utf-8")
        leaves.append(hash_leaf(raw))

    if not hashes:
        raise HTTPException(status_code=400, detail="block txs missing tx_hash")

    # Find index of this tx hash
    target_hash = str(tx.get("tx_hash") or "")
    try:
        idx = hashes.index(target_hash)
    except ValueError:
        raise HTTPException(status_code=400, detail="tx_hash not found in block tx list")

    root_b = merkle_root(leaves)
    proof = merkle_proof(leaves, idx)

    return {
        "ok": True,
        "algo": "sha256-merkle-v1",
        "block_height": h,
        "tx_id": tx_id,
        "tx_hash": target_hash,
        "leaf_index": idx,
        "txs_root": root_b.hex(),
        "proof": proof,
        "total_leaves": len(leaves),
    }

@router.post("/dev/proof/verify_tx")
async def chain_sim_dev_verify_tx_proof(body: Dict[str, Any] = Body(...)) -> Dict[str, Any]:
    """
    Verifies { tx_hash, txs_root, proof }.

    Body example:
      {"tx_hash":"<hex>", "txs_root":"<hex>", "proof":[...]}
    """
    try:
        tx_hash = str(body.get("tx_hash") or "").strip()
        txs_root = str(body.get("txs_root") or "").strip()
        proof = body.get("proof") or []

        if not tx_hash or not txs_root or not isinstance(proof, list):
            raise ValueError("invalid body")

        # Match /dev/proof/tx leaf construction: hash_leaf(raw(tx_hash))
        try:
            raw = bytes.fromhex(tx_hash)
        except Exception:
            raw = tx_hash.encode("utf-8")

        leaf_b = hash_leaf(raw)
        root_b = bytes.fromhex(txs_root)

        ok = verify_proof(leaf_b, proof, root_b)
        return {"ok": True, "verified": bool(ok)}

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"verify failed: {e}")


@router.post("/dev/proof/verify_account")
async def chain_sim_dev_verify_account_proof(body: Dict[str, Any] = Body(...)) -> Dict[str, Any]:
    """
    Verifies { bank_accounts_root, proof, leaf_hash } OR { bank_accounts_root, proof, account }.

    Body examples:
      {"bank_accounts_root":"...", "proof":[...], "leaf_hash":"..."}
      {"bank_accounts_root":"...", "proof":[...], "account":{"address":"...","balances":{...},"nonce":0}}
    """
    try:
        root_hex = str(body.get("bank_accounts_root") or "")
        proof = body.get("proof") or []
        if not root_hex or not isinstance(proof, list):
            raise ValueError("invalid body")

        leaf_hex = str(body.get("leaf_hash") or "")
        if leaf_hex:
            leaf_b = bytes.fromhex(leaf_hex)
        else:
            acct = body.get("account") or {}
            if not isinstance(acct, dict):
                raise ValueError("invalid account")
            payload_obj = {
                "address": str(acct.get("address") or ""),
                "balances": (acct.get("balances") or {}) if isinstance(acct.get("balances") or {}, dict) else {},
                "nonce": int(acct.get("nonce") or 0),
            }
            if not payload_obj["address"]:
                raise ValueError("account.address required")
            leaf_b = hash_leaf(_stable_json(payload_obj).encode("utf-8"))

        root_b = bytes.fromhex(root_hex)
        ok = verify_proof(leaf_b, proof, root_b)
        return {"ok": True, "verified": bool(ok)}

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"verify failed: {e}")

@router.get("/dev/proof/account")
async def chain_sim_dev_proof_account(address: str = Query(...)) -> Dict[str, Any]:
    """
    Returns a Merkle proof for the exported bank account record, against a bank_accounts_root.
    Root is computed from the SAME exported view as /dev/state to keep it deterministic.
    """
    bank_view = _get_chain_state_snapshot().get("bank") or {}
    accounts: Dict[str, Any] = bank_view.get("accounts") or {}

    rec = accounts.get(address)
    if rec is None:
        raise HTTPException(status_code=404, detail="account not found in exported bank view")

    addrs = sorted(accounts.keys())
    addr_to_idx = {a: i for i, a in enumerate(addrs)}

    leaves = []
    for a in addrs:
        r = accounts[a] or {}
        payload_obj = {
            "address": a,
            "balances": r.get("balances") or {},
            "nonce": int(r.get("nonce") or 0),
        }
        leaves.append(hash_leaf(_stable_json(payload_obj).encode("utf-8")))

    root_b = merkle_root(leaves)
    idx = addr_to_idx[address]
    proof = merkle_proof(leaves, idx)

    leaf_obj = {
        "address": address,
        "balances": rec.get("balances") or {},
        "nonce": int(rec.get("nonce") or 0),
    }
    leaf_h = hash_leaf(_stable_json(leaf_obj).encode("utf-8")).hex()

    return {
        "ok": True,
        "algo": "sha256-merkle-v1",
        "bank_accounts_root": root_b.hex(),
        "leaf_index": idx,
        "leaf_hash": leaf_h,
        "account": leaf_obj,
        "proof": proof,
        "total_leaves": len(leaves),
    }

# ───────────────────────────────────────────────
# Canonical entrypoint: submit_tx (P1_3)
# ───────────────────────────────────────────────

@router.post("/dev/submit_tx")
async def chain_sim_submit_tx(body: DevSubmitTx) -> Dict[str, Any]:
    # normalize aliases
    tx_type = body.tx_type
    if tx_type == "BANK_TRANSFER":
        tx_type = "BANK_SEND"

    tx = body.model_dump()
    tx["tx_type"] = tx_type

    # IMPORTANT: tx_executor expects attribute-style access (tx.tx_type)
    tx_obj = _AttrDict(tx)

    # 1) Canonical path: execute via tx_executor
    try:
        receipt = apply_tx_executor(tx_obj)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"apply_tx failed: {e}")

    # normalize receipt shape (defensive)
    if not isinstance(receipt, dict):
        receipt = {"ok": True, "result": receipt}

    result = receipt.get("result") or {}

    # infer "applied" defensively (but prefer explicit)
    applied = receipt.get("applied", None)
    if applied is None:
        if isinstance(result, (list, tuple)) and len(result) > 0 and isinstance(result[0], bool):
            applied = bool(result[0])
        elif isinstance(result, dict) and "ok" in result:
            applied = bool(result.get("ok"))
        else:
            applied = True
    else:
        applied = bool(applied)

    # ✅ Hard rule: failed tx must not advance chain (no ledger record, no ids/heights)
    if not applied:
        receipt["applied"] = False
        for k in ("tx_id", "tx_hash", "block_height", "tx_index", "state_root"):
            receipt.pop(k, None)
        return JSONResponse(content=jsonable_encoder(receipt))

    # 2) After apply, recompute state_root from SAME snapshot as /dev/state
    state_obj = _get_chain_state_snapshot()  # roots already committed here
    state_root = _compute_state_root(state_obj)

    receipt["state_root"] = state_root
    receipt["applied"] = True

    # pull fee from executor result (if present)
    fee = None
    if isinstance(result, dict):
        maybe_fee = result.get("fee")
        fee = maybe_fee if isinstance(maybe_fee, dict) else None

    # 3) Record tx + persist header commitments into the block
    try:
        rec = record_applied_tx(
            from_addr=body.from_addr,
            nonce=body.nonce,
            tx_type=tx_type,
            payload=body.payload,
            applied=True,
            result=result,
            fee=fee,  # ✅ ensures ledger columns populate
            block_header={"state_root": state_root},
        )
        receipt["tx_id"] = rec.tx_id
        receipt["tx_hash"] = rec.tx_hash
        receipt["block_height"] = rec.block_height
        receipt["tx_index"] = rec.tx_index
    except Exception as e:
        receipt["ledger_record_error"] = str(e)

    return JSONResponse(content=jsonable_encoder(receipt))
# ───────────────────────────────────────────────
# Explorer / ledger endpoints
# ───────────────────────────────────────────────

@router.get("/dev/blocks")
async def chain_sim_dev_blocks(
    limit: int = Query(20, ge=1, le=500),
    offset: int = Query(0, ge=0),
) -> Dict[str, Any]:
    return {"ok": True, "blocks": list_blocks(limit=limit, offset=offset)}

@router.get("/dev/block/{height}")
async def chain_sim_dev_block(height: int) -> Dict[str, Any]:
    blk = get_block(height)
    if not blk:
        raise HTTPException(status_code=404, detail="block not found")
    return {"ok": True, "block": blk}

@router.get("/dev/tx/{tx_id}")
async def chain_sim_dev_tx(tx_id: str) -> Dict[str, Any]:
    tx = get_tx(tx_id)
    if not tx:
        raise HTTPException(status_code=404, detail="tx not found")
    return {"ok": True, "tx": tx}

@router.get("/dev/txs")
async def chain_sim_dev_txs(
    address: Optional[str] = Query(None, description="Optional address filter (from_addr or payload.to)"),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
) -> Dict[str, Any]:
    return {"ok": True, "txs": list_txs(address=address, limit=limit, offset=offset)}

@router.get("/dev/tx")
async def chain_sim_get_tx(tx_id: str = Query(...)) -> Dict[str, Any]:
    tx = get_tx(tx_id)
    if not tx:
        raise HTTPException(status_code=404, detail="tx not found")
    return {"ok": True, "tx": tx}

# ───────────────────────────────────────────────
# Back-compat wrappers
# ───────────────────────────────────────────────

@router.post("/dev/mint")
async def chain_sim_dev_mint(body: DevMintRequest) -> Dict[str, Any]:
    signer = engine.DEV_MINT_AUTHORITY
    nonce = bank.get_or_create_account(signer).nonce
    tx = {
        "from_addr": signer,
        "nonce": nonce,
        "tx_type": "BANK_MINT",
        "payload": {"denom": body.denom, "to": body.to, "amount": body.amount},
    }
    try:
        receipt = engine.submit_tx(tx)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"mint failed: {e}")
    return receipt.get("result") or {"ok": False}

@router.post("/dev/transfer")
async def chain_sim_dev_transfer(body: DevTransferRequest) -> Dict[str, Any]:
    nonce = bank.get_or_create_account(body.from_addr).nonce
    tx = {
        "from_addr": body.from_addr,
        "nonce": nonce,
        "tx_type": "BANK_SEND",
        "payload": {"denom": body.denom, "to": body.to, "amount": body.amount},
    }
    try:
        receipt = engine.submit_tx(tx)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"transfer failed: {e}")
    return receipt.get("result") or {"ok": False}

@router.post("/dev/burn")
async def chain_sim_dev_burn(body: DevBurnRequest) -> Dict[str, Any]:
    nonce = bank.get_or_create_account(body.from_addr).nonce
    tx = {
        "from_addr": body.from_addr,
        "nonce": nonce,
        "tx_type": "BANK_BURN",
        "payload": {"denom": body.denom, "amount": body.amount},
    }
    try:
        receipt = engine.submit_tx(tx)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"burn failed: {e}")
    return receipt.get("result") or {"ok": False}

# ───────────────────────────────────────────────
# Queries
# ───────────────────────────────────────────────

@router.get("/dev/account")
async def chain_sim_dev_get_account(address: str = Query(...)) -> Dict[str, Any]:
    return bank.get_account_view(address)

@router.get("/dev/supply")
async def chain_sim_dev_get_supply() -> Dict[str, str]:
    return bank.get_supply_view()