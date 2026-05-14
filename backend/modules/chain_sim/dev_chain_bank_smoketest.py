# backend/modules/chain_sim/dev_chain_bank_smoketest.py

from __future__ import annotations

import os
import uuid
from decimal import Decimal
from typing import Any, Dict, List

import httpx

BASE_URL = os.getenv("CHAIN_SIM_BASE_URL", "http://localhost:8080").rstrip("/")

# Must match chain_sim_engine.DEV_MINT_AUTHORITY
DEV_MINT_AUTHORITY = "pho1-dev-gma-authority"

# Fee plumbing (if enabled)
FEE_COLLECTOR = os.getenv("CHAIN_SIM_FEE_COLLECTOR", "pho1-dev-fee-collector")
FEE_PER_TX = Decimal(os.getenv("CHAIN_SIM_FEE_PER_TX", "1"))

# Optional: fail fast if ledger isn't recording blocks
ASSERT_LEDGER = os.getenv("CHAIN_SIM_ASSERT_LEDGER", "1") == "1"


def _get_json(path: str, params: dict | None = None) -> dict:
    r = httpx.get(f"{BASE_URL}{path}", params=params or {}, timeout=10.0)
    r.raise_for_status()
    return r.json()


def _post_json(path: str, body: dict) -> dict:
    r = httpx.post(f"{BASE_URL}{path}", json=body, timeout=10.0)
    r.raise_for_status()
    return r.json()


def _get_account(address: str) -> dict:
    return _get_json("/api/chain_sim/dev/account", params={"address": address})


def _get_supply() -> dict:
    return _get_json("/api/chain_sim/dev/supply")


def _pho_bal(acc: dict) -> Decimal:
    bals = acc.get("balances") or {}
    return Decimal(str(bals.get("PHO", "0")))


def _nonce(acc: dict) -> int:
    return int(acc.get("nonce", 0))


def _extract_ops(result_obj: Any) -> List[Dict[str, Any]]:
    if not isinstance(result_obj, dict):
        return []

    if "op" in result_obj and isinstance(result_obj.get("op"), str):
        return [result_obj]

    ops = result_obj.get("ops")
    if not isinstance(ops, list):
        return []

    out: List[Dict[str, Any]] = []
    for item in ops:
        if isinstance(item, dict) and "op" in item:
            out.append(item)
            continue

        if isinstance(item, dict) and len(item) == 1:
            (_, inner) = next(iter(item.items()))
            if isinstance(inner, dict) and "op" in inner:
                out.append(inner)
                continue

    return out


def _unwrap_result(receipt_or_result: dict) -> dict:
    if isinstance(receipt_or_result, dict) and isinstance(receipt_or_result.get("result"), dict):
        return receipt_or_result["result"]
    return receipt_or_result


def _min_signer_nonce_increment(receipt: dict) -> int:
    """
    Stable, model-agnostic expectation:
      - any applied tx must increment signer nonce by at least +1
      - if fee.applied==True, your dev pipeline executes an extra bank op,
        so nonce should increase by at least +2 total.
    """
    fee = receipt.get("fee") or {}
    fee_applied = bool(fee.get("applied"))
    return 2 if fee_applied else 1


def _submit_tx(*, from_addr: str, tx_type: str, payload: dict) -> dict:
    signer_acc = _get_account(from_addr)
    nonce = _nonce(signer_acc)

    receipt = _post_json(
        "/api/chain_sim/dev/submit_tx",
        {
            "from_addr": from_addr,
            "nonce": nonce,
            "tx_type": tx_type,
            "payload": payload,
        },
    )

    assert receipt.get("ok") is True, receipt
    assert receipt.get("applied") is True, receipt
    assert receipt.get("from_addr") == from_addr, receipt
    assert receipt.get("nonce") == nonce, receipt
    assert receipt.get("tx_type") == tx_type, receipt
    assert "tx_id" in receipt, receipt
    assert "tx_hash" in receipt, receipt
    assert "result" in receipt, receipt

    if ASSERT_LEDGER:
        assert "block_height" in receipt and "tx_index" in receipt, (
            "submit_tx receipt missing block_height/tx_index. "
            "This usually means record_applied_tx is not being called in /dev/submit_tx "
            "or you need to restart the FastAPI server."
        )

    return receipt


def _mint_pho(to_addr: str, amount: str) -> dict:
    receipt = _submit_tx(
        from_addr=DEV_MINT_AUTHORITY,
        tx_type="BANK_MINT",
        payload={"denom": "PHO", "to": to_addr, "amount": amount},
    )
    result = _unwrap_result(receipt)
    ops = _extract_ops(result)
    if ops:
        assert any(op.get("op") == "MINT" for op in ops), ops
    else:
        assert result.get("ok") is True, result
        assert result.get("op") == "MINT", result
    return receipt


def _transfer_pho(from_addr: str, to_addr: str, amount: str) -> dict:
    receipt = _submit_tx(
        from_addr=from_addr,
        tx_type="BANK_SEND",
        payload={"denom": "PHO", "to": to_addr, "amount": amount},
    )
    result = _unwrap_result(receipt)
    ops = _extract_ops(result)
    if ops:
        assert any(op.get("op") in ("TRANSFER", "SEND") for op in ops), ops
    else:
        assert result.get("ok") is True, result
        assert result.get("op") in ("TRANSFER", "SEND"), result
    return receipt


def _burn_pho(from_addr: str, amount: str) -> dict:
    receipt = _submit_tx(
        from_addr=from_addr,
        tx_type="BANK_BURN",
        payload={"denom": "PHO", "amount": amount},
    )
    result = _unwrap_result(receipt)
    ops = _extract_ops(result)
    if ops:
        assert any(op.get("op") == "BURN" for op in ops), ops
    else:
        assert result.get("ok") is True, result
        assert result.get("op") == "BURN", result
    return receipt


def test_submit_tx_mint_transfer_burn_roundtrip():
    suffix = uuid.uuid4().hex[:10]
    alice = f"pho1-alice-test-bank-{suffix}"
    bob = f"pho1-bob-test-bank-{suffix}"

    supply0_pho = Decimal(str(_get_supply().get("PHO", "0")))

    auth0 = _get_account(DEV_MINT_AUTHORITY)
    alice0 = _get_account(alice)
    bob0 = _get_account(bob)
    fee0 = _get_account(FEE_COLLECTOR)

    n0_auth = _nonce(auth0)
    n0_alice = _nonce(alice0)
    n0_bob = _nonce(bob0)

    alice0_pho = _pho_bal(alice0)
    bob0_pho = _pho_bal(bob0)
    fee0_pho = _pho_bal(fee0)

    # 1) Mint 1000 PHO to Alice
    mint_amount = Decimal("1000")
    mint_receipt = _mint_pho(alice, "1000")

    supply1_pho = Decimal(str(_get_supply().get("PHO", "0")))
    assert supply1_pho == supply0_pho + mint_amount

    auth1 = _get_account(DEV_MINT_AUTHORITY)
    alice1 = _get_account(alice)
    fee1 = _get_account(FEE_COLLECTOR)

    # ✅ Nonce semantics: increment ONCE per submitted tx (fees do not add extra nonce bumps)
    assert _nonce(auth1) == n0_auth + 1
    assert _nonce(alice1) == n0_alice  # receiving mint shouldn't increment

    # Distribution sanity: Alice + fee_collector should reflect minted amount (relative to baseline)
    alice1_pho = _pho_bal(alice1)
    fee1_pho = _pho_bal(fee1)
    assert (alice1_pho - alice0_pho) + (fee1_pho - fee0_pho) == mint_amount

    # 2) Transfer 100 PHO Alice → Bob
    send_amount = Decimal("100")
    send_receipt = _transfer_pho(alice, bob, "100")

    supply2_pho = Decimal(str(_get_supply().get("PHO", "0")))
    assert supply2_pho == supply1_pho  # transfers conserve total supply

    alice2 = _get_account(alice)
    bob2 = _get_account(bob)
    fee2 = _get_account(FEE_COLLECTOR)

    # ✅ Nonce increments ONCE per submitted tx
    assert _nonce(alice2) == _nonce(alice1) + 1
    assert _nonce(bob2) == n0_bob  # receiving transfer shouldn't increment

    # Bob must increase by send_amount (fees should not reduce receiver)
    assert _pho_bal(bob2) == bob0_pho + send_amount

    # 3) Burn 50 PHO from Alice
    burn_amount = Decimal("50")
    burn_receipt = _burn_pho(alice, "50")

    supply3_pho = Decimal(str(_get_supply().get("PHO", "0")))
    assert supply3_pho == supply2_pho - burn_amount

    alice3 = _get_account(alice)
    bob3 = _get_account(bob)
    fee3 = _get_account(FEE_COLLECTOR)

    # ✅ Nonce increments ONCE per submitted tx
    assert _nonce(alice3) == _nonce(alice2) + 1
    assert _pho_bal(bob3) == _pho_bal(bob2)

    # Non-negative invariants
    assert _pho_bal(alice3) >= 0
    assert _pho_bal(bob3) >= 0
    assert supply3_pho >= 0

    # Fee collector should never go down
    assert _pho_bal(fee3) >= fee0_pho


def main():
    print("▶ dev_chain_bank_smoketest: starting")
    test_submit_tx_mint_transfer_burn_roundtrip()
    print("✅ dev_chain_bank_smoketest: all assertions passed")


if __name__ == "__main__":
    main()