"""
Deprecation Logger
------------------
Captures all DeprecationWarnings and logs them to a file.
"""

import warnings
from pathlib import Path

from backend.modules.aion_business.runtime.content_free_diagnostics import (
    append_diagnostic_event,
    default_node_diagnostics_root,
    fingerprint,
)

LOG_PATH = default_node_diagnostics_root() / "deprecation-events.jsonl"


def log_deprecation(
    message: str,
    *,
    category: type[Warning] | str = DeprecationWarning,
    filename: str = "",
    lineno: int = 0,
    log_path: str | Path | None = None,
):
    """Append a content-free warning event outside the application boundary."""
    try:
        category_name = (
            category.__name__ if isinstance(category, type) else str(category)
        )
        return append_diagnostic_event(
            log_path or LOG_PATH,
            event_type="deprecation_warning",
            code=category_name,
            source_fingerprint=fingerprint(filename),
            detail_fingerprint=fingerprint(message),
            line=lineno,
        )
    except Exception:
        # fail-safe: never crash on logging
        return None


def install_deprecation_hook():
    """Redirect all DeprecationWarnings to log file as well as stderr."""
    def _hook(message, category, filename, lineno, file=None, line=None):
        msg = warnings.formatwarning(message, category, filename, lineno, line)
        log_deprecation(
            str(message), category=category, filename=filename, lineno=lineno
        )
        # still print to stderr/pytest
        try:
            if file is None:
                file = os.sys.stderr
            file.write(msg)
        except Exception:
            pass

    warnings.showwarning = _hook
