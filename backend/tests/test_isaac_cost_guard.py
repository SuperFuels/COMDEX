import pytest

from integrations.isaac_lab.cost_guarded_brev_expedition import budget


def test_cost_guard_reports_bounded_maximum() -> None:
    assert budget(1.74, 45) == {
        "rate_per_hour_usd": 1.74,
        "maximum_minutes": 45,
        "maximum_compute_spend_usd": 1.3,
    }


@pytest.mark.parametrize("rate,minutes", [(0, 45), (1.74, 0), (1.74, 241), (10, 61)])
def test_cost_guard_rejects_invalid_or_excessive_runs(rate: float, minutes: int) -> None:
    with pytest.raises(ValueError):
        budget(rate, minutes)
