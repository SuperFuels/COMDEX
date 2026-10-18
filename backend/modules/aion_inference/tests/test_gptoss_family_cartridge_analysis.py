from backend.scripts.analyze_aion_gptoss_family_cartridges import (
    select_within_budget,
    simulate,
)


def test_budget_selection_never_exceeds_limit():
    sizes = {(0, 0): 4, (0, 1): 7, (0, 2): 3}
    selected = select_within_budget([(0, 0), (0, 1), (0, 2)], sizes, 8)
    assert selected == {(0, 0), (0, 2)}
    assert sum(sizes[key] for key in selected) <= 8


def test_fixed_cartridge_and_lru_halo_account_exact_misses():
    sizes = {(0, expert): 10 for expert in range(4)}
    accesses = [(0, 0), (0, 1), (0, 2), (0, 1), (0, 3), (0, 2)]
    result = simulate(accesses, sizes, {(0, 0)}, 20)
    assert result["accesses"] == 6
    assert result["hits"] == 2
    assert result["misses"] == 4
    assert result["miss_raw_bytes"] == 40
