from __future__ import annotations
import argparse, sys
from pathlib import Path
from backend.modules.photonlang.adapters.python_tokens import compress_text_py

def main(argv=None):
    ap = argparse.ArgumentParser(description="Compress Python -> Photon (.photon)")
    ap.add_argument("input", help="Input .py file")
    ap.add_argument("-o", "--output", help="Output path (defaults to input with .photon)")
    args = ap.parse_args(argv)

    inp = Path(args.input)
    out = Path(args.output) if args.output else inp.with_suffix(".photon")

    data = inp.read_text(encoding="utf-8")
    comp = compress_text_py(data)
    out.write_text(comp, encoding="utf-8")
    print(f"Wrote {out}")

if __name__ == "__main__":
    main()