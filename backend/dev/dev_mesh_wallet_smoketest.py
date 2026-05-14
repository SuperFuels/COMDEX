# backend/dev/dev_mesh_wallet_smoketest.py
"""
Quick smoketest for wallet + mesh local_state/local_send.

Usage (from repo root):
  python -m backend.dev.dev_mesh_wallet_smoketest

Assumes backend is running on http://localhost:8080.
"""

from __future__ import annotations

import json
import time
from decimal import Decimal

import requests

BASE = "http://localhost:8080"
ACCOUNT = "pho1-demo-offline"
TO_ACCOUNT = "pho1receiver"


def pretty(title: str, obj):
    print(f"\n=== {title} ===")
    print(json.dumps(obj, indent=2, sort_keys=True))


def get_wallet_balances(owner_wa: str | None = None):
    headers = {}
    if owner_wa:
        headers["X-Owner-WA"] = owner_wa
    r = requests.get(f"{BASE}/api/wallet/balances", headers=headers, timeout=5)
    r.raise_for_status()
    return r.json()


def get_local_state(account: str):
    r = requests.get(f"{BASE}/api/mesh/local_state/{account}", timeout=5)
    r.raise_for_status()
    return r.json()


def post_local_send(from_account: str, to_account: str, amount_pho: str):
    payload = {
        "from_account": from_account,
        "to_account": to_account,
        "amount_pho": amount_pho,
    }
    r = requests.post(
        f"{BASE}/api/mesh/local_send",
        headers={"Content-Type": "application/json"},
        data=json.dumps(payload),
        timeout=5,
    )
    r.raise_for_status()
    return r.json()


def main():
    print("Running dev_mesh_wallet_smoketest against", BASE)
    print(f"Using from_account={ACCOUNT}, to_account={TO_ACCOUNT}")

    # 1) Baseline wallet view
    w0 = get_wallet_balances(None)
    pretty("Wallet /balances (initial)", w0)

    # 2) Baseline mesh local_state
    s0 = get_local_state(ACCOUNT)
    pretty("Mesh /local_state (initial)", s0)

    # 3) Do a small mesh send (e.g. 1.0 PHO)
    amount = "1.0"
    print(f"\n-- POST /api/mesh/local_send {ACCOUNT} → {TO_ACCOUNT} amount={amount} --")
    send_resp = post_local_send(ACCOUNT, TO_ACCOUNT, amount)
    pretty("Mesh /local_send response", send_resp)

    # 4) Re-read mesh state
    time.sleep(0.1)
    s1 = get_local_state(ACCOUNT)
    pretty("Mesh /local_state (after send)", s1)

    # 5) Re-read wallet balances (should reflect new mesh_pending_pho + PHO display)
    w1 = get_wallet_balances(None)
    pretty("Wallet /balances (after send)", w1)

    # 6) Quick sanity checks
    try:
        b0 = Decimal(w0["balances"]["pho"])
        b1 = Decimal(w1["balances"]["pho"])
        pending1 = Decimal(w1["balances"]["mesh_pending_pho"])
        print(
            f"\nSanity: PHO display {b0} → {b1}, "
            f"mesh_pending_pho={pending1}"
        )
    except Exception as e:
        print("Sanity check failed:", e)

    print("\nSmoketest complete.")


if __name__ == "__main__":
    main()