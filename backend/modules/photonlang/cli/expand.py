# backend/modules/photonlang/cli/expand.py
from __future__ import annotations
import argparse
import sys
import re
import unicodedata
from pathlib import Path

from backend.modules.photonlang.adapters.python_tokens import expand_text_py
from backend.modules.photonlang.translator import expand_symatics_ops
from backend.utils.code_sanitize import sanitize_python_code_ascii


# --- same normalization logic used by the importer ---
_ASCII_TABLE = {
    ord("−"): "-", ord("–"): "-", ord("—"): "-", ord("‒"): "-",
    0x2010: "-", 0x2011: "-", 0x2212: "-", 0x00AD: "",
    ord("\u00A0"): " ",  # NBSP
    ord("\u202F"): " ",  # NNBSP
    ord("\u2009"): " ", ord("\u200A"): " ", ord("\u2007"): " ",
    ord("\u2060"): "",   # word joiner
    0x2000: " ", 0x2001: " ",
    0x2028: "\n", 0x2029: "\n",
    ord("\ufeff"): "",
    ord("\u200b"): "", ord("\u200c"): "", ord("\u200d"): "",
    ord("“"): '"', ord("”"): '"', ord("„"): '"', ord("‟"): '"',
    ord("«"): '"', ord("»"): '"',
    ord("‘"): "'", ord("’"): "'", ord("‚"): "'", ord("‛"): "'",
    ord("＜"): "<", ord("＞"): ">", ord("＝"): "=", ord("＋"): "+",
    ord("＊"): "*", ord("／"): "/", ord("％"): "%", ord("＆"): "&",
    ord("｜"): "|", ord("，"): ",", ord("；"): ";", ord("："): ":",
    ord("（"): "(", ord("）"): ")", ord("［"): "[", ord("］"): "]",
    ord("｛"): "{", ord("｝"): "}", ord("。"): ".", ord("、"): ",",
    ord("…"): "...",
    0x00B7: "*", 0x2215: "/", 0x2044: "/", 0x2217: "*", 0x22C5: "*", 0x00F7: "/",
}
_OP_REPLS = [(r"[≤≦]", "<="), (r"[≥≧]", ">="), (r"≠", "!="), (r"[×∗·]", "*"), (r"[÷∕]", "/")]

def _normalize(src: str) -> str:
    s = unicodedata.normalize("NFKC", src)
    s = s.translate(_ASCII_TABLE)
    for pat, repl in _OP_REPLS:
        s = re.sub(pat, repl, s)
    s = re.sub(r'([A-Za-z0-9_])\s*\.\s*([A-Za-z0-9_])', r'\1.\2', s)
    s = re.sub(
        r'(?<=\d)\s*([eE])\s*([+\-]?)\s*(\d+)',
        lambda m: f"{m.group(1).lower()}{m.group(2)}{m.group(3)}",
        s,
    )
    return s
# ----------------------------------------------------


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Expand Photon (.photon/.pthon) → Python")
    ap.add_argument("input", nargs="?", default="-",
                    help="Input file path or '-' for stdin (default: '-')")
    ap.add_argument("-o", "--output",
                    help="Output path. If omitted: INPUT with .py, or stdout when reading stdin.")
    ap.add_argument("--stdout", action="store_true",
                    help="Force writing expanded code to stdout.")
    args = ap.parse_args(argv)

    # Read input
    if args.input == "-" or args.input is None:
        in_path = None
        src = sys.stdin.read()
    else:
        in_path = Path(args.input)
        src = in_path.read_text(encoding="utf-8")

    # Expand: glyph-tokens -> Python tokens, then Symatics ops -> __OPS__ calls
    py_src = expand_text_py(src)
    py_src = expand_symatics_ops(py_src)
    py_src = _normalize(py_src)
    py_src = sanitize_python_code_ascii(py_src)

    # Decide output
    if args.stdout or (in_path is None and not args.output):
        sys.stdout.write(py_src)
        return 0

    out_path = Path(args.output) if args.output else in_path.with_suffix(".py")
    out_path.write_text(py_src, encoding="utf-8")
    print(f"Wrote {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())