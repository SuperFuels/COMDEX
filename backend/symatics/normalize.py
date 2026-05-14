# symatics/normalize.py
from __future__ import annotations
from .signature import Signature

def canonical_signature(sig: Signature) -> Signature:
    """
    Canonical Normal Form (CNF) for Signatures.
    v0.1: identity passthrough.
    TODO v0.2+: quantize amplitude/frequency to lattice, normalize phase range.
    """
    return sig