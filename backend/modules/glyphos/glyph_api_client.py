# backend/modules/glyphos/glyph_api_client.py

import os
import requests

GLYPH_API_BASE_URL = os.getenv("GLYPH_API_BASE_URL", "http://localhost:8000")

def synthesize_glyphs(text: str, source: str = "manual") -> dict | None:
    try:
        response = requests.post(
            f"{GLYPH_API_BASE_URL}/api/aion/synthesize-glyphs",
            json={"text": text, "source": source}
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"[GlyphAPI ❌] Failed to synthesize glyphs: {e}")
        return None