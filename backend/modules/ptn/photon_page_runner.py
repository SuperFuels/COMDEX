#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
⚙️ Photon Page Runner
────────────────────────────────────────────
Executes .ptn Photon Pages through the Photon Language engine.
Bridges WikiCapsule layer → PhotonExecutor pipeline.

Usage:
    from backend.modules.ptn.photon_page_runner import run_photon_page
    result = run_photon_page("docs/pages/Harmonic_Resonance.ptn")
"""

import json
import logging
from pathlib import Path
from typing import Optional, Dict, Any

from backend.modules.ptn.ptn_spec import PhotonPage
from backend.modules.ptn.ptn_validator import validate_page
from backend.modules.photon.photon_executor import execute_photon_capsule
from backend.modules.photon.photon_capsule_validator import validate_photon_capsule

logger = logging.getLogger(__name__)


def run_photon_page(path: str, *, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Load, validate, and execute a Photon Page (.ptn)."""
    page_path = Path(path)
    if not page_path.exists():
        raise FileNotFoundError(f"PhotonPage not found: {path}")

    # Load JSON-based Photon Page
    page_data = json.loads(page_path.read_text(encoding="utf-8"))
    page = PhotonPage(
        name=page_data["name"],
        imports=page_data.get("imports", []),
        body=page_data.get("body", ""),
        metadata=page_data.get("metadata", {}),
    )

    wiki_root = page_path.parent
    validate_page(page, wiki_root)

    # Build Photon capsule structure
    capsule = {
        "name": page.name,
        "engine": "symatics",
        "glyphs": [
            {
                "operator": "⊕",
                "logic": page.body,
                "args": [],
                "meta": {
                    "source": "photon_page_runner",
                    "checksum": page.checksum(),
                    "imports": page.imports,
                },
            }
        ],
        "metadata": page.metadata,
    }

    validate_photon_capsule(capsule)
    logger.info(f"[PhotonPageRunner] Executing PhotonPage: {page.name}")
    result = execute_photon_capsule(capsule, context=context)

    result["page_checksum"] = page.checksum()
    result["imports"] = page.imports
    return result