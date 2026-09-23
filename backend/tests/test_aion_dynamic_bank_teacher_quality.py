import pytest

from backend.scripts.run_aion_dynamic_bank_teacher_quality import (
    _aggregate,
    _control_continuations,
)


def test_aggregate_weights_probability_metrics_by_positions() -> None:
    items = [{"positions": 1, "top1_agreement_count": 1,
              "mean_top5_overlap_fraction": 1.0, "mean_kl_divergence_nats": 0.1,
              "mean_control_token_nll_delta_nats": 0.2, "candidate_seconds": 2.0},
             {"positions": 3, "top1_agreement_count": 0,
              "mean_top5_overlap_fraction": 0.0, "mean_kl_divergence_nats": 0.3,
              "mean_control_token_nll_delta_nats": 0.4, "candidate_seconds": 3.0}]
    result = _aggregate(items)
    assert result["teacher_forced_top1_agreement_fraction"] == 0.25
    assert result["mean_kl_divergence_nats"] == pytest.approx(0.25)
    assert result["total_seconds"] == 5.0


def test_control_continuations_accepts_abba_runs() -> None:
    generation = {"runs": [
        {"family": "alpha", "sequence": 0, "token_ids": [1, 2]},
        {"family": "alpha", "sequence": 1, "token_ids": [3, 4]},
        {"family": "beta", "sequence": 0, "token_ids": [5, 6]},
    ]}
    assert _control_continuations(generation, ["alpha", "beta"]) == {
        "alpha": [1, 2], "beta": [5, 6],
    }


def test_control_continuations_rejects_missing_family() -> None:
    with pytest.raises(ValueError, match="missing families"):
        _control_continuations({"runs": []}, ["alpha"])
