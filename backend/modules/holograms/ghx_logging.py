# File: backend/modules/hologram/ghx_logging.py
# Shim: keep old imports working, but delegate to the canonical helper.
from backend.utils.ghx_logging import safe_ghx_log

__all__ = ["safe_ghx_log"]