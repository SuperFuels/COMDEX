from __future__ import annotations

import json
from typing import Any, Dict, List, Tuple

from fastapi import APIRouter, Body, HTTPException, Query

from backend.modules.chain_sim.chain_sim_merkle import (
    hash_leaf,
    merkle_root,
    merkle_proof,
    verify_proof,
)
from backend.modules.staking import staking_model as staking

router = APIRouter(prefix="/staking", tags=["staking-dev"])


# ───────────────────────────────────────────────
# Helpers
# ───────────────────────────────────────────────

def _stable_json(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _get_staking_lock():
    return getattr(staking, "_LOCK", None)


def _validators_view() -> Dict[str, Any]:
    """
    Deterministic exported view: { address -> {address, power, commission} }
    """
    lock = _get_staking_lock()
    vals = getattr(staking, "_VALIDATORS", {}) or {}

    def _export() -> Dict[str, Any]:
        out: Dict[str, Any] = {}
        for addr, v in (vals or {}).items():
            a = str(getattr(v, "address", addr) or addr)
            out[a] = {
                "address": a,
                "power": str(getattr(v, "power", "0")),
                "commission": str(getattr(v, "commission", "0")),
            }
        return out

    if lock is not None:
        with lock:
            return _export()
    return _export()


def _delegations_view() -> Dict[Tuple[str, str], Any]:
    """
    Deterministic exported view: {(delegator, validator) -> {delegator, validator, amount_tess}}
    """
    lock = _get_staking_lock()
    dels = getattr(staking, "_DELEGATIONS", {}) or {}

    def _export() -> Dict[Tuple[str, str], Any]:
        out: Dict[Tuple[str, str], Any] = {}
        for k, d in (dels or {}).items():
            if isinstance(k, (tuple, list)) and len(k) == 2:
                delegator, validator = str(k[0]), str(k[1])
            else:
                delegator = str(getattr(d, "delegator", ""))
                validator = str(getattr(d, "validator", ""))
            out[(delegator, validator)] = {
                "delegator": delegator,
                "validator": validator,
                "amount_tess": str(getattr(d, "amount_tess", "0")),
            }
        return out

    if lock is not None:
        with lock:
            return _export()
    return _export()


def _compute_validators_root() -> str:
    vals = _validators_view()
    addrs = sorted(vals.keys())
    leaves: List[bytes] = []
    for a in addrs:
        v = vals.get(a) or {}
        payload = {
            "address": a,
            "power": str(v.get("power", "0")),
            "commission": str(v.get("commission", "0")),
        }
        leaves.append(hash_leaf(_stable_json(payload).encode("utf-8")))
    return merkle_root(leaves).hex()


def _compute_delegations_root() -> str:
    dels = _delegations_view()
    keys = sorted(dels.keys(), key=lambda kv: (kv[0], kv[1]))
    leaves: List[bytes] = []
    for delegator, validator in keys:
        d = dels.get((delegator, validator)) or {}
        payload = {
            "delegator": delegator,
            "validator": validator,
            "amount_tess": str(d.get("amount_tess", "0")),
        }
        leaves.append(hash_leaf(_stable_json(payload).encode("utf-8")))
    return merkle_root(leaves).hex()


# ───────────────────────────────────────────────
# Proof routes (staking)
# ───────────────────────────────────────────────

@router.get("/dev/proof/validator")
async def staking_dev_proof_validator(address: str = Query(...)) -> Dict[str, Any]:
    vals = _validators_view()
    rec = vals.get(address)
    if rec is None:
        raise HTTPException(status_code=404, detail="validator not found")

    addrs = sorted(vals.keys())
    idx = addrs.index(address)

    leaves: List[bytes] = []
    for a in addrs:
        v = vals.get(a) or {}
        payload = {
            "address": a,
            "power": str(v.get("power", "0")),
            "commission": str(v.get("commission", "0")),
        }
        leaves.append(hash_leaf(_stable_json(payload).encode("utf-8")))

    root_b = merkle_root(leaves)
    proof = merkle_proof(leaves, idx)

    leaf_payload = {
        "address": address,
        "power": str(rec.get("power", "0")),
        "commission": str(rec.get("commission", "0")),
    }
    leaf_h = hash_leaf(_stable_json(leaf_payload).encode("utf-8")).hex()

    return {
        "ok": True,
        "algo": "sha256-merkle-v1",
        "validators_root": root_b.hex(),            # ✅ canonical
        "staking_validators_root": root_b.hex(),    # back-compat
        "leaf_index": idx,
        "leaf_hash": leaf_h,
        "validator": leaf_payload,
        "proof": proof,
        "total_leaves": len(leaves),
    }


@router.post("/dev/proof/verify_validator")
async def staking_dev_verify_validator(body: Dict[str, Any] = Body(...)) -> Dict[str, Any]:
    try:
        root_hex = str(body.get("validators_root") or body.get("staking_validators_root") or "")
        proof = body.get("proof") or []
        if not root_hex or not isinstance(proof, list):
            raise ValueError("invalid body")

        leaf_hex = str(body.get("leaf_hash") or "")
        if leaf_hex:
            leaf_b = bytes.fromhex(leaf_hex)
        else:
            v = body.get("validator") or {}
            if not isinstance(v, dict):
                raise ValueError("invalid validator")
            payload = {
                "address": str(v.get("address") or ""),
                "power": str(v.get("power", "0")),
                "commission": str(v.get("commission", "0")),
            }
            if not payload["address"]:
                raise ValueError("validator.address required")
            leaf_b = hash_leaf(_stable_json(payload).encode("utf-8"))

        root_b = bytes.fromhex(root_hex)
        ok = verify_proof(leaf_b, proof, root_b)
        return {"ok": True, "verified": bool(ok)}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"verify failed: {e}")


@router.get("/dev/proof/delegation")
async def staking_dev_proof_delegation(
    delegator: str = Query(...),
    validator: str = Query(...),
) -> Dict[str, Any]:
    dels = _delegations_view()
    key = (delegator, validator)
    rec = dels.get(key)
    if rec is None:
        raise HTTPException(status_code=404, detail="delegation not found")

    keys = sorted(dels.keys(), key=lambda kv: (kv[0], kv[1]))
    idx = keys.index(key)

    leaves: List[bytes] = []
    for d, v in keys:
        r = dels.get((d, v)) or {}
        payload = {
            "delegator": d,
            "validator": v,
            "amount_tess": str(r.get("amount_tess", "0")),
        }
        leaves.append(hash_leaf(_stable_json(payload).encode("utf-8")))

    root_b = merkle_root(leaves)
    proof = merkle_proof(leaves, idx)

    leaf_payload = {
        "delegator": delegator,
        "validator": validator,
        "amount_tess": str(rec.get("amount_tess", "0")),
    }
    leaf_h = hash_leaf(_stable_json(leaf_payload).encode("utf-8")).hex()

    return {
        "ok": True,
        "algo": "sha256-merkle-v1",
        "delegations_root": root_b.hex(),           # ✅ canonical
        "staking_delegations_root": root_b.hex(),   # back-compat
        "leaf_index": idx,
        "leaf_hash": leaf_h,
        "delegation": leaf_payload,
        "proof": proof,
        "total_leaves": len(leaves),
    }


@router.post("/dev/proof/verify_delegation")
async def staking_dev_verify_delegation(body: Dict[str, Any] = Body(...)) -> Dict[str, Any]:
    try:
        root_hex = str(body.get("delegations_root") or body.get("staking_delegations_root") or "")
        proof = body.get("proof") or []
        if not root_hex or not isinstance(proof, list):
            raise ValueError("invalid body")

        leaf_hex = str(body.get("leaf_hash") or "")
        if leaf_hex:
            leaf_b = bytes.fromhex(leaf_hex)
        else:
            d = body.get("delegation") or {}
            if not isinstance(d, dict):
                raise ValueError("invalid delegation")
            payload = {
                "delegator": str(d.get("delegator") or ""),
                "validator": str(d.get("validator") or ""),
                "amount_tess": str(d.get("amount_tess", "0")),
            }
            if not payload["delegator"] or not payload["validator"]:
                raise ValueError("delegation.delegator and delegation.validator required")
            leaf_b = hash_leaf(_stable_json(payload).encode("utf-8"))

        root_b = bytes.fromhex(root_hex)
        ok = verify_proof(leaf_b, proof, root_b)
        return {"ok": True, "verified": bool(ok)}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"verify failed: {e}")