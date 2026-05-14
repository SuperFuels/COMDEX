import json
import sqlite3

import pytest


def _stable_json(obj) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _tamper_checkpoint(db_path: str, *, new_state_root: str) -> None:
    con = sqlite3.connect(db_path)
    try:
        cur = con.cursor()
        cur.execute("SELECT value FROM meta WHERE key=?", ("checkpoint_json",))
        row = cur.fetchone()
        assert row and row[0], "checkpoint row missing before tamper"

        ck = json.loads(row[0])
        ck["last_state_root"] = new_state_root

        cur.execute(
            "UPDATE meta SET value=? WHERE key=?",
            (_stable_json(ck), "checkpoint_json"),
        )
        con.commit()
    finally:
        con.close()


def _delete_checkpoint(db_path: str) -> None:
    con = sqlite3.connect(db_path)
    try:
        cur = con.cursor()
        cur.execute("DELETE FROM meta WHERE key=?", ("checkpoint_json",))
        con.commit()
    finally:
        con.close()


@pytest.mark.asyncio
async def test_replay_strict_fails_on_tampered_checkpoint(tmp_path, monkeypatch):
    db_path = str(tmp_path / "chain_sim.sqlite3")

    monkeypatch.setenv("CHAIN_SIM_DB_PATH", db_path)
    monkeypatch.setenv("CHAIN_SIM_PERSIST", "1")
    monkeypatch.setenv("CHAIN_SIM_REPLAY_ON_STARTUP", "1")

    # build a real checkpoint first (non-strict)
    monkeypatch.setenv("CHAIN_SIM_REPLAY_STRICT", "0")

    from backend.modules.chain_sim import chain_sim_ledger as ledger
    from backend.modules.chain_sim import chain_sim_routes as routes
    from backend.modules.chain_sim.tx_executor import apply_tx_receipt as apply_tx

    # reset cached sqlite connection for this test DB
    ledger._DB_CONN = None
    ledger._DB_CONN_PATH = None

    ledger.persist_clear_all()

    # persist genesis snapshot so replay_startup has something to import
    try:
        genesis = routes._get_chain_state_snapshot()
    except Exception:
        genesis = {}
    if not isinstance(genesis, dict):
        genesis = {}
    genesis.setdefault("config", {"chain_id": "glyphchain-dev", "network_id": "dev"})
    genesis.setdefault("bank", {})
    genesis.setdefault("staking", {})
    ledger.persist_set_genesis_state(genesis)

    # create 1 applied tx + commit a block with correct state_root so checkpoint is valid
    class _AttrDict(dict):
        def __getattr__(self, k):
            return self[k]

    ledger.begin_block()

    # try a few common tx types; fail loudly if none apply in your executor
    candidates = [
        ("BANK_MINT", {"to": "addr_test_1", "denom": "uglyph", "amount": "1"}),
        ("BANK_FAUCET", {"to": "addr_test_1", "denom": "uglyph", "amount": "1"}),
        ("BANK_SEND", {"to": "addr_test_1", "denom": "uglyph", "amount": "0"}),
        ("BANK_BURN", {"denom": "uglyph", "amount": "0"}),
    ]

    applied_ok = False
    last_result = {}
    last_fee = None
    tx_type_used = ""
    payload_used = {}

    for tx_type, payload in candidates:
        tx_obj = _AttrDict(
            {"from_addr": "addr_test_0", "nonce": 1, "tx_type": tx_type, "payload": payload}
        )
        receipt = apply_tx(tx_obj)
        if not isinstance(receipt, dict):
            receipt = {"ok": True, "result": receipt}

        result = receipt.get("result") or {}
        applied = receipt.get("applied", None)
        if applied is None:
            if isinstance(result, dict) and "ok" in result:
                applied = bool(result.get("ok"))
            else:
                applied = True

        if bool(applied):
            applied_ok = True
            tx_type_used = tx_type
            payload_used = payload
            last_result = result if isinstance(result, dict) else {}
            if isinstance(last_result, dict):
                maybe_fee = last_result.get("fee")
                last_fee = maybe_fee if isinstance(maybe_fee, dict) else None
            break

    assert applied_ok, "Could not apply any candidate tx type; update candidates to match your executor"

    ledger.record_applied_tx(
        from_addr="addr_test_0",
        nonce=1,
        tx_type=tx_type_used,
        payload=payload_used,
        applied=True,
        result=last_result,
        fee=last_fee,
    )

    # compute state_root from *current* in-memory state (must match replay computation)
    state_root = routes._compute_state_root(routes._get_chain_state_snapshot())
    ledger.commit_block(header_patch={"state_root": state_root})

    ck = ledger.persist_get_checkpoint()
    assert isinstance(ck, dict) and int(ck.get("last_height") or 0) > 0

    # tamper checkpoint in sqlite
    _tamper_checkpoint(db_path, new_state_root="00" * 32)

    # simulate restart by dropping cached connection
    ledger._DB_CONN = None
    ledger._DB_CONN_PATH = None

    # now strict replay must fail loudly
    monkeypatch.setenv("CHAIN_SIM_REPLAY_STRICT", "1")
    with pytest.raises(RuntimeError):
        await routes.chain_sim_replay_startup()


@pytest.mark.asyncio
async def test_replay_strict_fails_on_missing_checkpoint(tmp_path, monkeypatch):
    db_path = str(tmp_path / "chain_sim.sqlite3")

    monkeypatch.setenv("CHAIN_SIM_DB_PATH", db_path)
    monkeypatch.setenv("CHAIN_SIM_PERSIST", "1")
    monkeypatch.setenv("CHAIN_SIM_REPLAY_ON_STARTUP", "1")
    monkeypatch.setenv("CHAIN_SIM_REPLAY_STRICT", "0")

    from backend.modules.chain_sim import chain_sim_ledger as ledger
    from backend.modules.chain_sim import chain_sim_routes as routes

    ledger._DB_CONN = None
    ledger._DB_CONN_PATH = None

    ledger.persist_clear_all()
    ledger.persist_set_genesis_state(
        {"config": {"chain_id": "glyphchain-dev", "network_id": "dev"}, "bank": {}, "staking": {}}
    )

    # create a fake checkpoint row then delete it (ensures the "missing checkpoint" path is exercised)
    ledger.persist_set_checkpoint(last_height=1, last_state_root="11" * 32, last_txs_root="22" * 32)
    _delete_checkpoint(db_path)

    ledger._DB_CONN = None
    ledger._DB_CONN_PATH = None

    monkeypatch.setenv("CHAIN_SIM_REPLAY_STRICT", "1")
    with pytest.raises(RuntimeError):
        await routes.chain_sim_replay_startup()