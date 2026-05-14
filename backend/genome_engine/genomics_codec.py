from __future__ import annotations
from typing import Dict, List
from .types import Json

MAPPINGS: Dict[str, Dict[str, int]] = {
    "GX1_MAP_V1": {"A": 0, "C": 1, "G": 2, "T": 3},
}

def get_mapping(mapping_id: str) -> Dict[str, int]:
    if mapping_id not in MAPPINGS:
        raise ValueError(f"Unknown mapping_id={mapping_id}")
    return dict(MAPPINGS[mapping_id])

def encode_dna(seq: str, mapping_id: str, chip_mode: str = "ONEHOT4") -> List[int]:
    m = get_mapping(mapping_id)
    s = (seq or "").strip().upper()
    out: List[int] = []
    for ch in s:
        if ch not in m:
            raise ValueError(f"Invalid base '{ch}' (allowed: {sorted(m.keys())})")
        out.append(m[ch])
    return out

def decode_tokens(tokens: List[int], mapping_id: str) -> str:
    inv = {v: k for k, v in get_mapping(mapping_id).items()}
    return "".join(inv.get(int(t), "N") for t in tokens)

def mapping_table(mapping_id: str) -> Json:
    return {"mapping_id": mapping_id, "table": get_mapping(mapping_id)}
