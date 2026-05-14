from __future__ import annotations

from backend.utils.warn_gate import apply_test_quiet_warning_filters


def pytest_configure(config) -> None:
    # When TESSARIS_TEST_QUIET=1, suppress known-noisy warnings in test output.
    apply_test_quiet_warning_filters()