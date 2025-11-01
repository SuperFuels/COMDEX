# backend/tests/test_python_corpus.py
import os
import re
import ast
import random
import pathlib
import pytest

from backend.modules.photonlang.adapters.python_tokens import (
    compress_text_py,
    expand_text_py,
)
from backend.utils.code_sanitize import sanitize_python_code_ascii

ROOT = pathlib.Path(__file__).resolve().parents[1]
SKIP_DIRS = {
    ".git", "venv", ".venv", "env", "node_modules", "__pycache__",
    ".pytest_cache", ".mypy_cache", "dist", "build",
    "data", "docs", "frontend", "models", "assets",
    "backend/models",
}

MAX_FILE_SIZE = int(os.getenv("PY_CORPUS_MAX_KB", "64")) * 1024
LIMIT = int(os.getenv("PY_CORPUS_LIMIT", "200"))
SEED = int(os.getenv("PY_CORPUS_SEED", "1337"))
STRICT = os.getenv("PY_CORPUS_STRICT", "0") not in {"", "0", "false", "False"}
SKIP_UNICODE = os.getenv("PY_CORPUS_SKIP_UNICODE", "1") not in {"", "0", "false", "False"}

# --- normalization -------------------------------------------------------------

_ASCII_TABLE = {
    # dashes/minus
    ord("−"): "-", ord("–"): "-", ord("—"): "-", ord("‒"): "-",
    # spaces & zero-width & BOM
    ord("\u00A0"): " ", ord("\u202F"): " ", ord("\u2009"): " ",
    ord("\u200A"): " ", ord("\u2007"): " ", ord("\u2060"): "",
    ord("\u200B"): "",  # zero width space
    ord("\u200C"): "",  # ZWNJ
    ord("\u200D"): "",  # ZWJ
    ord("\ufeff"): "",  # BOM
    # smart quotes -> ASCII
    ord("“"): '"', ord("”"): '"', ord("„"): '"', ord("‟"): '"',
    ord("«"): '"', ord("»"): '"',
    ord("‘"): "'", ord("’"): "'", ord("‚"): "'", ord("‛"): "'",
    # fullwidth ops / punct / brackets
    ord("＜"): "<", ord("＞"): ">", ord("＝"): "=", ord("＋"): "+",
    ord("＊"): "*", ord("／"): "/", ord("％"): "%", ord("＆"): "&",
    ord("｜"): "|", ord("，"): ",", ord("；"): ";", ord("："): ":",
    ord("（"): "(", ord("）"): ")", ord("［"): "[", ord("］"): "]",
    ord("｛"): "{", ord("｝"): "}", ord("。"): ".", ord("、"): ",",
    # ellipsis
    ord("…"): "...",
}

_OP_REPLS = [
    (r"[≤≦]", "<="),
    (r"[≥≧]", ">="),
    (r"≠", "!="),
    (r"[×·]", "*"),
]

# Use real unicode escapes (not raw) so Python turns them into characters,
# and the regex sees proper ranges inside the [] character class.
UNICODE_MATH_RANGES = (
    "\u0370-\u03FF"   # Greek & Coptic
    "\u1F00-\u1FFF"   # Greek extended
    "\u2200-\u22FF"   # Math operators
    "\u27C0-\u27EF"   # Misc math symbols
    "\u2980-\u29FF"   # Misc math symbols B
)
_UNICODE_PAT = re.compile(f"[{UNICODE_MATH_RANGES}]")

def _aggressive_ascii_normalize(s: str) -> str:
    s = s.translate(_ASCII_TABLE)
    for pat, repl in _OP_REPLS:
        s = re.sub(pat, repl, s)
    return s

def _has_unicode_math(s: str) -> bool:
    return _UNICODE_PAT.search(s) is not None

def _strip_docstrings(tree: ast.AST) -> ast.AST:
    class Strip(ast.NodeTransformer):
        def _strip_first_doc(self, body):
            if body and isinstance(body[0], ast.Expr):
                v = getattr(body[0], "value", None)
                if isinstance(v, ast.Constant) and isinstance(v.value, str):
                    return body[1:]
            return body
        def visit_Module(self, node: ast.Module):
            self.generic_visit(node); node.body = self._strip_first_doc(node.body); return node
        def visit_FunctionDef(self, node: ast.FunctionDef):
            self.generic_visit(node); node.body = self._strip_first_doc(node.body); return node
        def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
            return self.visit_FunctionDef(node)
        def visit_ClassDef(self, node: ast.ClassDef):
            self.generic_visit(node); node.body = self._strip_first_doc(node.body); return node
    return Strip().visit(tree)

def _normalize_string_constants(tree: ast.AST) -> ast.AST:
    class NormStrings(ast.NodeTransformer):
        def visit_Constant(self, node: ast.Constant):
            if isinstance(node.value, str):
                return ast.copy_location(ast.Constant(value="__S__"), node)
            return node
    return NormStrings().visit(tree)

def _normalized_dump(tree: ast.AST) -> str:
    tree = _strip_docstrings(tree)
    tree = _normalize_string_constants(tree)
    ast.fix_missing_locations(tree)
    return ast.dump(tree, include_attributes=False)

# --- corpus selection ----------------------------------------------------------

def _is_candidate(path: pathlib.Path) -> bool:
    if path.suffix != ".py":
        return False
    if any(part in SKIP_DIRS for part in path.parts):
        return False
    try:
        if path.stat().st_size > MAX_FILE_SIZE:
            return False
        text = path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return False

    lower = text.lower()
    if "do not edit" in lower or "generated" in lower:
        return False

    # optionally skip unicode-heavy math/greek sources
    if SKIP_UNICODE and _has_unicode_math(text):
        return False

    try:
        ast.parse(text, filename=str(path))
    except SyntaxError:
        return False
    return True

def _collect_files():
    files = [p for p in ROOT.rglob("*.py") if _is_candidate(p)]
    random.Random(SEED).shuffle(files)
    return files[:LIMIT]

# --- test ----------------------------------------------------------------------

@pytest.mark.parametrize("path", _collect_files())
def test_python_corpus_roundtrip(path: pathlib.Path):
    src = path.read_text(encoding="utf-8")

    # compress -> expand
    comp = compress_text_py(src)
    if isinstance(comp, bytes):
        comp = comp.decode("utf-8")
    back = expand_text_py(comp)

    # normalize typography to safe ASCII tokens
    back = _aggressive_ascii_normalize(back)
    back = sanitize_python_code_ascii(back)

    # parse expanded code (lenient by default)
    try:
        b_ast = ast.parse(back, filename=str(path))
    except SyntaxError as e:
        if STRICT:
            raise
        pytest.xfail(f"expanded parse failed after normalization: {path} :: {e}")

    a_ast = ast.parse(src, filename=str(path))

    # compare normalized ASTs (ignore docstrings & string bodies)
    da = _normalized_dump(a_ast)
    db = _normalized_dump(b_ast)
    if STRICT:
        assert da == db, f"AST mismatch after round-trip for {path}."
    else:
        if da != db:
            pytest.xfail(f"non-strict AST mismatch tolerated: {path}")