"""
🧮 Codex Utils
-----------------------------------------------------
Utility functions for Codex-related operations:
    • Hash generation (content addressing)
    • Symbol-safe encoding for glyph and container IDs
    • Miscellaneous helpers for Codex runtime
"""

import hashlib
import base64
import json
import logging
from typing import Union

logger = logging.getLogger(__name__)

# ---------------------------------------------------------
# 🔑 Generate SHA256 Hash (default for Codex)
# ---------------------------------------------------------
def generate_hash(data: Union[str, bytes, dict, list], encoding: str = "hex") -> str:
    """
    Generates a SHA256 hash of the provided input.
    Supports strings, bytes, dicts, and lists (auto-JSON serialization).

    Args:
        data: Input data (str, bytes, dict, or list)
        encoding: "hex" (default) or "base64"

    Returns:
        Hash string (hex or base64 encoded)
    """
    # ✅ Auto-convert dict/list to JSON (deterministic order)
    if isinstance(data, (dict, list)):
        try:
            data = json.dumps(data, sort_keys=True).encode("utf-8")
        except Exception as e:
            logger.error(f"[CodexUtils] Failed to serialize data for hashing: {e}")
            raise

    elif isinstance(data, str):
        data = data.encode("utf-8")
    elif not isinstance(data, (bytes, bytearray)):
        raise TypeError(f"[CodexUtils] Unsupported type for generate_hash: {type(data)}")

    sha = hashlib.sha256(data).digest()

    if encoding == "base64":
        return base64.urlsafe_b64encode(sha).decode("utf-8").rstrip("=")
    return hashlib.sha256(data).hexdigest()


# ---------------------------------------------------------
# 🧪 CLI Test
# ---------------------------------------------------------
if __name__ == "__main__":
    sample = {"id": "Tesseract", "glyphs": ["↔", "⧖", "🧬"]}
    print("Input (dict):", sample)
    print("SHA256 Hex:", generate_hash(sample))
    print("SHA256 Base64:", generate_hash(sample, encoding="base64"))