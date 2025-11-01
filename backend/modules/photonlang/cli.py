# backend/modules/photonlang/cli.py
from __future__ import annotations
import sys

from backend.modules.photonlang.adapters.python_tokens import (
    compress_text_py,
    expand_text_py,
)

def _read_stdin_text() -> str:
    data = sys.stdin.buffer.read()
    try:
        return data.decode("utf-8")
    except Exception:
        return data.decode("utf-8", errors="replace")

def main():
    if len(sys.argv) < 2 or sys.argv[1] not in {"compress", "expand"}:
        print("Usage: python -m backend.modules.photonlang.cli [compress|expand]", file=sys.stderr)
        sys.exit(2)

    cmd = sys.argv[1]
    src = _read_stdin_text()

    if cmd == "compress":
        out = compress_text_py(src)
    else:  # expand
        out = expand_text_py(src)

    sys.stdout.write(out)

if __name__ == "__main__":
    main()