# backend/modules/chain_sim/dev_chain_bank_smoketest.py

from __future__ import annotations

from decimal import Decimal
import uuid
import httpx

BASE_URL = "http://localhost:8080"

# Must match chain_sim_engine.DEV_MINT_AUTHORITY
DEV_MINT_AUTHORITY = "pho1-dev-gma-authority"


def _get_account(address: str):
    r = httpx.get(
        f"{BASE_URL}/api/chain_sim/dev/account",
        params={"address": address},
        timeout=5.0,
    )
    r.raise_for_status()
    return r.json()


def _get_supply():
    r = httpx.get(f"{BASE_URL}/api/chain_sim/dev/supply", timeout=5.0)
    r.raise_for_status()
    return r.json()


def _submit(tx: dict):
    """
    tx = {
      "from_addr": "...",
      "tx_type": "BANK_MINT" | "BANK_SEND" | "BANK_BURN",
      "payload": {...}
    }
    nonce is auto-filled from chain state.
    """
    from_addr = tx["from_addr"]

    # signer nonce comes from chain state
    acc = _get_account(from_addr)
    nonce = int(acc.get("nonce", 0))

    r = httpx.post(
        f"{BASE_URL}/api/chain_sim/dev/submit_tx",
        json={
            "from_addr": from_addr,
            "nonce": nonce,
            "tx_type": tx["tx_type"],
            "payload": tx["payload"],
        },
        timeout=5.0,
    )
    r.raise_for_status()
    data = r.json()

    # receipt-level asserts (keep these; they prove envelope semantics)
    assert data["ok"] is True
    assert data["applied"] is True
    assert data["from_addr"] == from_addr
    assert data["nonce"] == nonce
    assert data["tx_type"] == tx["tx_type"]
    assert "tx_id" in data
    assert "tx_hash" in data
    assert "result" in data
    return data

def _mint_pho(to_addr: str, amount: str = "1000"):
    receipt = _submit({
        "from_addr": DEV_MINT_AUTHORITY,
        "tx_type": "BANK_MINT",
        "payload": {"denom": "PHO", "to": to_addr, "amount": amount},
    })
    res = receipt["result"]
    assert res["op"] == "MINT"
    assert res["amount"] == amount
    return receipt


def _transfer_pho(from_addr: str, to_addr: str, amount: str):
    receipt = _submit({
        "from_addr": from_addr,
        "tx_type": "BANK_SEND",
        "payload": {"denom": "PHO", "to": to_addr, "amount": amount},
    })
    res = receipt["result"]
    assert res["op"] == "TRANSFER"
    assert res["amount"] == amount
    return receipt


def _burn_pho(from_addr: str, amount: str):
    receipt = _submit({
        "from_addr": from_addr,
        "tx_type": "BANK_BURN",
        "payload": {"denom": "PHO", "amount": amount},
    })
    res = receipt["result"]
    assert res["op"] == "BURN"
    assert res["amount"] == amount
    return receipt


def test_submit_tx_mint_transfer_burn_roundtrip():
    # Use unique addresses so repeated runs don't collide with in-memory state
    suffix = uuid.uuid4().hex[:10]
    alice = f"pho1-alice-test-bank-{suffix}"
    bob = f"pho1-bob-test-bank-{suffix}"

    # Baseline supply before we touch anything
    supply0 = _get_supply()
    supply0_pho = Decimal(supply0.get("PHO", "0"))

    # Baseline nonces
    n0_auth = int(_get_account(DEV_MINT_AUTHORITY).get("nonce", 0))
    n0_alice = int(_get_account(alice).get("nonce", 0))
    n0_bob = int(_get_account(bob).get("nonce", 0))

    # 1) Mint 1000 PHO to Alice (signed by dev mint authority)
    _mint_pho(alice, "1000")

    acc_alice = _get_account(alice)
    assert acc_alice["address"] == alice
    assert acc_alice["balances"]["PHO"] == "1000"

    supply1 = _get_supply()
    supply1_pho = Decimal(supply1["PHO"])
    assert supply1_pho == supply0_pho + Decimal("1000")

    # Nonce semantics: ONLY signer increments (authority), not receiver (alice)
    n1_auth = int(_get_account(DEV_MINT_AUTHORITY).get("nonce", 0))
    n1_alice = int(_get_account(alice).get("nonce", 0))
    assert n1_auth == n0_auth + 1
    assert n1_alice == n0_alice  # unchanged by receiving mint

    # 2) Transfer 100 PHO Alice → Bob (signed by Alice)
    _transfer_pho(alice, bob, "100")

    acc_alice = _get_account(alice)
    acc_bob = _get_account(bob)

    assert acc_alice["balances"]["PHO"] == "900"
    assert acc_bob["balances"]["PHO"] == "100"

    supply2 = _get_supply()
    supply2_pho = Decimal(supply2["PHO"])
    # Transfers must conserve total PHO supply
    assert supply2_pho == supply1_pho

    # Nonce semantics: ONLY signer increments (alice), not receiver (bob)
    n2_alice = int(_get_account(alice).get("nonce", 0))
    n2_bob = int(_get_account(bob).get("nonce", 0))
    assert n2_alice == n1_alice + 1
    assert n2_bob == n0_bob  # unchanged by receiving transfer

    # 3) Burn 50 PHO from Alice (signed by Alice)
    _burn_pho(alice, "50")

    acc_alice_after = _get_account(alice)
    acc_bob_after = _get_account(bob)
    supply3 = _get_supply()
    supply3_pho = Decimal(supply3["PHO"])

    assert acc_alice_after["balances"]["PHO"] == "850"
    assert acc_bob_after["balances"]["PHO"] == "100"
    assert supply3_pho == supply2_pho - Decimal("50")

    # Burn increments signer nonce again
    n3_alice = int(_get_account(alice).get("nonce", 0))
    assert n3_alice == n2_alice + 1

    # Basic non-negative invariants
    assert Decimal(acc_alice_after["balances"]["PHO"]) >= 0
    assert Decimal(acc_bob_after["balances"]["PHO"]) >= 0
    assert supply3_pho >= 0


def main():
    print("▶ dev_chain_bank_smoketest: starting")
    test_submit_tx_mint_transfer_burn_roundtrip()
    print("✅ dev_chain_bank_smoketest: all assertions passed")


if __name__ == "__main__":
    main()