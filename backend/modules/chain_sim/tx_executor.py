# backend/modules/chain_sim/tx_executor.py
from __future__ import annotations

import inspect
from importlib import import_module
from typing import Any, Dict, Tuple, Optional, Callable

from .tx_models import TxEnvelope

# Bank ops live here (mint/transfer/burn + nonce increments + fees)
from backend.modules.chain_sim import chain_sim_model as bank

# ────────────────────────────────────────────────────────────────
# Cached engine/module lookups (keeps tx path fast)
# ────────────────────────────────────────────────────────────────

_ENGINE_MOD: Optional[Any] = None
_ENGINE_APPLY: Optional[Callable[..., Any]] = None
_ENGINE_SNAPSHOT: Optional[Callable[..., Any]] = None
_TX_FN_CACHE: Dict[str, Optional[Callable[..., Any]]] = {}


def _engine() -> Any:
    global _ENGINE_MOD
    if _ENGINE_MOD is None:
        _ENGINE_MOD = import_module("backend.modules.chain_sim.chain_sim_engine")
    return _ENGINE_MOD


def _call(fn: Callable[..., Any], **kwargs) -> Any:
    """Call fn with only the kwargs it actually accepts."""
    sig = inspect.signature(fn)
    accepted = {k: v for k, v in kwargs.items() if k in sig.parameters}
    return fn(**accepted)


def _first_callable_from_engine(names: tuple[str, ...]) -> Optional[Callable[..., Any]]:
    mod = _engine()
    for n in names:
        fn = getattr(mod, n, None)
        if callable(fn):
            return fn
    return None


def _normalize_engine_return(out: Any) -> Tuple[bool, Optional[str], Dict[str, Any]]:
    """
    Normalize common return shapes into:
      (applied_bool, error_str_or_None, result_payload_dict)

    Supported:
      - (ok/applied, err, receipt) OR [ok/applied, err, receipt]
      - {"applied": bool, "error": ..., "result": ...}
      - {"ok": bool, "error": ..., "receipt"/"result": ...}
      - dict payload (assume applied=True)
      - any other -> {"result": out} (assume applied=True)
    """
    if isinstance(out, (tuple, list)) and len(out) == 3 and isinstance(out[0], bool):
        applied = bool(out[0])
        err = out[1]
        receipt = out[2]
        payload = (receipt or {}) if isinstance(receipt, dict) else {"receipt": receipt}
        return applied, (str(err) if err else None), payload

    if isinstance(out, dict):
        if "applied" in out:
            applied = bool(out.get("applied", False))
            err = out.get("error")
            res = out.get("result") if "result" in out else (out.get("receipt") or {})
            payload = res if isinstance(res, dict) else {"receipt": res}
            return applied, (str(err) if err else None), payload

        if "ok" in out or "error" in out:
            applied = bool(out.get("ok", True))
            err = out.get("error")
            res = out.get("receipt") or out.get("result") or {}
            payload = res if isinstance(res, dict) else {"receipt": res}
            return applied, (str(err) if err else None), payload

        return True, None, out

    return True, None, {"result": out}


def _get_attr(x: Any, name: str, default: Any = None) -> Any:
    try:
        return getattr(x, name)
    except Exception:
        return default


def _current_nonce(addr: str) -> int:
    try:
        return int(bank.get_or_create_account(str(addr)).nonce or 0)
    except Exception:
        return 0


def _check_nonce(from_addr: str, nonce: Any) -> Optional[str]:
    """
    GlyphChain dev txs use 1-based nonces:
      - stored account.nonce starts at 0 after reset/genesis
      - first tx must use nonce=1
      - after apply, bank ops increment nonce by exactly +1
    """
    if nonce is None:
        return "nonce is required"
    try:
        got = int(nonce)
    except Exception:
        return "nonce must be an int"

    cur = _current_nonce(from_addr)
    exp = int(cur) + 1  # ✅ 1-based expected nonce

    if got != exp:
        return f"bad nonce: expected {exp}, got {got}"
    return None


# Candidate function names per tx type (ENGINE ONLY) — kept permissive.
_TX_CANDIDATES: Dict[str, tuple[str, ...]] = {
    "BANK_MINT": (
        "apply_bank_mint",
        "bank_mint",
        "dev_bank_mint",
        "dev_mint",
        "mint_dev",
    ),
    "BANK_SEND": (
        "apply_bank_send",
        "bank_send",
        "dev_bank_send",
        "send_dev",
    ),
    "BANK_TRANSFER": (
        "apply_bank_transfer",
        "bank_transfer",
        "dev_bank_transfer",
        "dev_transfer",
        "transfer_dev",
    ),
    "BANK_BURN": (
        "apply_bank_burn",
        "bank_burn",
        "dev_bank_burn",
        "dev_burn",
        "burn_dev",
    ),
    "STAKING_DELEGATE": (
        "apply_staking_delegate",
        "staking_delegate",
        "dev_staking_delegate",
        "dev_delegate",
        "handle_staking_delegate",
    ),
    "STAKING_UNDELEGATE": (
        "apply_staking_undelegate",
        "staking_undelegate",
        "dev_staking_undelegate",
        "dev_undelegate",
        "handle_staking_undelegate",
    ),
}


def _apply_bank_inline(envelope: Any) -> Tuple[bool, Optional[str], Dict[str, Any]]:
    """
    Inline BANK_* implementation (dev correctness path).
    Uses backend.modules.chain_sim.chain_sim_model.

    Enforces:
      - nonce equality (expected == provided)
      - dev fee rules (PHO fixed fee) applied atomically w/ the op (inside bank.* lock)

    Returns: (applied, error, result_payload)
    """
    t = str(_get_attr(envelope, "tx_type", "") or "")
    if t == "BANK_TRANSFER":
        t = "BANK_SEND"

    from_addr = str(_get_attr(envelope, "from_addr", "") or "").strip()
    payload = _get_attr(envelope, "payload", None) or {}
    nonce = _get_attr(envelope, "nonce", None)

    if not from_addr:
        return False, "from_addr required", {"op": t, "payload": payload}

    nerr = _check_nonce(from_addr, nonce)
    if nerr:
        cur = _current_nonce(from_addr)
        return False, nerr, {
            "op": t,
            "payload": payload,
            "expected_nonce": int(cur) + 1,  # ✅ match 1-based rule
            "got_nonce": nonce,
        }

    try:
        denom = str((payload or {}).get("denom", "") or "")
        amount_raw = (payload or {}).get("amount", None)

        # Parse once for fee carve-out decisions
        amt = bank._parse_nonneg_int(amount_raw, field="amount", allow_zero=False)  # type: ignore[attr-defined]

        if t == "BANK_MINT":
            to_addr = str((payload or {}).get("to", "") or "")
            if not denom or not to_addr:
                return False, "payload must include denom and to", {"op": t, "payload": payload}

            fee = bank.charge_fee_if_needed(
                signer=from_addr,
                op="BANK_MINT",
                mint_denom=denom,
                mint_amount=amt,
            )
            out = bank.mint(
                denom=denom,
                signer=from_addr,
                to_addr=to_addr,
                amount=str(amt),
                fee=fee,
            )
            # bank.mint attaches fee when applied
            return True, None, out

        if t == "BANK_SEND":
            to_addr = str((payload or {}).get("to", "") or "")
            if not denom or not to_addr:
                return False, "payload must include denom and to", {"op": t, "payload": payload}

            fee = bank.charge_fee_if_needed(signer=from_addr, op="BANK_SEND")
            out = bank.transfer(
                denom=denom,
                signer=from_addr,
                to_addr=to_addr,
                amount=str(amt),
                fee=fee,
            )
            return True, None, out

        if t == "BANK_BURN":
            burn_from = str((payload or {}).get("from_addr", "") or "") or from_addr
            if not denom:
                return False, "payload must include denom", {"op": t, "payload": payload}

            fee = bank.charge_fee_if_needed(signer=from_addr, op="BANK_BURN")
            out = bank.burn(
                denom=denom,
                signer=from_addr,
                from_addr=burn_from,
                amount=str(amt),
                fee=fee,
            )
            return True, None, out

        return False, f"inline bank handler missing for {t}", {"op": t, "payload": payload}

    except Exception as e:
        return False, str(e), {"op": t, "payload": payload}


def apply_tx(envelope: TxEnvelope) -> Tuple[bool, Optional[str], Dict[str, Any]]:
    """
    Returns: (applied_bool, error, result_payload)

    ROUTING + EXECUTION.
    - Prefers engine dispatcher if present.
    - Else routes to engine helper if present.
    - Else executes BANK_* inline (dev correctness path).

    Conventions:
      - applied_bool=True  => state mutated (block should be recorded)
      - applied_bool=False => tx rejected / no-op OR internal failure
      - internal failures MUST set result_payload["internal_error"]=True
    """
    global _ENGINE_APPLY

    t = str(_get_attr(envelope, "tx_type", "") or "")
    p = _get_attr(envelope, "payload", None) or {}

    t_eff = "BANK_SEND" if t == "BANK_TRANSFER" else t

    def _ctx(extra: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        base: Dict[str, Any] = {"op": t_eff, "payload": p}
        if isinstance(extra, dict):
            base.update(extra)
        return base

    try:
        if _ENGINE_APPLY is None:
            _ENGINE_APPLY = _first_callable_from_engine(
                (
                    "apply_tx",
                    "apply_dev_tx",
                    "execute_tx",
                    "apply_tx_envelope",
                    "apply_tx_type",
                    "apply_tx_dispatch",
                    "apply_tx_to_state",
                )
            )

        if _ENGINE_APPLY:
            out = _call(
                _ENGINE_APPLY,
                envelope=envelope,
                tx=envelope,
                tx_type=t_eff,
                from_addr=_get_attr(envelope, "from_addr", None),
                sender=_get_attr(envelope, "from_addr", None),
                payload=p,
                nonce=_get_attr(envelope, "nonce", None),
                tx_id=_get_attr(envelope, "tx_id", None),
                tx_hash=_get_attr(envelope, "tx_hash", None),
            )
            applied, err, payload = _normalize_engine_return(out)
            if isinstance(payload, dict):
                payload.setdefault("op", t_eff)
                payload.setdefault("payload", p)
            else:
                payload = {"result": payload, **_ctx()}
            return bool(applied), (str(err) if err else None), payload

        if t_eff in ("BANK_MINT", "BANK_SEND", "BANK_BURN"):
            fn = _TX_FN_CACHE.get(t_eff)
            if fn is None and t_eff not in _TX_FN_CACHE:
                fn = _first_callable_from_engine(_TX_CANDIDATES.get(t_eff, ()))
                _TX_FN_CACHE[t_eff] = fn

            fn = _TX_FN_CACHE.get(t_eff)
            if fn:
                out = _call(
                    fn,
                    envelope=envelope,
                    tx=envelope,
                    tx_type=t_eff,
                    from_addr=_get_attr(envelope, "from_addr", None),
                    sender=_get_attr(envelope, "from_addr", None),
                    payload=p,
                    **(p if isinstance(p, dict) else {}),
                )
                applied, err, payload = _normalize_engine_return(out)
                if isinstance(payload, dict):
                    payload.setdefault("op", t_eff)
                    payload.setdefault("payload", p)
                else:
                    payload = {"result": payload, **_ctx()}
                return bool(applied), (str(err) if err else None), payload

            applied, err, payload = _apply_bank_inline(envelope)
            if isinstance(payload, dict):
                payload.setdefault("op", t_eff)
                payload.setdefault("payload", p)
            else:
                payload = {"result": payload, **_ctx()}
            return bool(applied), (str(err) if err else None), payload

        if t_eff not in _TX_CANDIDATES:
            return False, f"unknown tx_type: {t_eff}", _ctx()

        fn = _TX_FN_CACHE.get(t_eff)
        if fn is None and t_eff not in _TX_FN_CACHE:
            fn = _first_callable_from_engine(_TX_CANDIDATES[t_eff])
            _TX_FN_CACHE[t_eff] = fn

        fn = _TX_FN_CACHE.get(t_eff)
        if not fn:
            return False, f"{t_eff} not wired (no helper found in chain_sim_engine)", _ctx()

        out = _call(
            fn,
            envelope=envelope,
            tx=envelope,
            tx_type=t_eff,
            from_addr=_get_attr(envelope, "from_addr", None),
            sender=_get_attr(envelope, "from_addr", None),
            payload=p,
            **(p if isinstance(p, dict) else {}),
        )
        applied, err, payload = _normalize_engine_return(out)
        if isinstance(payload, dict):
            payload.setdefault("op", t_eff)
            payload.setdefault("payload", p)
        else:
            payload = {"result": payload, **_ctx()}
        return bool(applied), (str(err) if err else None), payload

    except Exception as e:
        return False, str(e), {"internal_error": True, **_ctx()}


def apply_tx_receipt(envelope: TxEnvelope) -> Dict[str, Any]:
    """
    Convenience wrapper used by routes:
      returns { ok, applied, error, result }

    Standardized semantics:
      - ok=True  => request handled (even if tx rejected)
      - applied=True => state mutated / block should be recorded
      - ok=False => internal executor failure (bug/exception path), not a user rejection
    """
    applied_flag, err, payload = apply_tx(envelope)

    if isinstance(payload, dict):
        result: Dict[str, Any] = dict(payload)
    else:
        result = {"result": payload}

    try:
        op = getattr(envelope, "tx_type", None)
        if op:
            result.setdefault("op", op)
    except Exception:
        pass

    try:
        p = getattr(envelope, "payload", None) or {}
        if isinstance(p, dict):
            result.setdefault("payload", p)
    except Exception:
        pass

    internal = bool(result.get("internal_error") is True)

    if internal:
        return {
            "ok": False,
            "applied": False,
            "error": (str(err) if err else "internal executor error"),
            "result": result,
        }

    return {
        "ok": True,
        "applied": bool(applied_flag),
        "error": (str(err) if err else None),
        "result": result,
    }


def get_chain_state_snapshot() -> Dict[str, Any]:
    """
    Must return a deterministic snapshot:
      { "config": {...}, "bank": {...}, "staking": {...} }

    Uses chain_sim_engine ONLY.
    """
    global _ENGINE_SNAPSHOT

    try:
        if _ENGINE_SNAPSHOT is None:
            _ENGINE_SNAPSHOT = _first_callable_from_engine(
                (
                    "get_chain_state_snapshot",
                    "get_dev_state_snapshot",
                    "get_dev_chain_state_snapshot",
                    "export_dev_state",
                    "export_state_snapshot",
                    "snapshot",
                )
            )

        if _ENGINE_SNAPSHOT:
            out = _call(_ENGINE_SNAPSHOT)
            if isinstance(out, dict):
                return out

        return {"config": {}, "bank": {}, "staking": {}}

    except Exception:
        return {"config": {}, "bank": {}, "staking": {}}