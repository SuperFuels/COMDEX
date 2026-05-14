from __future__ import annotations

import os
import warnings

def apply_test_quiet_warning_filters() -> None:
    """
    When TESSARIS_TEST_QUIET=1, hide known-noisy warnings during test runs.
    Keep behavior unchanged otherwise.
    """
    if os.getenv("TESSARIS_TEST_QUIET", "") != "1":
        return

    # Deprecation warnings that spam GX1 runs but aren't relevant to GX1 scope.
    warnings.filterwarnings("ignore", category=DeprecationWarning)
