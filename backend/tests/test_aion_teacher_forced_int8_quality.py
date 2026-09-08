import torch

from backend.scripts.run_forced_int8_quality import _quality_metrics


def test_quality_metrics_are_exact_for_equal_logits() -> None:
    logits = torch.tensor([[1.0, 3.0, 2.0, 0.0, -1.0],
                           [4.0, 2.0, 1.0, 0.0, -2.0]])
    result = _quality_metrics(logits, logits.clone(), [1, 0])
    assert result["top1_agreement_fraction"] == 1.0
    assert result["mean_kl_divergence_nats"] == 0.0
    assert result["mean_control_token_nll_delta_nats"] == 0.0
