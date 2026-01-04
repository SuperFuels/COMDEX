from __future__ import annotations
from typing import Any, Dict

Json = Any

def stable_stringify(x: Json) -> str:
    import json
    return json.dumps(_stabilize(x), separators=(",", ":"), ensure_ascii=False)

def _stabilize(x: Json) -> Json:
    if x is None or isinstance(x, (bool, int, float, str)):
        return x
    if isinstance(x, list):
        return [_stabilize(v) for v in x]
    if isinstance(x, dict):
        out: Dict[str, Json] = {}
        for k in sorted(x.keys()):
            out[str(k)] = _stabilize(x[k])
        return out
    return str(x)
