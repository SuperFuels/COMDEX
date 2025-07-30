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
from typing import Union

# ---------------------------------------------------------
# 🔑 Generate SHA256 Hash (default for Codex)
# ---------------------------------------------------------
def generate_hash(data: Union[str, bytes], encoding: str = "hex") -> str:
    """
    Generates a SHA256 hash of the provided string or bytes.
    Used for container IDs, glyph traces, and symbolic addressing.

    Args:
        data: Input string or bytes
        encoding: "hex" (default) or "base64"

    Returns:
        Hash string (hex or base64 encoded)
    """
    if isinstance(data, str):
        data = data.encode("utf-8")

    sha = hashlib.sha256(data).digest()

    if encoding == "base64":
        return base64.urlsafe_b64encode(sha).decode("utf-8").rstrip("=")
    return hashlib.sha256(data).hexdigest()

# ---------------------------------------------------------
# 🧪 CLI Test
# ---------------------------------------------------------
if __name__ == "__main__":
    sample = "Tesseract Container"
    print("Input:", sample)
    print("SHA256 Hex:", generate_hash(sample))
    print("SHA256 Base64:", generate_hash(sample, encoding="base64"))