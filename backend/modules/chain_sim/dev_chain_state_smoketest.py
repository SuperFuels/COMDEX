from __future__ import annotations

import json
import os
import sys
import urllib.request
from typing import Any, Dict


def _base() -> str:
    # You export CHAIN_SIM_BASE_URL like "http://127.0.0.1:8080"
    b = os.getenv("CHAIN_SIM_BASE_URL", "http://127.0.0.1:8080").rstrip("/")
    # Our API routes are under /api
    return f"{b}/api"


def _stable_json(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _get(path: str) -> Dict[str, Any]:
    url = _base() + path
    with urllib.request.urlopen(url, timeout=10) as resp:
        raw = resp.read().decode("utf-8")
    return json.loads(raw) if raw else {}


def _post(path: str, body: Dict[str, Any]) -> Dict[str, Any]:
    url = _base() + path
    data = _stable_json(body).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=20) as resp:
        raw = resp.read().decode("utf-8")
    return json.loads(raw) if raw else {}


def main() -> None:
    print("▶ dev_chain_state_smoketest: starting")

    # 1) Reset + apply a tiny genesis so state is non-trivial
    genesis = {
        "chain_id": "comdex-dev",
        "network_id": "local",
        "allocs": [
            {"address": "pho1-alice", "balances": {"PHO": "100", "TESS": "50"}},
            {"address": "pho1-val-1", "balances": {"TESS": "10"}},
        ],
        "validators": [
            {"address": "pho1-val-1", "self_delegation_tess": "10", "commission": "0"},
        ],
    }
    r = _post("/chain_sim/dev/reset", genesis)
    assert r.get("ok") is True, f"reset failed: {r}"

    # 2) Ledger should be empty after reset+apply (genesis is NOT tx submission)
    blocks = _get("/chain_sim/dev/blocks?limit=1&offset=0")
    assert blocks.get("ok") is True
    assert blocks.get("blocks") == [], f"expected empty blocks, got: {blocks}"

    # 3) Export state
    s1 = _get("/chain_sim/dev/state")
    assert s1.get("ok") is True, f"state export failed: {s1}"
    root1 = s1.get("state_root")
    assert isinstance(root1, str) and len(root1) >= 16

    # 4) Import the exact snapshot we just exported
    # Accepts either {"state": {...}} or the whole wrapper; we send wrapper (what curl saved)
    post_out = _post("/chain_sim/dev/state", s1)
    assert post_out.get("ok") is True, f"state import failed: {post_out}"
    root_post = post_out.get("state_root")
    assert isinstance(root_post, str)

    # 5) Export again; state_root must be stable now
    s2 = _get("/chain_sim/dev/state")
    assert s2.get("ok") is True, f"state export 2 failed: {s2}"
    root2 = s2.get("state_root")

    assert root1 == root2, f"state_root changed: {root1} -> {root2}"

    # Optional: also ensure the actual state payload is identical after roundtrip
    st1 = s1.get("state")
    st2 = s2.get("state")
    assert _stable_json(st1) == _stable_json(st2), "state payload changed after import/export"

    print("✅ dev_chain_state_smoketest: all assertions passed")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"❌ dev_chain_state_smoketest: failed: {e}", file=sys.stderr)
        raise