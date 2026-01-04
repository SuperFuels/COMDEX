from __future__ import annotations

from typing import Any, Dict
import hashlib
import json
import math

Json = Any


def stable_stringify(x: Json) -> str:
    """
    Canonical JSON string:
    - dict keys are stringified + sorted
    - lists preserve order
    - floats: forbid NaN/Inf, normalize -0.0 -> 0.0
    - separators tightened for stable bytes
    """
    return json.dumps(
        _stabilize(x),
        separators=(",", ":"),
        ensure_ascii=False,
        sort_keys=True,   # keys are strings by the time they get here
        allow_nan=False,  # hard fail if NaN/Inf tries to leak in
    )


def stable_hash(x: Json) -> str:
    """
    Stable SHA-256 over the canonical JSON bytes.
    This is the ONE hashing helper tests + replay digests should use.
    """
    b = stable_stringify(x).encode("utf-8")
    return hashlib.sha256(b).hexdigest()


def _stabilize(x: Json) -> Json:
    if x is None or isinstance(x, (bool, int, str)):
        return x

    if isinstance(x, float):
        if not math.isfinite(x):
            raise ValueError("stable_json: NaN/Inf not allowed in deterministic artifacts")
        # normalize -0.0 -> 0.0 (canonical)
        return 0.0 if x == 0.0 else x

    if isinstance(x, list):
        return [_stabilize(v) for v in x]

    if isinstance(x, tuple):
        return [_stabilize(v) for v in x]

    if isinstance(x, dict):
        out: Dict[str, Json] = {}
        for k, v in x.items():
            out[str(k)] = _stabilize(v)
        # sort by stringified keys
        return {k: out[k] for k in sorted(out.keys())}

    return str(x)