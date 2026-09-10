from backend.scripts.run_aion_gptoss_route_cartridge_gate import (
    compile_cartridge,
    evaluate,
)


def test_byte_budget_is_strict_and_frequency_driven() -> None:
    sizes = {(0, 1): 10, (0, 2): 10, (0, 3): 10}
    tokens = [
        [[1, 2, 3, 1]],
        [[1, 2, 1, 3]],
    ]
    selected = compile_cartridge(tokens, sizes, 20)
    assert selected == {(0, 1), (0, 2)}
    assert sum(sizes[key] for key in selected) <= 20


def test_evaluation_counts_access_and_compressed_bytes() -> None:
    selected = {(0, 1), (0, 2)}
    compressed = {(0, 1): 4, (0, 2): 5, (0, 3): 7, (0, 4): 8}
    raw = {key: 10 for key in compressed}
    result = evaluate([[[1, 2, 3, 4]]], selected, compressed, raw)
    assert result["accesses"] == 4
    assert result["hits"] == 2
    assert result["route_coverage"] == 0.5
    assert result["missed_compressed_bytes"] == 15
    assert result["total_unretained_compressed_bytes"] == 24
    assert result["resident_raw_bytes"] == 20
