# backend/tests/test_corpus_smoke.py
import os, ast, re
from pathlib import Path
from backend.modules.photonlang.adapters.python_tokens import compress_text_py, expand_text_py

EXCLUDE_DIRS = {
    ".git", ".hg", ".svn", "__pycache__", ".mypy_cache", ".pytest_cache",
    "venv", ".venv", "env", ".env", "site-packages", "node_modules",
    "dist", "build",
}

def _roots_from_env():
    roots = os.getenv("PHOTON_CORPUS_ROOTS")
    if roots:
        return [Path(r).resolve() for r in roots.split(":") if r]
    # Default: repo backend/ only
    return [Path(__file__).resolve().parents[2] / "backend"]

def _iter_py_files(roots, limit):
    count = 0
    for root in roots:
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [d for d in dirnames if d not in EXCLUDE_DIRS]
            for fn in filenames:
                if not fn.endswith(".py"):
                    continue
                if count >= limit:
                    return
                yield Path(dirpath, fn)
                count += 1

# --- Normalizers ---------------------------------------------------------
# glue "1 e -12" (and variants) → "1e-12"  (do not cross newlines!)
_SCI_FIX = re.compile(r"""
    (?<![A-Za-z_])                              # not part of an identifier
    (?P<mant>(?:\d+(?:\.\d*)?|\.\d+))           # 12, 12., 0.12, .12
    [^\S\n]*(?P<e>[eE])[^\S\n]*                 # e / E with spaces/tabs only
    (?P<sign>[+\-]?)[^\S\n]*                    # optional sign with spaces/tabs only
    (?P<exp>\d+)                                # exponent digits
""", re.VERBOSE)

# collapse non-breaking/thin spaces to normal space
_WS_FIX = re.compile(r"[\u00A0\u2000-\u200B]")

def _normalize_ws(s: str) -> str:
    return _WS_FIX.sub(" ", s)

def _normalize_sci_notation(s: str) -> str:
    return _SCI_FIX.sub(lambda m: f"{m.group('mant')}e{m.group('sign')}{m.group('exp')}", s)

def _normalize_all(s: str) -> str:
    # order matters: first tame odd whitespace, then fix sci-notation
    s = _normalize_ws(s)
    s = _normalize_sci_notation(s)
    return s

def test_corpus_can_roundtrip_parse():
    limit = int(os.getenv("PHOTON_CORPUS_LIMIT", "200"))
    roots = _roots_from_env()

    failures = []
    tested = 0

    for p in _iter_py_files(roots, limit):
        try:
            src = p.read_text(encoding="utf-8")
        except Exception:
            continue

        # Only include files that parse (possibly after normalization)
        src_for_test = _normalize_ws(src)
        try:
            ast.parse(src_for_test)
        except Exception:
            src_fixed = _normalize_all(src_for_test)
            try:
                ast.parse(src_fixed)
                src_for_test = src_fixed
            except Exception:
                continue  # still invalid → skip this file

        try:
            comp = compress_text_py(src_for_test)
            back = expand_text_py(comp)
            back = _normalize_all(back)         # normalize expanded text too
            ast.parse(back)

            compile(src_for_test, str(p), "exec")
            compile(back, f"{p}::rt", "exec")
            tested += 1
        except Exception as e:
            failures.append((str(p), repr(e)))

    assert tested > 0, "No files tested."
    assert not failures, "Failures:\n" + "\n".join(f"{p}: {err}" for p, err in failures)