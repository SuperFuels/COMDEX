# /workspaces/COMDEX/sitecustomize.py
from __future__ import annotations
import os, sys

if os.getenv("PHOTON_SITE_INSTALL", "").lower() in {"1", "true", "yes"}:
    try:
        from backend.modules.photonlang.importer import install as _install
        _install()
    except Exception as e:
        sys.stderr.write(f"[sitecustomize] photon importer not installed: {e}\n")