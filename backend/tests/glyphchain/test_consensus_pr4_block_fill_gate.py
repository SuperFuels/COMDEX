import os
import time
import pytest

import pytest
pytestmark = [pytest.mark.integration, pytest.mark.glyphchain]

@pytest.mark.asyncio
async def test_pr4_block_fill_import_replay_makes_blocks_available(tmp_path, monkeypatch):
    """
    Gate:
      - simulate peer-supplied blocks (same shape returned by /api/p2p/block_req)
      - import them via ConsensusEngine._import_block_into_chain_sim_db
      - replay_state_from_db()
      - assert get_block(h) becomes non-None
    """

    # isolate chain_sim DB for this test
    db_path = tmp_path / "chain_sim.sqlite3"
    monkeypatch.setenv("CHAIN_SIM_PERSIST", "1")
    monkeypatch.setenv("CHAIN_SIM_DB_PATH", str(db_path))

    from backend.modules.chain_sim.chain_sim_ledger import reset_ledger, get_block, replay_state_from_db
    reset_ledger(clear_persist=True)

    # engine (only using import helpers)
    from backend.modules.consensus.engine import ConsensusEngine
    eng = ConsensusEngine()

    # synthetic blocks matching p2p /block_req shape: {"height","created_at_ms","header","txs",...}
    def mk_block(h: int) -> dict:
        now = int(time.time() * 1000)
        tx = {
            "tx_id": f"tx_{h:04d}",
            "tx_hash": f"{h:064x}",  # deterministic-ish
            "block_height": h,
            "tx_index": 0,
            "from_addr": "addr1",
            "nonce": h,
            "tx_type": "BANK_SEND",
            "payload": {"to": "addr2", "amount": "1", "denom": "uglyph"},
            "applied": True,
            "result": {"ok": True},
            "fee": None,
        }
        return {
            "height": h,
            "created_at_ms": now,
            "header": {"txs_root": "", "state_root": ""},  # ok if empty; commit path is best-effort
            "txs_root": "",
            "state_root": "",
            "txs": [tx],
        }

    # import a small range
    for h in range(1, 6):
        ok = eng._import_block_into_chain_sim_db(mk_block(h))  # type: ignore[attr-defined]
        assert ok is True

    # replay and verify visibility
    replay_state_from_db()

    for h in range(1, 6):
        b = get_block(h)
        assert b is not None, f"expected get_block({h}) to exist after import+replay"
        assert int(b.get("height") or 0) == h