# backend/dev/dev_gma_reserve_smoketest.py

from __future__ import annotations

from decimal import Decimal
from pprint import pprint

from backend.modules.gma import gma_state_model as gma_state_model
from backend.modules.gma.gma_state_model import GMAState


def _new_demo_state() -> GMAState:
    """
    Reuse the same demo factory as other GMA dev tools.

    Supports either:
      - make_demo_gma_state()
      - make_demo_state()
    """
    factory = getattr(gma_state_model, "make_demo_gma_state", None)
    if factory is None:
        factory = getattr(gma_state_model, "make_demo_state", None)

    if factory is None:
        raise RuntimeError(
            "No demo factory found in gma_state_model "
            "(expected make_demo_gma_state() or make_demo_state())."
        )

    return factory()


def dump(label: str, state: GMAState) -> None:
    print()
    print("=" * 72)
    print(label)
    print("=" * 72)
    pprint(state.snapshot_dict())


def main() -> None:
    print("Running dev_gma_reserve_smoketest")
    state = _new_demo_state()

    dump("Initial GMAState", state)

    # ------------------------------------------------------------------
    # 1) Simple reserve-backed deposit: +2000 PHO of USD_BANK_X
    # ------------------------------------------------------------------
    print()
    print("=" * 72)
    print("Reserve deposit: +2000 PHO into USD_BANK_X (should raise PHO supply)")
    print("=" * 72)
    state.record_reserve_deposit("USD_BANK_X", Decimal("2000"))
    dump("After record_reserve_deposit(USD_BANK_X, 2000)", state)

    # ------------------------------------------------------------------
    # 2) Valid redemption: burn 500 PHO, release matching reserves
    # ------------------------------------------------------------------
    print()
    print("=" * 72)
    print("Reserve redemption: 500 PHO from USD_BANK_X (should shrink reserves + supply)")
    print("=" * 72)
    state.record_reserve_redemption("USD_BANK_X", Decimal("500"))
    dump("After record_reserve_redemption(USD_BANK_X, 500)", state)

    # ------------------------------------------------------------------
    # 3) Redemption too large for available reserves → should fail cleanly
    # ------------------------------------------------------------------
    print()
    print("=" * 72)
    print("Attempt over-redemption: huge PHO amount (expect failure)")
    print("=" * 72)
    try:
        state.record_reserve_redemption("USD_BANK_X", Decimal("10_000_000"))
        print("⚠️ Unexpected success (BUG) – redemption should have failed.")
    except Exception as e:
        print(f"Expected failure: {e!r}")

    dump("Final GMAState after failed over-redemption attempt", state)

    print()
    print("Smoketest complete.")


if __name__ == "__main__":
    main()