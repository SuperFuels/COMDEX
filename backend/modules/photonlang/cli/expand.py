from __future__ import annotations
import argparse
from pathlib import Path
from backend.modules.photonlang.adapters.python_tokens import expand_text_py

def main(argv=None):
    ap = argparse.ArgumentParser(description="Expand Photon -> Python (.py)")
    ap.add_argument("input", help="Input .photon/.pthon file")
    ap.add_argument("-o", "--output", help="Output path (defaults to input with .py)")
    args = ap.parse_args(argv)

    inp = Path(args.input)
    out = Path(args.output) if args.output else inp.with_suffix(".py")

    data = inp.read_text(encoding="utf-8")
    exp = expand_text_py(data)
    out.write_text(exp, encoding="utf-8")
    print(f"Wrote {out}")

if __name__ == "__main__":
    main()