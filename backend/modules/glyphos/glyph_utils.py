import hashlib
import json


def parse_to_glyphos(data: str) -> dict:
    """Parse raw string or JSON into glyph-compatible dictionary."""
    try:
        return json.loads(data)
    except json.JSONDecodeError:
        return {"raw": data}


def summarize_to_glyph(data: dict) -> str:
    """Generate a symbolic glyph summary from a data block."""
    if "type" in data and "value" in data:
        return f"⟦{data['type']}|{data.get('tag', '')}:{data['value']}⟧"
    if "raw" in data:
        return f"⟦Raw|Text:{data['raw']}⟧"
    return f"⟦Data|Unknown:{str(data)[:20]}⟧"


def generate_hash(obj: dict) -> str:
    """Generate a SHA256 hash from a dictionary object."""
    json_str = json.dumps(obj, sort_keys=True)
    return hashlib.sha256(json_str.encode("utf-8")).hexdigest()