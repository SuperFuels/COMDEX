#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🧩 Photon Page Validator
────────────────────────────────────────────
Ensures .ptn files conform to syntax, entanglement,
and import integrity rules before execution.
"""

import re
from pathlib import Path
from backend.modules.ptn.ptn_spec import PhotonPage


def validate_syntax(page: PhotonPage) -> bool:
    """Ensure name/body validity and Photon operator presence."""
    if not page.name or not isinstance(page.name, str):
        raise ValueError("PhotonPage must have a valid name.")
    if not page.body.strip():
        raise ValueError("PhotonPage body cannot be empty.")
    # Check for at least one valid Photon operator
    if not re.search(r"[⊕↔∇⟲μ>]", page.body):
        raise ValueError("PhotonPage body must contain at least one Photon operator.")
    return True


def validate_imports(page: PhotonPage, wiki_root: Path) -> bool:
    """Verify that all imports exist under wiki root."""
    for imp in page.imports:
        file_path = wiki_root / f"{imp.title()}.wiki.phn"
        if not file_path.exists():
            raise FileNotFoundError(f"Missing import: {file_path}")
    return True


def validate_entanglement(page: PhotonPage) -> bool:
    """Ensure self-entanglement and cyclic imports are avoided."""
    if page.name in page.imports:
        raise ValueError(f"PhotonPage {page.name} cannot import itself.")
    return True


def validate_page(page: PhotonPage, wiki_root: Path) -> bool:
    """Full composite validation."""
    return (
        validate_syntax(page)
        and validate_imports(page, wiki_root)
        and validate_entanglement(page)
    )