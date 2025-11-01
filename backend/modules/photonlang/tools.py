import sys, argparse
from pathlib import Path
from .adapters.python_tokens import compress_text_py, expand_text_py

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["compress","expand"])
    ap.add_argument("infile")
    ap.add_argument("-o","--outfile")
    a = ap.parse_args()

    txt = Path(a.infile).read_text(encoding="utf-8")
    out = compress_text_py(txt) if a.mode=="compress" else expand_text_py(txt)
    if a.outfile:
        Path(a.outfile).write_text(out, encoding="utf-8")
    else:
        sys.stdout.write(out)

if __name__ == "__main__":
    main()