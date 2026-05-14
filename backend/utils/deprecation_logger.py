"""
Deprecation Logger
------------------
Captures all DeprecationWarnings and logs them to a file.
"""

import os
import warnings
import datetime

LOG_PATH = os.path.join(os.path.dirname(__file__), "deprecation_warnings.log")


def log_deprecation(message: str):
    """Append deprecation warnings to a log file with timestamp."""
    ts = datetime.datetime.now(datetime.timezone.utc).isoformat().replace("+00:00", "Z")
    try:
        with open(LOG_PATH, "a", encoding="utf-8") as f:
            f.write(f"[{ts}] {message}\n")
    except Exception:
        # fail-safe: never crash on logging
        pass


def install_deprecation_hook():
    """Redirect all DeprecationWarnings to log file as well as stderr."""
    def _hook(message, category, filename, lineno, file=None, line=None):
        msg = warnings.formatwarning(message, category, filename, lineno, line)
        log_deprecation(msg)
        # still print to stderr/pytest
        try:
            if file is None:
                file = os.sys.stderr
            file.write(msg)
        except Exception:
            pass

    warnings.showwarning = _hook