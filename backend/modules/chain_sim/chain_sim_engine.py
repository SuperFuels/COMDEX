# backend/modules/chain_sim/chain_sim_engine.py

from __future__ import annotations

import hashlib
import json
import time
import uuid
from typing import Any, Dict, Optional

from backend.modules.chain_sim import chain_sim_model as bank
from backend.modules.chain_sim.chain_sim_ledger import (
    get_tx as ledger_get_tx,
    list_txs as ledger_list_txs,
)
from backend.modules.staking import staking_model as staking

DEV_MINT_AUTHORITY = "pho1-dev-gma-authority"

# ───────────────────────────────────────────────
# Dev fees (P1_4: small but real progress)
# ───────────────────────────────────────────────

FEE_DENOM = "PHO"
FEE_PER_TX = "1"  # string int
FEE_COLLECTOR = "pho1-dev-fee-collector"

# Legacy in-process log (kept for back-compat / debugging)
_TX_LOG: Dict[str, Dict[str, Any]] = {}


def _now_ms() -> int:
    return int(time.time() * 1000)


def _canonical_bytes(obj: Any) -> bytes:
    return json.dumps(
        obj,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


def _sha256_hex(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def _new_client_tx_id() -> str:
    return f"TX_{uuid.uuid4().hex[:16]}"


def _as_int_amount(x: Any, field: str = "amount") -> int:
    """Accept int or numeric string. Raises ValueError on bad inputs."""
    if isinstance(x, int):
        return x
    if isinstance(x, str):
        s = x.strip()
        if s.isdigit():
            return int(s)
    raise ValueError(f"{field} must be an int-like string (e.g. '10')")


def _int_to_amount_str(n: int) -> str:
    if n < 0:
        raise ValueError("amount cannot be negative")
    return str(int(n))


def _fee_int() -> int:
    return _as_int_amount(FEE_PER_TX, "FEE_PER_TX")


def _maybe_assert_invariants() -> None:
    """
    Central invariant hook. If chain_sim_model.assert_invariants exists, call it.
    """
    fn = getattr(bank, "assert_invariants", None)
    if callable(fn):
        fn()


def _force_signer_nonce_once(from_addr: str, expected_next: int) -> None:
    """
    Dev semantics: a tx should consume exactly ONE nonce.
    If internal ops increment nonce multiple times, clamp to (tx_nonce + 1).
    """
    try:
        acc = bank.get_or_create_account(from_addr)
        setattr(acc, "nonce", int(expected_next))
    except Exception:
        return


def get_tx(tx_id: str) -> Optional[Dict[str, Any]]:
    """Prefer ledger-backed txs; fallback to legacy _TX_LOG."""
    tx = ledger_get_tx(tx_id)
    if tx:
        return tx
    return _TX_LOG.get(tx_id)


def list_txs_for_address(address: str, limit: int = 50) -> Dict[str, Any]:
    """Back-compat wrapper (old shape: {'txs': [...]})"""
    return {"txs": ledger_list_txs(address=address, limit=limit, offset=0)}


def submit_tx(tx: Dict[str, Any]) -> Dict[str, Any]:
    """
    Canonical dev tx executor.
    IMPORTANT: ledger recording is handled by chain_sim_routes.py (single source of truth).

    Fee rules (dev):
      - Fee denom is PHO.
      - BANK_SEND / BANK_BURN: fee transferred from signer → fee_collector (PHO)
      - BANK_MINT: if denom == PHO, carve-out:
          mint (amount - fee) to recipient, mint fee to fee_collector
        else: no fee (avoid minting PHO out of thin air)

    Staking (dev skeleton):
      - STAKING_DELEGATE / STAKING_UNDELEGATE (no consensus hooks yet)
      - fees disabled for staking txs (fee.enabled = false)
    """
    client_tx_id = tx.get("tx_id") or _new_client_tx_id()
    from_addr = tx.get("from_addr")
    nonce = tx.get("nonce")
    tx_type = tx.get("tx_type")
    payload = tx.get("payload") or {}

    if not isinstance(from_addr, str) or not from_addr:
        raise ValueError("from_addr required")
    if not isinstance(nonce, int) or nonce < 0:
        raise ValueError("nonce must be int >= 0")
    if tx_type not in (
        "BANK_MINT",
        "BANK_SEND",
        "BANK_BURN",
        "STAKING_DELEGATE",
        "STAKING_UNDELEGATE",
    ):
        raise ValueError("invalid tx_type")

    signer_acc = bank.get_or_create_account(from_addr)
    if nonce != int(getattr(signer_acc, "nonce", 0)):
        raise ValueError(f"bad nonce: expected {signer_acc.nonce}, got {nonce}")

    signing_obj = {
        "from_addr": from_addr,
        "nonce": nonce,
        "tx_type": tx_type,
        "payload": payload,
    }
    tx_hash = _sha256_hex(_canonical_bytes(signing_obj))

    applied = False
    result: Dict[str, Any] = {}

    fee_n = _fee_int()
    fee_info: Dict[str, Any] = {
        "enabled": bool(tx_type and str(tx_type).startswith("BANK_")),
        "fee_denom": FEE_DENOM,
        "fee_amount": FEE_PER_TX,
        "applied": False,
        "collector": FEE_COLLECTOR,
    }

    accounts_touched = [from_addr]

    # ───────────────────────────────────────────────
    # Apply tx + fee (BANK_*)
    # ───────────────────────────────────────────────
    if tx_type == "BANK_MINT":
        denom = payload.get("denom")
        to_addr = payload.get("to")
        amount_raw = payload.get("amount")

        if from_addr != DEV_MINT_AUTHORITY:
            raise ValueError("mint requires dev authority signer")
        if not isinstance(to_addr, str) or not to_addr:
            raise ValueError("payload.to required")

        accounts_touched.append(to_addr)

        if denom == FEE_DENOM and fee_n > 0:
            amt = _as_int_amount(amount_raw, "payload.amount")
            if amt < fee_n:
                raise ValueError(f"mint amount must be >= fee ({fee_n})")
            net_amt = amt - fee_n

            main_res = bank.mint(
                denom=denom,
                signer=from_addr,
                to_addr=to_addr,
                amount=_int_to_amount_str(net_amt),
            )
            fee_res = bank.mint(
                denom=FEE_DENOM,
                signer=from_addr,
                to_addr=FEE_COLLECTOR,
                amount=_int_to_amount_str(fee_n),
            )

            accounts_touched.append(FEE_COLLECTOR)
            fee_info["applied"] = True
            result = {"ok": True, "ops": [main_res, {"fee_to_collector": fee_res}]}
        else:
            result = bank.mint(
                denom=denom,
                signer=from_addr,
                to_addr=to_addr,
                amount=amount_raw,
            )

        applied = True

    elif tx_type == "BANK_SEND":
        denom = payload.get("denom")
        to_addr = payload.get("to")
        amount = payload.get("amount")

        if not isinstance(to_addr, str) or not to_addr:
            raise ValueError("payload.to required")

        accounts_touched.append(to_addr)

        if fee_n > 0:
            fee_res = bank.transfer(
                denom=FEE_DENOM,
                signer=from_addr,
                to_addr=FEE_COLLECTOR,
                amount=_int_to_amount_str(fee_n),
            )
            accounts_touched.append(FEE_COLLECTOR)
            fee_info["applied"] = True

            main_res = bank.transfer(
                denom=denom,
                signer=from_addr,
                to_addr=to_addr,
                amount=amount,
            )
            result = {"ok": True, "ops": [{"fee_to_collector": fee_res}, main_res]}
        else:
            result = bank.transfer(
                denom=denom,
                signer=from_addr,
                to_addr=to_addr,
                amount=amount,
            )

        applied = True

    elif tx_type == "BANK_BURN":
        denom = payload.get("denom")
        amount = payload.get("amount")

        if fee_n > 0:
            fee_res = bank.transfer(
                denom=FEE_DENOM,
                signer=from_addr,
                to_addr=FEE_COLLECTOR,
                amount=_int_to_amount_str(fee_n),
            )
            accounts_touched.append(FEE_COLLECTOR)
            fee_info["applied"] = True

            main_res = bank.burn(
                denom=denom,
                signer=from_addr,
                from_addr=from_addr,
                amount=amount,
            )
            result = {"ok": True, "ops": [{"fee_to_collector": fee_res}, main_res]}
        else:
            result = bank.burn(
                denom=denom,
                signer=from_addr,
                from_addr=from_addr,
                amount=amount,
            )

        applied = True

    # ───────────────────────────────────────────────
    # Staking (dev skeleton) — no fees
    # ───────────────────────────────────────────────
    elif tx_type == "STAKING_DELEGATE":
        validator = payload.get("validator")
        amount_tess = payload.get("amount_tess")

        if not isinstance(validator, str) or not validator:
            raise ValueError("payload.validator required")
        # amount_tess validated inside staking module

        result = staking.delegate(
            delegator=from_addr,
            validator=validator,
            amount_tess=str(amount_tess),
        )
        applied = True

        # consume exactly one nonce for the tx
        signer_acc.nonce += 1

        # staking invariants + bank invariants (if present)
        staking.assert_invariants()
        _maybe_assert_invariants()

    elif tx_type == "STAKING_UNDELEGATE":
        validator = payload.get("validator")
        amount_tess = payload.get("amount_tess")

        if not isinstance(validator, str) or not validator:
            raise ValueError("payload.validator required")

        result = staking.undelegate(
            delegator=from_addr,
            validator=validator,
            amount_tess=str(amount_tess),
        )
        applied = True

        signer_acc.nonce += 1

        staking.assert_invariants()
        _maybe_assert_invariants()

    # One nonce per tx (BANK txs can increment internally; clamp)
    if applied:
        _force_signer_nonce_once(from_addr, nonce + 1)
        _maybe_assert_invariants()

    receipt: Dict[str, Any] = {
        "ok": True,
        "tx_id": client_tx_id,  # back-compat
        "client_tx_id": client_tx_id,  # explicit
        "tx_hash": tx_hash,
        "tx_type": tx_type,
        "from_addr": from_addr,
        "nonce": nonce,
        "applied": applied,
        "created_at_ms": _now_ms(),
        "accounts_touched": list(dict.fromkeys(accounts_touched)),
        "fee": fee_info,
        "result": result,
    }

    _TX_LOG[client_tx_id] = receipt
    return receipt