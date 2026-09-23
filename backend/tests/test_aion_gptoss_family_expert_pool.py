from backend.scripts.build_aion_gptoss_family_expert_pool import select_pool


def test_select_pool_preserves_floor_then_uses_global_score() -> None:
    sizes = {(layer, expert): 1 for layer in range(36) for expert in range(128)}
    scores = {(layer, expert): float(128 - expert)
              for layer in range(36) for expert in range(128)}
    scores[(7, 127)] = 1000.0
    selected, resident = select_pool(scores, sizes, capacity=145, minimum_per_layer=4)
    assert resident == 145
    assert all(sum(chosen_layer == layer for chosen_layer, _ in selected) >= 4
               for layer in range(36))
    assert (7, 127) in selected


def test_select_pool_rejects_floor_above_capacity() -> None:
    sizes = {(layer, expert): 2 for layer in range(36) for expert in range(128)}
    try:
        select_pool({}, sizes, capacity=287, minimum_per_layer=4)
    except ValueError as error:
        assert "minimum" in str(error)
    else:
        raise AssertionError("impossible floor was accepted")
