#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
📘 Photon Page Spec (.ptn)
────────────────────────────────────────────
Defines structure, metadata, and checksum rules
for Tessaris Photon Pages (Symbolic Capsules).

Used by:
 - ptn_validator.py  -> syntax/import checks
 - ptn_runner.py     -> execution
 - ptn_converter.py  -> serialization

Author: Tessaris / Aion Systems
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any
import hashlib, time


@dataclass
class PhotonPage:
    """High-level symbolic container for Photon execution capsules."""
    name: str
    imports: List[str] = field(default_factory=list)
    body: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def checksum(self) -> str:
        """Return SHA3-256 checksum of the body."""
        return hashlib.sha3_256(self.body.encode("utf-8")).hexdigest()

    def to_dict(self) -> Dict[str, Any]:
        meta = self.metadata.copy()
        meta.setdefault("version", "1.0")
        meta.setdefault("timestamp", time.time())
        meta.setdefault("signed_by", "Tessaris-Core")

        return {
            "name": self.name,
            "imports": self.imports,
            "body": self.body,
            "metadata": meta,
            "checksum": self.checksum(),
        }


def make_photon_page(name: str, imports=None, body="", metadata=None) -> PhotonPage:
    """Factory helper for creating PhotonPage instances."""
    return PhotonPage(name=name, imports=imports or [], body=body, metadata=metadata or {})