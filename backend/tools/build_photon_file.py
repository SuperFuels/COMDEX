#!/usr/bin/env python3
"""
Build a Photon compressed file (.photo) from any text source.

Example:
    python tools/build_photon_file.py --input log.txt --output log.photo
"""

import argparse
from pathlib import Path
import json
import time
import os

# ------------------------------------------------------------
# 🌙 Lite-Boot Switch (default: lite mode)
# ------------------------------------------------------------
def activate_lite_mode(force=False):
    """
    Enables AION/Tessaris lite mode - no heartbeat, no KG boot,
    no consciousness stack - only glyph compression core.
    """
    if force or os.getenv("PHOTON_BOOT_MODE") == "lite":
        os.environ["AION_LITE"] = "1"

# detect --lite before imports
for i, arg in enumerate(os.sys.argv):
    if arg in ("--lite", "-l"):
        activate_lite_mode(force=True)
        break
else:
    if os.getenv("PHOTON_BOOT_MODE") != "full":
        activate_lite_mode()

# ------------------------------------------------------------
# Import compression tool AFTER lite mode activation
# ------------------------------------------------------------
from backend.modules.glyphos.glyph_synthesis_engine import compress_to_glyphs

# ------------------------------------------------------------
# Helpers
# ------------------------------------------------------------
def read_file(fp: Path) -> str:
    try:
        return fp.read_text(encoding="utf-8", errors="ignore")
    except Exception as e:
        raise RuntimeError(f"Failed to read {fp}: {e}")

def write_output(fp: Path, payload: dict):
    fp.parent.mkdir(parents=True, exist_ok=True)
    fp.write_text(json.dumps(payload, indent=2, ensure_ascii=False))

def build_capsule(text: str, source_file: str):
    glyph_packet = compress_to_glyphs(text, source=source_file)

    # ensure minimal meta block present
    meta = glyph_packet.get("meta", {})
    meta.update({
        "source_file": source_file,
        "length": len(text),
        "chars_preview": text[:120] + ("..." if len(text) > 120 else "")
    })

    # standardized .photo capsule format
    return {
        "type": "photon_compressed",
        "timestamp": glyph_packet.get("timestamp", time.time()),
        "glyphs": glyph_packet.get("glyphs", []),
        "semantics": glyph_packet.get("semantics"),     # ✅ NEW semantic vector / score
        "hash": glyph_packet.get("hash"),
        "source": source_file,
        "meta": meta
    }

# ------------------------------------------------------------
# Main
# ------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", "-i", required=True, help="Input file")
    parser.add_argument("--output", "-o", help="Output .photo file")
    parser.add_argument("--lite", "-l", action="store_true", help="Force lite mode")

    args = parser.parse_args()

    input_path = Path(args.input)
    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found: {input_path}")

    out_path = Path(args.output) if args.output else input_path.with_suffix(".photo")

    text = read_file(input_path)
    capsule = build_capsule(text, str(input_path))

    write_output(out_path, capsule)
    print(f"✅ Photon capsule written: {out_path}")

if __name__ == "__main__":
    main()