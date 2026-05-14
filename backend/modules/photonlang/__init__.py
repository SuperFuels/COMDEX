# backend/modules/photonlang/__init__.py
from __future__ import annotations
import os, sys

# Public adapters
try:
    from .adapters.python_tokens import (
        compress_text_py,
        expand_text_py,
        contains_code_glyphs,
        normalize_roundtrip,
    )
except Exception:
    # Soft fallbacks so importing this package never explodes
    def compress_text_py(s: str) -> str: return s
    def expand_text_py(s: str) -> str: return s
    def contains_code_glyphs(s: str) -> bool: return False
    def normalize_roundtrip(s: str) -> str: return s

# Importer control
from .importer import (
    register_photon_importer as _register,
    unregister_photon_importer as _unregister,
)

__version__ = "0.1.0+local"

def install() -> bool:
    """Install the Photon FileFinder hook (idempotent)."""
    return bool(_register())

def uninstall() -> bool:
    """Remove the Photon FileFinder hook."""
    return bool(_unregister())

def is_installed() -> bool:
    """True if our FileFinder path hook is present."""
    return any(getattr(h, "_tessaris_photon_hook", False) for h in sys.path_hooks)

# Optional: allow env opt-in auto-install without crashing
_auto = os.getenv("PHOTON_AUTO_INSTALL", "").strip().lower()
if _auto not in {"", "0", "false", "no"}:
    try:
        install()
    except Exception as e:
        # Don’t kill importers; just warn
        sys.stderr.write(f"[photonlang] auto-install failed: {e}\n")

__all__ = [
    "compress_text_py", "expand_text_py", "contains_code_glyphs", "normalize_roundtrip",
    "install", "uninstall", "is_installed", "__version__",
]