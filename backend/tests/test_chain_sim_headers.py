import pytest
from fastapi.testclient import TestClient

from backend.main import app

@pytest.mark.unit
def test_dev_headers_matches_blocks():
    c = TestClient(app)

    genesis = {
        "chain_id": "glyphchain-dev",
        "network_id": "devnet",
        "allocs": [
            {"address": "pho1-dev-val1", "balances": {"PHO": "1000", "TESS": "1000"}},
            {"address": "pho1-dev-val2", "balances": {"PHO": "1000", "TESS": "1000"}},
            {"address": "pho1-dev-user1", "balances": {"PHO": "1000", "TESS": "0"}},
        ],
        "validators": [
            {"address": "pho1-dev-val1", "power": "100", "commission": "0"},
            {"address": "pho1-dev-val2", "power": "100", "commission": "0"},
        ],
    }

    r = c.post("/api/chain_sim/dev/reset", json=genesis)
    assert r.status_code == 200, r.text

    tx = {
        "from_addr": "pho1-dev-user1",
        "nonce": 1,
        "tx_type": "BANK_SEND",
        "payload": {"to": "pho1-dev-val1", "denom": "PHO", "amount": "1"},
    }
    r = c.post("/api/chain_sim/dev/submit_tx", json=tx)
    assert r.status_code == 200, r.text

    blocks = c.get("/api/chain_sim/dev/blocks?limit=1&order=desc").json()["blocks"]
    headers = c.get("/api/chain_sim/dev/headers?limit=1&order=desc").json()["headers"]

    assert len(blocks) == 1
    assert len(headers) == 1

    b0 = blocks[0]
    h0 = headers[0]

    assert h0["height"] == b0["height"]
    assert h0["header"]["state_root"] == b0["header"]["state_root"]
    assert h0["header"]["txs_root"] == b0["header"]["txs_root"]
    assert h0["state_root"] == b0["header"]["state_root"]
    assert h0["txs_root"] == b0["header"]["txs_root"]