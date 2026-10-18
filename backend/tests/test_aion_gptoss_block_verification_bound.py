from backend.scripts.analyze_aion_gptoss_block_verification_bound import analyze


def test_block_bound_counts_each_layer_expert_once() -> None:
    tokens = []
    for position in range(2):
        tokens.append({"layers": [{"route": [1, 2, 3, 4] if position == 0
                                    else [1, 2, 5, 6]} for _ in range(36)]})
    result = analyze(tokens, 2)
    assert result["naive_layer_expert_uses"] == 288
    assert result["layer_major_unique_expert_loads"] == 216
    assert result["ideal_expert_load_traffic_reduction"] == 4 / 3
