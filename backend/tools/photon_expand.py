#!/usr/bin/env python3
"""
Reverse Photon Capsule → Human Reconstruction (v0.1)

Usage:
    PYTHONPATH=. python backend/tools/photon_expand.py --input sample.photo
"""

import json
import argparse
from pathlib import Path

# Import glyph registry + utils
from backend.modules.glyphos.glyph_storage import get_glyph_registry
from backend.modules.glyphos.glyph_utils import expand_from_glyphs


def load_capsule(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        raise RuntimeError(f"Failed to read capsule {path}: {e}")


def reconstruct_text(glyphs):
    """
    Reverse path:

    glyphs[] → (lookup lemma) → expanded text (placeholder layer)
    """
    registry = get_glyph_registry()
    results = []

    for g in glyphs:
        # Find matching lemma(s)
        lemmas = [k for k, v in registry.items()
                  if isinstance(v, dict) and v.get("glyph") == g]

        if lemmas:
            # Best match = first lemma
            reconstructed = lemmas[0]
        else:
            # Fall back to reversible scaffolding util
            reconstructed = expand_from_glyphs([g])

        results.append(f"{g} → {reconstructed}")

    return "\n".join(results)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", "-i", required=True, help="Input .photo file")
    parser.add_argument("--output", "-o", help="Write full reconstruction to file")

    args = parser.parse_args()

    input_path = Path(args.input)
    if not input_path.exists():
        raise FileNotFoundError(f"No such file: {input_path}")

    capsule = load_capsule(input_path)
    glyphs = capsule.get("glyphs", [])

    header = f"🔁 Photon Reverse Expansion\nSource: {capsule.get('source')}\nGlyphs: {glyphs}\n\n"
    body = reconstruct_text(glyphs)
    text = header + body

    if args.output:
        out_path = Path(args.output)
    else:
        out_path = input_path.with_suffix(".recon.txt")

    out_path.write_text(text, encoding="utf-8")
    print(f"✅ Reconstruction written: {out_path}")


if __name__ == "__main__":
    main()