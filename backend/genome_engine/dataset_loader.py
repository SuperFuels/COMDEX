from __future__ import annotations
from typing import List
import json
from .types import DatasetRow

def _normalize_row(r: dict) -> DatasetRow:
    seq = r.get("seq")
    if seq is None:
        seq = r.get("sequence")
    if seq is None:
        raise ValueError(f"Row missing seq/sequence keys: {sorted(r.keys())}")

    out: DatasetRow = {
        "id": str(r.get("id", "")),
        "seq": str(seq),
        "label": r.get("label"),
        "channel_key": r.get("channel_key"),
        "mutation": r.get("mutation"),
    }
    return out

def load_jsonl_dataset(path: str) -> List[DatasetRow]:
    rows: List[DatasetRow] = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            s = line.strip()
            if not s:
                continue
            rows.append(_normalize_row(json.loads(s)))
    rows.sort(key=lambda r: str(r.get("id", "")))  # deterministic order
    return rows
