# backend/modules/photonlang/cli.py
#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from backend.modules.photonlang.adapters.python_tokens import (
    compress_text_py,
    expand_text_py,
    normalize_roundtrip,
)
from backend.modules.photonlang.translator import expand_symatics_ops

# Best-effort version string
try:
    from backend.modules.photonlang import __version__ as _PHOTON_VERSION
except Exception:  # pragma: no cover
    _PHOTON_VERSION = "0.0.0+local"


# ---------------- I/O helpers ----------------

def _read_stdin_text() -> str:
    data = sys.stdin.buffer.read()
    try:
        return data.decode("utf-8")
    except Exception:
        return data.decode("utf-8", errors="replace")


def _read_input(path_or_dash: str | None) -> str:
    """
    Read from a file path, '-' (stdin), or if no path is provided read stdin.
    This matches Git clean/smudge filter expectations.
    """
    if not path_or_dash or path_or_dash == "-":
        return _read_stdin_text()
    return Path(path_or_dash).read_text(encoding="utf-8")


def _write_output(text: str, out_path: str | None) -> None:
    if out_path:
        Path(out_path).write_text(text, encoding="utf-8")
    else:
        sys.stdout.write(text)


# ---------------- subcommands ----------------

def cmd_compress(args: argparse.Namespace) -> None:
    src = _read_input(args.input)
    out = compress_text_py(src)
    _write_output(out, args.output)


def cmd_expand(args: argparse.Namespace) -> None:
    src = _read_input(args.input)
    # 1) Photon glyphs → Python tokens
    py = expand_text_py(src)
    # 2) Symatics ops (⊕, μ, …) → __OPS__["…"](...) + import prolog
    py = expand_symatics_ops(py)
    # 3) Canonical spacing for stable round-trips
    py = normalize_roundtrip(py)
    _write_output(py, args.output)


def cmd_run(args: argparse.Namespace) -> None:
    # Load from file (preserves filename in tracebacks)
    path = Path(args.path)
    src = path.read_text(encoding="utf-8")

    # Expand + canonicalize
    py = expand_text_py(src)
    py = expand_symatics_ops(py)
    py = normalize_roundtrip(py)

    g: dict[str, object] = {"__name__": "__main__", "__file__": str(path)}
    code = compile(py, str(path), "exec")
    exec(code, g, g)

    if args.eval:
        val = eval(args.eval, g, g)
        # Pretty JSON for simple types; fallback to str()
        try:
            import json
            if isinstance(val, (dict, list, tuple, int, float, bool, type(None))):
                _write_output(json.dumps(val, ensure_ascii=False) + "\n")
            else:
                _write_output(f"{val}\n")
        except Exception:
            _write_output(f"{val}\n")


# ---------------- argparse wiring ----------------

def main(argv: list[str] | None = None) -> None:
    epilog = r"""
Examples:
  # Expand Photon → Python (stdout)
  python -m backend.modules.photonlang.cli expand backend/tests/demo_math.photon | head -n 12

  # Run a Photon module and evaluate an expression
  python -m backend.modules.photonlang.cli run backend/tests/demo_math.photon -e 'add_and_measure(2,3)'

  # Enriched tracebacks (map to .photon lines)
  PHOTON_TB=1 python -m backend.modules.photonlang.cli run backend/tests/demo_error.photon -e 'oops(3)'

  # Policy: block host imports and enforce signature
  PHOTON_HOST_DENY=os,subprocess PHOTON_SIG_SHA256=<hex> \
    python -m backend.modules.photonlang.cli run your_module.photon

  # Git clean/smudge via stdin/stdout
  git config filter.photon.clean  "python -m backend.modules.photonlang.cli compress"
  git config filter.photon.smudge "python -m backend.modules.photonlang.cli expand"
""".strip("\n")

    parser = argparse.ArgumentParser(
        prog="photonlang",
        description="Photon CLI: compress, expand, and run .photon modules.",
        epilog=epilog,
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"photonlang {_PHOTON_VERSION}",
        help="Show version and exit.",
    )

    sub = parser.add_subparsers(dest="cmd", required=True)

    p_compress = sub.add_parser(
        "compress",
        help="Compress Python → Photon tokens (reads stdin if no path)."
    )
    p_compress.add_argument("input", nargs="?", help="Path or '-' (default: stdin)")
    p_compress.add_argument("-o", "--output", help="Output file (default: stdout)")
    p_compress.set_defaults(func=cmd_compress)

    p_expand = sub.add_parser(
        "expand",
        help="Expand .photon → Python (reads stdin if no path)."
    )
    p_expand.add_argument("input", nargs="?", help="Path or '-' (default: stdin)")
    p_expand.add_argument("-o", "--output", help="Output file (default: stdout)")
    p_expand.set_defaults(func=cmd_expand)

    p_run = sub.add_parser("run", help="Run a .photon/.pthon file.")
    p_run.add_argument("path", help="Path to .photon/.pthon file")
    p_run.add_argument("-e", "--eval", help="Expression to eval after exec (prints result).")
    p_run.set_defaults(func=cmd_run)

    args = parser.parse_args(argv)
    args.func(args)


# Optional console_script wrappers (keep for entry_points)
def main_compress() -> None:
    main(["compress"])


def main_expand() -> None:
    main(["expand"])


def main_run() -> None:
    main(["run"])


if __name__ == "__main__":
    main()