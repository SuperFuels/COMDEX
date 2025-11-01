# -*- coding: utf-8 -*-
from __future__ import annotations
import os

def install() -> None:
    # Importing register installs the path hook (idempotent).
    from backend.modules.photonlang.importer import register_photon_importer
    register_photon_importer()

def uninstall() -> None:
    # Properly remove our path hook and clear caches.
    from backend.modules.photonlang.importer import unregister_photon_importer
    unregister_photon_importer()

# Auto-install via env var for convenience
if os.getenv("PHOTON_IMPORT", "").lower() in {"1", "true", "yes"}:
    install()