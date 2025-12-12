# backend/dev/dev_gma_state_smoketest.py

from __future__ import annotations

from pprint import pprint

from backend.modules.gma.gma_state_model import (
    new_dev_gma_state,
    GMAState,
)


def print_banner(title: str) -> None:
    print("\n" + "=" * 72)
    print(title)
    print("=" * 72)


def show_snapshot(label: str, s: GMAState) -> None:
    print_banner(label)
    snap = s.snapshot_dict()
    pprint(snap)


def main() -> None:
    print("Running dev_gma_state_smoketest\n")

    # 1) Start from the default dev GMA state
    s = new_dev_gma_state()
    show_snapshot("Initial GMAState", s)

    # 2) Try extending offline credit within the soft cap
    print_banner("Extend offline credit: +3000 PHO (should succeed)")
    can_3k = s.can_extend_offline_credit("3000")
    print(f"can_extend_offline_credit(3000) = {can_3k}")
    if can_3k:
        s.extend_offline_credit("3000")
    show_snapshot("After extending +3000 offline credit", s)

    # 3) Try extending beyond the soft cap, expect a failure
    print_banner("Extend offline credit: +7000 PHO (should hit soft cap)")
    can_7k = s.can_extend_offline_credit("7000")
    print(f"can_extend_offline_credit(7000) = {can_7k}")
    try:
        s.extend_offline_credit("7000")
        print("WARN: extend_offline_credit(7000) unexpectedly succeeded")
    except RuntimeError as e:
        print(f"Expected failure extending +7000 offline credit: {e!s}")

    show_snapshot("After attempted +7000 offline credit", s)

    # 4) Simulate a small PHO mint by GMA (e.g. reserve deposit)
    print_banner("Mint 100 PHO via gma_mint_photon (reserves unchanged)")
    s.gma_mint_photon("100", reason="dev_test_mint")
    show_snapshot("After gma_mint_photon(100)", s)

    # 5) Realise some offline losses (e.g. bad mesh debt)
    print_banner("Realise 500 PHO of offline losses")
    s.realise_offline_losses("500")
    show_snapshot("After realise_offline_losses(500)", s)

    print("\nSmoketest complete.\n")


if __name__ == "__main__":
    main()