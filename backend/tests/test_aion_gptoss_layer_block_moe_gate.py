from backend.scripts.run_aion_gptoss_layer_block_moe_gate import union_schedule


def test_union_schedule_is_deterministic_and_unique() -> None:
    tokens = [{"layers": [{"route": [7, 2, 9, 1]}]},
              {"layers": [{"route": [9, 3, 7, 4]}]}]
    assert union_schedule(tokens, 0) == [1, 2, 3, 4, 7, 9]
