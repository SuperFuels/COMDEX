# backend/modules/glyphos/symbolic_hash_engine.py

import hashlib
import json
from typing import Union, Set, Dict, Any

def normalize_glyph(glyph: Union[str, Dict[str, Any]]) -> str:
    """
    Normalize a glyph input (str or dict) into a consistent canonical string.
    - Strings are trimmed and returned as-is.
    - Dicts are converted to a sorted JSON string, optionally prioritizing key metadata fields.
    - CodexAST objects with .to_dict() are serialized with only relevant metadata.
    """
    if isinstance(glyph, str):
        return glyph.strip()

    elif hasattr(glyph, "to_dict"):
        glyph_dict = glyph.to_dict()
    elif isinstance(glyph, dict):
        glyph_dict = glyph
    else:
        raise TypeError(f"Unsupported glyph type for hashing: {type(glyph)}")

    # 🧠 Prioritize important metadata fields (optional)
    important_metadata = {}
    meta = glyph_dict.get("metadata", {})
    if isinstance(meta, dict):
        for k in ("prediction", "sqi_score", "collapse_state"):
            if k in meta:
                important_metadata[k] = meta[k]

    hash_friendly_dict = dict(glyph_dict)  # Shallow copy
    hash_friendly_dict["__hash_metadata__"] = important_metadata
    return json.dumps(hash_friendly_dict, sort_keys=True, separators=(',', ':'))

def symbolic_hash(
    glyph: Union[str, Dict[str, Any]],
    hash_algo: str = "sha256"
) -> str:
    """
    Generate a versioned symbolic hash of a glyph.
    Supports SHA-256 by default; extendable in future.
    """
    canonical = normalize_glyph(glyph).encode("utf-8")
    h = hashlib.new(hash_algo)
    h.update(canonical)
    return h.hexdigest()

def symbolic_short_hash(
    glyph: Union[str, Dict[str, Any]],
    length: int = 8
) -> str:
    """
    Generate a short symbolic hash (e.g. for display or fast indexing).
    """
    return symbolic_hash(glyph)[:length]

def is_duplicate(
    glyph: Union[str, Dict[str, Any]],
    known_hashes: Set[str]
) -> bool:
    """
    Check if a glyph has already been processed.
    """
    return symbolic_hash(glyph) in known_hashes

def add_to_known(
    glyph: Union[str, Dict[str, Any]],
    known_hashes: Set[str]
) -> None:
    """
    Add a glyph hash to the known set.
    """
    known_hashes.add(symbolic_hash(glyph))

def log_hash(
    glyph: Union[str, Dict[str, Any]],
    label: str = "glyph"
):
    """
    Print the symbolic hash and short hash of a glyph for debugging.
    """
    full = symbolic_hash(glyph)
    short = full[:8]
    print(f"🔗 {label} hash → {short}… ({full})")