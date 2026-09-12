from __future__ import annotations

import pytest
import numpy as np

from backend.scripts.run_aion_gptoss_first_token_gate import (
    local_c4_similarity,
    local_c4_prediction,
    local_c4_region_supported,
    parse_layer_spec,
    parse_optional_layer_spec,
    router_boundary_diagnostic,
)


def test_local_c4_secant_is_gate_scaled_and_anchor_exact() -> None:
    cartridge = {'training_gate': np.float32(0.25),
                 'contribution': np.asarray([2.0, 3.0], dtype=np.float32),
                 'activation_anchor': np.zeros(2, dtype=np.float32),
                 'secant_dual': np.asarray([0.5, 0.0], dtype=np.float32),
                 'secant_response': np.asarray([4.0, 5.0], dtype=np.float32)}
    assert np.array_equal(local_c4_prediction(np.zeros(2, dtype=np.float32), 0.25, cartridge), [2, 3])
    assert np.array_equal(local_c4_prediction(np.asarray([2, 0], dtype=np.float32), 0.5, cartridge), [12, 16])
    del cartridge['secant_response']
    assert np.array_equal(local_c4_prediction(np.zeros(2, dtype=np.float32), 0.5, cartridge), [4, 6])


def test_local_c4_secant_rejects_extrapolation() -> None:
    cartridge = {'activation_anchor': np.zeros(2, dtype=np.float32),
                 'secant_dual': np.asarray([0.5, 0], dtype=np.float32),
                 'secant_response': np.ones(2, dtype=np.float32)}
    assert local_c4_region_supported(np.asarray([1, 0], dtype=np.float32), cartridge)
    assert not local_c4_region_supported(np.asarray([3, 0], dtype=np.float32), cartridge)
    assert not local_c4_region_supported(np.asarray([-1, 0], dtype=np.float32), cartridge)


def test_router_boundary_diagnostic_retains_exact_admission_margin() -> None:
    scores = np.arange(128, dtype=np.float32)
    result = router_boundary_diagnostic(scores)
    assert result['unrestricted_top_five'] == [127, 126, 125, 124, 123]
    assert result['fourth_fifth_margin'] == 1.0
    scores[123] = scores[124]
    assert router_boundary_diagnostic(scores)['fourth_fifth_margin'] == 0.0


def test_router_boundary_diagnostic_rejects_bad_scores() -> None:
    with pytest.raises(ValueError):
        router_boundary_diagnostic(np.zeros(127))
    with pytest.raises(ValueError):
        router_boundary_diagnostic(np.full(128, np.nan))


def test_local_c4_similarity_averages_router_and_ffn_cosines() -> None:
    cartridge = {
        "router_unit": np.asarray([1.0, 0.0], dtype=np.float32),
        "ffn_unit": np.asarray([0.0, 1.0], dtype=np.float32),
    }
    assert local_c4_similarity(
        np.asarray([2.0, 0.0], dtype=np.float32),
        np.asarray([0.0, 3.0], dtype=np.float32),
        cartridge,
    ) == pytest.approx(1.0)


def test_adaptive_default_still_selects_every_layer() -> None:
    assert parse_layer_spec(None) == set(range(36))


def test_absent_optional_diagnostic_selects_no_layers() -> None:
    assert parse_optional_layer_spec(None) == set()
    assert parse_optional_layer_spec("") == set()


def test_optional_layer_ranges_are_bounded_and_inclusive() -> None:
    assert parse_optional_layer_spec("0,28-35") == {0, *range(28, 36)}
    with pytest.raises(ValueError):
        parse_optional_layer_spec("35-36")
