# backend/modules/chain_sim/dev_chain_bank_smoketest.py

from __future__ import annotations

from decimal import Decimal
import httpx


BASE_URL = "http://localhost:8080"


def _mint_pho(address: str, amount: str = "1000"):
    r = httpx.post(
        f"{BASE_URL}/api/chain_sim/dev/mint",
        json={"denom": "PHO", "to": address, "amount": amount},
        timeout=5.0,
    )
    r.raise_for_status()
    data = r.json()
    assert data["ok"] is True
    assert data["denom"] == "PHO"
    assert data["amount"] == amount
    return data


def _transfer_pho(from_addr: str, to_addr: str, amount: str):
    r = httpx.post(
        f"{BASE_URL}/api/chain_sim/dev/transfer",
        json={
            "denom": "PHO",
            "from_addr": from_addr,
            "to": to_addr,
            "amount": amount,
        },
        timeout=5.0,
    )
    r.raise_for_status()
    data = r.json()
    assert data["ok"] is True
    assert data["denom"] == "PHO"
    assert data["amount"] == amount
    return data


def _get_supply():
    r = httpx.get(f"{BASE_URL}/api/chain_sim/dev/supply", timeout=5.0)
    r.raise_for_status()
    return r.json()


def test_mint_and_transfer_roundtrip():
    """
    Very small invariants smoketest for the dev chain bank:

      • Mint increases PHO supply by the minted amount.
      • Transfer call succeeds and does NOT change total PHO supply.
    """
    alice = "pho1-alice-test"
    bob = "pho1-bob-test"

    # Baseline total supply
    supply0 = _get_supply()
    pho0 = Decimal(supply0.get("PHO", "0"))

    # 1) Mint 1000 PHO to Alice
    _mint_pho(alice, "1000")

    # 2) Transfer 100 PHO Alice → Bob
    _transfer_pho(alice, bob, "100")

    # 3) Check total supply invariant
    supply1 = _get_supply()
    pho1 = Decimal(supply1.get("PHO", "0"))

    # Mint should add exactly 1000 PHO, transfer should conserve supply
    assert pho1 == pho0 + Decimal("1000")


def main():
    print("▶ dev_chain_bank_smoketest: starting")
    test_mint_and_transfer_roundtrip()
    print("✅ dev_chain_bank_smoketest: all assertions passed")


if __name__ == "__main__":
    main()