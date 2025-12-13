# backend/modules/gma/dev_gma_events_smoketest.py

from __future__ import annotations

import asyncio

from backend.modules.gma.gma_state_dev import (
    record_mint_burn,
    record_reserve_move,
)
from backend.modules.gma.gma_state_routes import (
    gma_state_dev_snapshot,
)


async def run_smoketest() -> None:
    print("▶ dev_gma_events_smoketest: starting")

    # 1) Log some events
    record_mint_burn(kind="MINT", amount_pho="100.0", reason="test_mint")
    record_mint_burn(kind="BURN", amount_pho="25.0", reason="test_burn")

    record_reserve_move(
        kind="ADD",
        amount_pho_eq="50.0",
        reason="test_reserve_add",
    )
    record_reserve_move(
        kind="REMOVE",
        amount_pho_eq="10.0",
        reason="test_reserve_remove",
    )

    # 2) Fetch snapshot via the same function the API route uses
    snapshot = await gma_state_dev_snapshot()

    mint_burn_log = snapshot.get("mint_burn_log") or []
    reserve_moves_log = snapshot.get("reserve_moves_log") or []

    assert any(ev.get("reason") == "test_mint" for ev in mint_burn_log), \
        "test_mint event missing from mint_burn_log"
    assert any(ev.get("reason") == "test_burn" for ev in mint_burn_log), \
        "test_burn event missing from mint_burn_log"

    assert any(ev.get("reason") == "test_reserve_add" for ev in reserve_moves_log), \
        "test_reserve_add event missing from reserve_moves_log"
    assert any(ev.get("reason") == "test_reserve_remove" for ev in reserve_moves_log), \
        "test_reserve_remove event missing from reserve_moves_log"

    print("✅ dev_gma_events_smoketest: all assertions passed")


if __name__ == "__main__":
    asyncio.run(run_smoketest())