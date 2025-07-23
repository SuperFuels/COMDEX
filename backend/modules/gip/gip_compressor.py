# File: backend/modules/gip/gip_compressor.py

from typing import List, Dict, Any
import hashlib
import json

_compression_cache: Dict[str, Dict[str, Any]] = {}

def compress_glyph_packet(glyph_packet: Dict[str, Any]) -> Dict[str, Any]:
    """
    Compresses a glyph packet into a hash-based reference if already seen.
    Returns the same packet or a compressed alias.
    """
    glyph_str = json.dumps(glyph_packet, sort_keys=True)
    hash_key = hashlib.sha256(glyph_str.encode()).hexdigest()

    if hash_key in _compression_cache:
        return {"ref": hash_key}
    else:
        _compression_cache[hash_key] = glyph_packet
        return {"ref": hash_key, "data": glyph_packet}

def decompress_glyph_packet(ref_packet: Dict[str, Any]) -> Dict[str, Any]:
    """
    Resolves a compressed glyph packet reference into full form.
    """
    ref = ref_packet.get("ref")
    if not ref:
        return ref_packet
    return _compression_cache.get(ref, {"error": "Unknown ref"})