# backend/modules/wallet/mesh_wallet_state.py

from __future__ import annotations

from decimal import Decimal
from typing import Dict, Tuple, Any

from backend.modules.mesh.mesh_types import (
    LocalBalance,
    AccountId,
    ClusterId,
    DeviceId,
)
from backend.modules.mesh.mesh_tx import MeshTx, LocalTxLog, new_mesh_tx
from backend.modules.gma.gma_mesh_policy import get_offline_limit


# ───────────────────────────────────────────────
# Core mesh wallet helpers (device-side model)
# ───────────────────────────────────────────────


def init_local_balance(
    account: AccountId,
    global_confirmed_pho: str,
    safety_buffer_pho: str = "1.0",
) -> LocalBalance:
    """
    Initialize a LocalBalance for an account when entering mesh mode.
    """
    limit = get_offline_limit(account)
    return LocalBalance(
        account=account,
        global_confirmed_pho=global_confirmed_pho,
        local_net_delta_pho="0",
        offline_credit_limit_pho=str(limit),
        safety_buffer_pho=safety_buffer_pho,
    )


def effective_spendable_local(balance: LocalBalance) -> Decimal:
    """
    What the wallet should show as "local available" in mesh mode.

      base = global_confirmed_pho
      + max(local_net_delta_pho, 0)
      - safety_buffer_pho

    with the net negative delta clamped to the offline limit.
    """
    g = Decimal(balance["global_confirmed_pho"])
    d = Decimal(balance["local_net_delta_pho"])
    buf = Decimal(balance["safety_buffer_pho"])
    limit = Decimal(balance["offline_credit_limit_pho"])

    # clamp net spending to offline limit
    if d < Decimal("0"):
        min_delta = -limit
        if d < min_delta:
            d = min_delta

    # only add positive local_net_delta to displayed “available”
    local_plus = d if d > 0 else Decimal("0")

    return g + local_plus - buf


def new_local_tx_log(account: AccountId) -> LocalTxLog:
    return LocalTxLog(account=account, entries=[], last_seq=0)


def _apply_mesh_tx_delta(balance: LocalBalance, tx: MeshTx) -> LocalBalance:
    """
    Pure function: return a LocalBalance with updated local_net_delta_pho.
    """
    acct = balance["account"]
    delta = Decimal(balance["local_net_delta_pho"])
    amt = Decimal(tx["amount_pho"])

    if tx["from_account"] == acct:
        delta -= amt
    if tx["to_account"] == acct:
        delta += amt

    balance["local_net_delta_pho"] = str(delta)
    return balance


def record_outgoing_tx(
    balance: LocalBalance,
    log: LocalTxLog,
    to_account: AccountId,
    amount_pho: str,
    mesh_tx_id: str,
    cluster_id: str,
    device_id: str,
    created_at_ms: int,
    sender_signature: str,
) -> Tuple[LocalBalance, LocalTxLog, MeshTx]:
    """
    Construct a MeshTx for an outgoing payment from this account,
    bump local seq, update LocalBalance + LocalTxLog.
    """
    next_seq = log["last_seq"] + 1

    tx: MeshTx = {
        "mesh_tx_id": mesh_tx_id,
        "cluster_id": cluster_id,
        "from_account": balance["account"],
        "to_account": to_account,
        "amount_pho": amount_pho,
        "created_at_ms": created_at_ms,
        "prev_local_seq": next_seq - 1,
        "sender_device_id": device_id,
        "sender_signature": sender_signature,
    }

    _apply_mesh_tx_delta(balance, tx)
    log["entries"].append(tx)
    log["last_seq"] = next_seq

    return balance, log, tx


def record_incoming_tx(
    balance: LocalBalance,
    log: LocalTxLog,
    tx: MeshTx,
) -> Tuple[LocalBalance, LocalTxLog]:
    """
    Apply a received MeshTx to local state (for this account).
    """
    _apply_mesh_tx_delta(balance, tx)
    log["entries"].append(tx)
    # we *do not* bump last_seq here, seq is tied to sender, not receiver
    return balance, log


def refresh_from_chain(
    balance: LocalBalance,
    new_global_confirmed_pho: str,
) -> LocalBalance:
    """
    Called when we reconnect and fetch latest on-chain balance.
    Keeps local_net_delta_pho as-is; reconciliation will later adjust.
    """
    balance["global_confirmed_pho"] = new_global_confirmed_pho
    return balance


# ───────────────────────────────────────────────
# API-facing mesh wallet state (in-memory demo)
# ───────────────────────────────────────────────

_LOCAL_BALANCES: Dict[AccountId, LocalBalance] = {}
_LOCAL_LOGS: Dict[AccountId, LocalTxLog] = {}

_DEFAULT_GLOBAL_CONFIRMED = Decimal("100.0")
_DEFAULT_OFFLINE_LIMIT = Decimal("25.0")
_DEFAULT_SAFETY_BUFFER = Decimal("1.0")


def _init_state_for_api(account: AccountId) -> None:
    """
    Ensure we have a LocalBalance + LocalTxLog for the given account.
    """
    if account in _LOCAL_BALANCES:
        return

    _LOCAL_BALANCES[account] = LocalBalance(
        account=account,
        global_confirmed_pho=str(_DEFAULT_GLOBAL_CONFIRMED),
        local_net_delta_pho="0",
        offline_credit_limit_pho=str(_DEFAULT_OFFLINE_LIMIT),
        safety_buffer_pho=str(_DEFAULT_SAFETY_BUFFER),
    )
    _LOCAL_LOGS[account] = LocalTxLog(
        account=account,
        entries=[],
        last_seq=0,
    )


def get_or_init_local_state_for_api(
    account: AccountId,
) -> Tuple[LocalBalance, LocalTxLog]:
    """
    Public helper for API routes:
      - creates a demo LocalBalance/LocalTxLog if missing
      - returns live references (mutations are shared)
    """
    _init_state_for_api(account)
    return _LOCAL_BALANCES[account], _LOCAL_LOGS[account]


def _effective_spendable(local: LocalBalance) -> Decimal:
    """
    Simple effective spendable used by dev-only API:

      global_confirmed
      + local_net_delta
      + offline_limit
      - safety_buffer
    """
    g = Decimal(local["global_confirmed_pho"])
    d = Decimal(local["local_net_delta_pho"])
    lim = Decimal(local["offline_credit_limit_pho"])
    buf = Decimal(local["safety_buffer_pho"])
    return g + d + lim - buf


def record_local_send_for_api(
    *,
    from_account: AccountId,
    to_account: AccountId,
    amount_pho: str,
    cluster_id: ClusterId = "cluster_demo",
    sender_device_id: DeviceId = "dev-mesh-api",
    sender_signature: str = "sig-api",
) -> Tuple[LocalBalance, LocalTxLog, MeshTx]:
    """
    Records an offline mesh send for the given account (dev/demo path).

    - Enforces a simple credit check using _effective_spendable
    - Appends a MeshTx to the local log
    - Updates LocalBalance.local_net_delta_pho
    """
    local_balance, local_log = get_or_init_local_state_for_api(from_account)

    amt = Decimal(amount_pho)
    if amt <= 0:
        raise ValueError("amount_pho must be positive")

    spendable = _effective_spendable(local_balance)
    if amt > spendable:
        raise ValueError(
            f"Insufficient mesh credit; spendable={spendable}, tried={amt}"
        )

    prev_seq = local_log["last_seq"]

    tx = new_mesh_tx(
        cluster_id=cluster_id,
        from_account=from_account,
        to_account=to_account,
        amount_pho=str(amt),
        prev_local_seq=prev_seq,
        sender_device_id=sender_device_id,
        sender_signature=sender_signature,
    )

    # update log
    local_log["entries"].append(tx)
    local_log["last_seq"] = prev_seq + 1

    # update balance: spending → more negative local_net_delta_pho
    delta = Decimal(local_balance["local_net_delta_pho"])
    local_balance["local_net_delta_pho"] = str(delta - amt)

    return local_balance, local_log, tx


def get_local_wallet_view(account: AccountId) -> Dict[str, Any]:
    """
    Convenience helper for APIs that want a single JSON-friendly view:
      - local_balance
      - tx_log
      - mesh_pending_pho = max(0, -local_net_delta_pho)
    """
    local_balance, local_log = get_or_init_local_state_for_api(account)

    try:
        delta = Decimal(local_balance["local_net_delta_pho"])
        pending = max(Decimal("0"), -delta)
    except Exception:
        pending = Decimal("0")

    return {
        "account": account,
        "local_balance": local_balance,
        "tx_log": local_log,
        "mesh_pending_pho": str(pending),
    }