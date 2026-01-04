from __future__ import annotations

from backend.utils.warn_gate import apply_test_quiet_warning_filters

def pytest_configure(config):
    apply_test_quiet_warning_filters()
