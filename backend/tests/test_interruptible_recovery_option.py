import pytest

from backend.modules.hexcore.interruptible_recovery_option import (
    InterruptibleRecoveryOption,
    RecoveryOptionConfig,
)


def test_requires_sustained_entry_and_reobserves_each_action():
    option = InterruptibleRecoveryOption(
        RecoveryOptionConfig(0.9, 0.5, sustained_observations=2, max_burst_actions=3)
    )
    assert option.decide(0.95)[0] is False
    assert option.decide(0.96) == (True, "interruptible_recovery_enter")
    assert option.decide(0.7) == (True, "interruptible_recovery_continue")
    assert option.decide(0.2) == (False, "recovery_exit_to_nominal")


def test_burst_is_bounded_and_cooldown_protects_nominal_control():
    option = InterruptibleRecoveryOption(
        RecoveryOptionConfig(
            0.8, 0.4, sustained_observations=1, max_burst_actions=2, cooldown_actions=2
        )
    )
    assert option.decide(0.9)[0] is True
    assert option.decide(0.9)[0] is True
    assert option.decide(0.9) == (False, "recovery_exit_to_nominal")
    assert option.decide(0.99) == (False, "recovery_cooldown_nominal")
    assert option.decide(0.99) == (False, "recovery_cooldown_nominal")
    assert option.decide(0.99)[0] is True


def test_invalid_authority_expansion_fails_closed():
    with pytest.raises(ValueError):
        RecoveryOptionConfig(0.4, 0.8)
    with pytest.raises(ValueError):
        RecoveryOptionConfig(0.8, 0.4, max_burst_actions=8)

