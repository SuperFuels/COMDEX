# backend/modules/chain_sim/canonical_codec.py
from __future__ import annotations

import hashlib
from typing import Any

# Deterministic, JSON-ambiguity-free encoding.
# - Dict keys must be strings
# - Floats are not allowed (use int/bps/strings)
# - Bytes supported
# - Order: dict keys sorted lexicographically

def canonical_encode(x: Any) -> bytes:
    if x is None:
        return b"n"

    if isinstance(x, bool):
        return b"t" if x else b"f"

    if isinstance(x, int):
        # i<decimal>;
        return b"i" + str(x).encode("utf-8") + b";"

    if isinstance(x, float):
        raise TypeError("canonical_encode: float is not allowed (use int or string).")

    if isinstance(x, bytes):
        # y<len>:<bytes>
        return b"y" + str(len(x)).encode("utf-8") + b":" + x

    if isinstance(x, str):
        b = x.encode("utf-8")
        # s<len>:<utf8>
        return b"s" + str(len(b)).encode("utf-8") + b":" + b

    if isinstance(x, (list, tuple)):
        out = [b"l", str(len(x)).encode("utf-8"), b":"]
        for item in x:
            out.append(canonical_encode(item))
        out.append(b";")
        return b"".join(out)

    if isinstance(x, dict):
        # d<len>: (k,v,k,v...) ;
        keys = list(x.keys())
        for k in keys:
            if not isinstance(k, str):
                raise TypeError("canonical_encode: dict keys must be strings.")
        keys.sort()

        out = [b"d", str(len(keys)).encode("utf-8"), b":"]
        for k in keys:
            out.append(canonical_encode(k))
            out.append(canonical_encode(x[k]))
        out.append(b";")
        return b"".join(out)

    # Pydantic/BaseModel etc.
    if hasattr(x, "model_dump"):
        return canonical_encode(x.model_dump())
    if hasattr(x, "dict"):
        return canonical_encode(x.dict())

    raise TypeError(f"canonical_encode: unsupported type {type(x)}")


def sha256_hex(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def canonical_hash_hex(x: Any) -> str:
    return sha256_hex(canonical_encode(x))