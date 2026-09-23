from __future__ import annotations

from backend.scripts.analyze_aion_gptoss_pool_holdout import analyze, canonical_sha256


def _pool() -> dict:
    value = {
        "schema": "aion.gptoss-120b-constrained-expert-pool.v1",
        "quality_track": True,
        "layers": {str(layer): [0, 1, 2, 3] for layer in range(36)},
    }
    value["canonical_sha256"] = canonical_sha256(value)
    return value


def _report() -> dict:
    layer_records = [{
        "layer": layer,
        "route": [0, 1, 7, 8],
        "gates": [0.4, 0.3, 0.2, 0.1],
    } for layer in range(36)]
    return {
        "status": "PASSED",
        "final_hidden_and_logits_bitwise_repeatable": True,
        "run_a": {"tokens": [
            {"layers": layer_records},
            {"layers": layer_records},
        ]},
    }


def test_holdout_metrics_cover_only_resident_experts() -> None:
    metrics = analyze(_pool(), _report(), 1)
    assert metrics["holdout_positions"] == 1
    assert metrics["holdout_layer_routes"] == 36
    assert metrics["complete_layer_routes"] == 0
    assert metrics["mean_missing_experts_per_route"] == 2
    assert abs(metrics["median_retained_gate_mass"] - 0.7) < 1e-12


def test_holdout_rejects_modified_pool() -> None:
    pool = _pool()
    pool["layers"]["0"] = [4, 5, 6, 7]
    try:
        analyze(pool, _report(), 1)
    except ValueError as error:
        assert "hash" in str(error)
    else:
        raise AssertionError("modified pool was accepted")
