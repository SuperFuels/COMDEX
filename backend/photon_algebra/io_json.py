# -*- coding: utf-8 -*-
"""
Photon JSON I/O
===============
Task: I6 - Deterministic JSON Serialization Layer

Provides export and import of Photon Algebra expressions in JSON form.
Guarantees canonical structure (sorted keys, UTF-8 safe) and reversibility
through `json_to_photon(photon_to_json(expr)) == expr`.

Intended for stable interchange between tools or persistent caching.
"""

import json
from backend.photon_algebra.rewriter import normalize


def photon_to_json(expr, *, pretty=False, sort_keys=True) -> str:
    """
    Serialize a Photon IR expression into deterministic JSON.
    """
    expr_norm = normalize(expr)
    if pretty:
        return json.dumps(expr_norm, ensure_ascii=False, indent=2, sort_keys=sort_keys)
    return json.dumps(expr_norm, ensure_ascii=False, separators=(",", ":"), sort_keys=sort_keys)


def json_to_photon(json_str: str):
    """
    Deserialize a Photon IR expression from JSON.
    """
    return json.loads(json_str)


def photon_roundtrip(expr):
    """
    Full encode/decode roundtrip convenience wrapper.
    """
    return json_to_photon(photon_to_json(expr))


# Diagnostic entrypoint
if __name__ == "__main__":
    from backend.photon_algebra.tests.test_pp_roundtrip import photon_exprs
    sample = photon_exprs().example()
    print("Original:", sample)
    encoded = photon_to_json(sample, pretty=True)
    print("\nEncoded JSON:\n", encoded)
    decoded = json_to_photon(encoded)
    print("\nDecoded:", decoded)
    print("\nRoundtrip OK:", normalize(sample) == normalize(decoded))