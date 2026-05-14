"""
📘 Photon Page Spec
-------------------
Defines .ptn file structure and header grammar.
A Photon Page (.ptn) orchestrates Wiki + Photon capsules.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any
import hashlib, time

@dataclass
class PhotonPage:
    name: str
    imports: List[str] = field(default_factory=list)
    body: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def checksum(self) -> str:
        """Return SHA3-256 checksum of page body."""
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
            "checksum": self.checksum()
        }

def make_photon_page(name: str, imports=None, body="", metadata=None) -> PhotonPage:
    return PhotonPage(name=name, imports=imports or [], body=body, metadata=metadata or {})