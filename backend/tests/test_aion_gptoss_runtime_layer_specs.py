from __future__ import annotations

import pytest

from backend.scripts.run_aion_gptoss_first_token_gate import (
    parse_layer_spec,
    parse_optional_layer_spec,
)


def test_adaptive_default_still_selects_every_layer() -> None:
    assert parse_layer_spec(None) == set(range(36))


def test_absent_optional_diagnostic_selects_no_layers() -> None:
    assert parse_optional_layer_spec(None) == set()
    assert parse_optional_layer_spec("") == set()


def test_optional_layer_ranges_are_bounded_and_inclusive() -> None:
    assert parse_optional_layer_spec("0,28-35") == {0, *range(28, 36)}
    with pytest.raises(ValueError):
        parse_optional_layer_spec("35-36")
