# backend/dev_mesh_reconcile_smoketest.py

"""
Quick smoketest for MeshReconcile + offline credit policy.

Usage:
    PYTHONPATH=. python backend/dev_mesh_reconcile_smoketest.py
"""

from decimal import Decimal
import time
import uuid

from backend.modules.mesh.mesh_tx import MeshTx
from backend.modules.mesh.mesh_reconcile_service import ReconcileRequest, reconcile_account
from backend.modules.gma.gma_mesh_policy import set_offline_limit
from backend.modules.wallet.mesh_wallet_state import (
    init_local_balance,
    new_local_tx_log,
    record_outgoing_tx,
    effective_spendable_local,
)


def main():
    account = "pho1demooffline"
    device_id = "dev-mesh-1"

    # Set a small offline limit so we can see clamping in action.
    set_offline_limit(account, Decimal("25.0"))  # 25 PHO offline headroom

    # Enter mesh mode with 100 PHO global.
    balance = init_local_balance(account, "100.0", safety_buffer_pho="1.0")
    log = new_local_tx_log(account)

    print("Initial balance:", balance)
    print("Effective spendable (local):", effective_spendable_local(balance))

    # Create 2 local outgoing txs: 10 + 20 = 30 PHO (beyond 25 limit).
    now_ms = int(time.time() * 1000)

    for amt in ("10.0", "20.0"):
        balance, log, tx = record_outgoing_tx(
            balance=balance,
            log=log,
            to_account="pho1receiver",
            amount_pho=amt,
            mesh_tx_id=f"m_{uuid.uuid4().hex[:8]}",
            cluster_id="cluster_demo",
            device_id=device_id,
            created_at_ms=now_ms,
            sender_signature="sig-demo",
        )
        print(f"\nRecorded local send of {amt} PHO → MeshTx:", tx)

    print("\nFinal LocalBalance:", balance)
    print("Effective spendable (local, client-side):", effective_spendable_local(balance))

    # Now pretend we reconnected and send everything to MeshReconcile.
    req: ReconcileRequest = {
        "account": account,
        "device_id": device_id,
        "last_global_block_height": 0,
        "local_mesh_txs": log["entries"],
    }

    result = reconcile_account(req)

    print("\n--- Reconcile Result ---")
    print("accepted_local_delta_pho:", result["accepted_local_delta_pho"])
    print("disputed_mesh_tx_ids:", result["disputed_mesh_tx_ids"])
    print("settlement_tx_hash:", result["settlement_tx_hash"])


if __name__ == "__main__":
    main()