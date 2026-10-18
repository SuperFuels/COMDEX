from __future__ import annotations

import sqlite3

import pytest

from backend.modules.chain_sim.ledger_content_policy import (
    LedgerContentPolicyError,
    assert_public_transaction_result,
    normalize_public_transaction_payload,
)


def test_bank_payload_is_exact_and_canonical():
    assert normalize_public_transaction_payload(
        "BANK_SEND", {"denom": "PHO", "to": "pho1-recipient", "amount": 12}
    ) == {"denom": "PHO", "to": "pho1-recipient", "amount": "12"}


@pytest.mark.parametrize(
    "private_field",
    ["customer_name", "email", "notes", "invoice", "document_text"],
)
def test_private_or_extra_payload_fields_fail_closed(private_field: str):
    payload = {
        "denom": "PHO",
        "to": "pho1-recipient",
        "amount": "12",
        private_field: "customer@example.test",
    }
    with pytest.raises(LedgerContentPolicyError, match="unsupported transaction payload fields"):
        normalize_public_transaction_payload("BANK_SEND", payload)


def test_free_form_or_personal_result_fails_closed():
    with pytest.raises(LedgerContentPolicyError, match="private result field"):
        assert_public_transaction_result({"ok": True, "customer_name": "Private Customer"})
    with pytest.raises(LedgerContentPolicyError, match="personal text"):
        assert_public_transaction_result({"error": "contact private@example.test"})


def test_executor_rejects_private_payload_before_state_mutation():
    from backend.modules.chain_sim import chain_sim_model as bank
    from backend.modules.chain_sim.tx_executor import apply_tx_receipt
    from backend.modules.chain_sim.tx_models import TxEnvelope

    bank.reset_state()
    sender = bank.get_or_create_account("pho1-sender")
    sender.balances["PHO"] = "100"
    before = dict(sender.balances)

    receipt = apply_tx_receipt(
        TxEnvelope(
            from_addr="pho1-sender",
            nonce=1,
            tx_type="BANK_TRANSFER",
            payload={
                "denom": "PHO",
                "to": "pho1-recipient",
                "amount": "1",
                "customer_name": "Private Customer",
            },
        )
    )

    assert receipt["applied"] is False
    assert receipt["result"]["policy_rejected"] is True
    assert dict(sender.balances) == before


def test_persistence_rejects_private_payload_before_sqlite_write(tmp_path, monkeypatch):
    from backend.modules.chain_sim import chain_sim_ledger as ledger

    database = tmp_path / "external-vault" / "chain.sqlite3"
    monkeypatch.setenv("CHAIN_SIM_PERSIST", "1")
    monkeypatch.setenv("CHAIN_SIM_DB_PATH", str(database))
    ledger.reset_ledger()

    row = {
        "tx_id": "tx_private",
        "tx_hash": "a" * 64,
        "block_height": 1,
        "tx_index": 0,
        "from_addr": "pho1-sender",
        "nonce": 1,
        "tx_type": "BANK_SEND",
        "payload": {
            "denom": "PHO",
            "to": "pho1-recipient",
            "amount": "1",
            "notes": "Private customer instructions",
        },
        "applied": True,
        "result": {"ok": True},
    }
    with pytest.raises(LedgerContentPolicyError):
        ledger.persist_tx_row(row)

    with sqlite3.connect(database) as connection:
        assert connection.execute("SELECT COUNT(*) FROM txs").fetchone()[0] == 0
