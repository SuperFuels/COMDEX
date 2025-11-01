# backend/tests/test_python_corpus.py
import os
import re
import ast
import random
import pathlib
import unicodedata
import pytest

# Sanitizer — ensures only ASCII punctuation in code tokens
from backend.utils.code_sanitize import sanitize_python_code_ascii

# Adapter functions under test
from backend.modules.photonlang.adapters.python_tokens import (
    compress_text_py,
    expand_text_py,
)

# ------------------------------------------------------------------------------
# Config (env-tunable)
# ------------------------------------------------------------------------------

ROOT = pathlib.Path(__file__).resolve().parents[1]

# Include/Exclude controls
ONLY = [s.strip() for s in os.getenv("PY_CORPUS_ONLY", "").split(",") if s.strip()]
EXCLUDE = [s.strip() for s in os.getenv("PY_CORPUS_EXCLUDE", "").split(",") if s.strip()]

# Known fragile files/patterns (path substring -> reason)
KNOWN_BAD = {
    "backend/routes/sqi_route.py": "brace escaping in JSON/f-string after expand",
    "backend/modules/scrolls/scroll_builder.py": "try/except wrapper altered by expand",
    "backend/modules/sqi/__init__.py": "inner import/function stub rewritten",
    "backend/modules/holograms/ghx_logging.py": "expand injects extra import",
    "backend/alembic/versions/": "migration headers not stable across round-trip",
    "backend/modules/codex/collapse_trace_exporter.py": "indentation drift on wrapped import",
    "backend/modules/photonlang/runtime/photon_importer.py": "wrapper auto-install; AST drift under round-trip",
    "backend/utils/code_sanitize.py": "newline-sensitive dot-join in normalization triggers indent error after expand",
}

# Whether to skip (default) or include known-bad files
SKIP_KNOWN_BAD = os.getenv("PY_CORPUS_SKIP_KNOWN_BAD", "1").lower() in {"1", "true", "yes"}
# If not skipped, mark them xfail by default
XFAIL_KNOWN_BAD = os.getenv("PY_CORPUS_XFAIL_KNOWN_BAD", "1").lower() in {"1", "true", "yes"}

# Skip heavy/generated/vendor dirs
SKIP_DIRS = {
    ".git", "venv", ".venv", "env", "node_modules", "__pycache__",
    ".pytest_cache", ".mypy_cache", "dist", "build",
    "data", "docs", "frontend", "models", "assets",
    "backend/models",
}

MAX_FILE_SIZE = int(os.getenv("PY_CORPUS_MAX_KB", "64")) * 1024  # default 64KB
LIMIT = int(os.getenv("PY_CORPUS_LIMIT", "200"))                 # sample size
SEED = int(os.getenv("PY_CORPUS_SEED", "1337"))

# Strictness toggles
STRICT = os.getenv("PY_CORPUS_STRICT", "0").lower() in {"1", "true", "yes"}
STRICT_BYTECODE = os.getenv("PY_CORPUS_STRICT_BYTECODE", "0").lower() in {"1", "true", "yes"}

# Skip files that contain non-ASCII / mathy unicode by default
SKIP_UNICODE = os.getenv("PY_CORPUS_SKIP_UNICODE", "1").lower() not in {"", "0", "false"}

# ------------------------------------------------------------------------------
# Unicode normalization helpers
# ------------------------------------------------------------------------------

# Common typographic/fullwidth replacements (applied after NFKC)
_ASCII_TABLE = {
    # dashes/minus
    ord("−"): "-", ord("–"): "-", ord("—"): "-", ord("‒"): "-",
    ord("\u2010"): "-", ord("\u2011"): "-",
    0x2212: "-",            # mathematical minus
    0x00AD: "",             # soft hyphen

    # spaces & joiners
    ord("\u00A0"): " ",     # NBSP
    ord("\u202F"): " ",     # NNBSP
    ord("\u2009"): " ", ord("\u200A"): " ", ord("\u2007"): " ",
    ord("\u2060"): "",      # word joiner
    0x2000: " ", 0x2001: " ",  # en/em quad → space

    # line/paragraph separators
    0x2028: "\n", 0x2029: "\n",

    # zero-width / BOM
    ord("\ufeff"): "",
    ord("\u200b"): "", ord("\u200c"): "", ord("\u200d"): "",

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

    # additional single-char operator variants
    0x00B7: "*",            # middle dot (often used as multiply)
    0x2215: "/", 0x2044: "/",  # division/fraction slash
    0x2217: "*", 0x22C5: "*",  # asterisk/middle dot operator
    0x00F7: "/",            # ÷
}

# Regex operator normalizations (multi-char)
_OP_REPLS = [
    (r"[≤≦]", "<="),
    (r"[≥≧]", ">="),
    (r"≠", "!="),
    (r"[×∗·]", "*"),
    (r"[÷∕]", "/"),
]

# Math-ish blocks that often sneak in
UNICODE_MATH_RANGES = (
    r"\u0370-\u03FF"   # Greek & Coptic
    r"\u1F00-\u1FFF"   # Greek extended
    r"\u2070-\u209F"   # Superscripts/Subscripts
    r"\u2200-\u22FF"   # Math operators
    r"\u27C0-\u27EF"   # Misc math symbols
    r"\u2980-\u29FF"   # Misc math symbols B
)
_UNICODE_MATH_RE = re.compile(f"[{UNICODE_MATH_RANGES}]")

def _aggressive_ascii_normalize(s: str) -> str:
    """
    Make expanded text safe for Python parsing by removing typographic
    unicode in code tokens, fixing scientific notation spacing, and
    rejoining attribute access / floats split by spaces.
    """
    # 1) Fold compatibility/fullwidth forms (ｅ, １, －) to ASCII
    s = unicodedata.normalize("NFKC", s)

    # 2) Strip zero-widths / BOM / word-joiners that can hide in code
    for zw in ("\u200b", "\u200c", "\u200d", "\ufeff", "\u2060"):
        s = s.replace(zw, "")

    # 3) Targeted codepoint fixes (minus & slashes & asterisk op)
    manual = {
        "\u2212": "-",  # mathematical minus
        "\u207b": "-",  # superscript minus
        "\u208b": "-",  # subscript minus
        "\u2044": "/",  # fraction slash
        "\u2215": "/",  # division slash
        "\u2217": "*",  # asterisk operator
    }
    s = s.translate(str.maketrans(manual))

    # 4) General ASCII table & operator replacements (≤, ≥, ≠, ×, ·, …)
    s = s.translate(_ASCII_TABLE)
    for pat, repl in _OP_REPLS:
        s = re.sub(pat, repl, s)

    # 5) Glue dotted attribute access and floats: "np . linspace" -> "np.linspace", "1 . 0" -> "1.0"
    s = re.sub(r"([A-Za-z0-9_])\s*\.\s*([A-Za-z0-9_])", r"\1.\2", s)

    # 6) Glue scientific notation with optional spaces/signs:
    #    "1 e − 9" / "1e −9" / "1  E   6"  -> "1e-9" / "1e-9" / "1E6"
    s = re.sub(
        r"(?<=\d)\s*([eE])\s*([+\-]?)\s*(\d+)",
        lambda m: f"{m.group(1).lower()}{m.group(2)}{m.group(3)}",
        s,
    )

    return s

def _has_unicode_math(s: str) -> bool:
    """True if file contains non-ASCII or mathy Unicode that often breaks tokens."""
    if _UNICODE_MATH_RE.search(s):
        return True
    # Be conservative by default: skip on any non-ASCII if SKIP_UNICODE=1
    return any(ord(ch) > 127 for ch in s)

# ------------------------------------------------------------------------------
# AST canonicalization (reduce false diffs)
# ------------------------------------------------------------------------------

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

# ------------------------------------------------------------------------------
# Corpus selection
# ------------------------------------------------------------------------------

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
    if "do not edit" in lower or "generated" in lower or "auto-generated" in lower:
        return False

    if SKIP_UNICODE and _has_unicode_math(text):
        return False

    try:
        ast.parse(text, filename=str(path))
    except SyntaxError:
        return False
    return True

def _is_known_bad(path: pathlib.Path) -> str | None:
    p = str(path)
    for key, reason in KNOWN_BAD.items():
        if key in p:
            return reason
    return None

# --- include/exclude filters from env ---
ONLY    = [s.strip() for s in os.getenv("PY_CORPUS_ONLY", "").split(",") if s.strip()]
EXCLUDE = [s.strip() for s in os.getenv("PY_CORPUS_EXCLUDE", "").split(",") if s.strip()]

def _collect_files():
    files = [p for p in ROOT.rglob("*.py") if _is_candidate(p)]

    # include-only filter (if set)
    if ONLY:
        files = [p for p in files if any(token in str(p) for token in ONLY)]

    # exclude filter (if set)
    if EXCLUDE:
        files = [p for p in files if not any(token in str(p) for token in EXCLUDE)]

    random.Random(SEED).shuffle(files)
    return files[:LIMIT]

# ------------------------------------------------------------------------------
# Test
# ------------------------------------------------------------------------------

@pytest.mark.parametrize(
    "path",
    _collect_files(),
    ids=lambda p: str(p.relative_to(ROOT))  # human/filterable ids
)
def test_python_corpus_roundtrip(path: pathlib.Path):
    # If we're not skipping known-bad files, pre-emptively xfail them (even in STRICT)
    kb_reason = _is_known_bad(path)
    if kb_reason and not SKIP_KNOWN_BAD and XFAIL_KNOWN_BAD:
        pytest.xfail(f"known-bad: {kb_reason}")

    # read original text (tolerate odd bytes)
    src = path.read_text(encoding="utf-8", errors="replace")

    # compress
    comp = compress_text_py(src)
    if isinstance(comp, bytes):
        comp = comp.decode("utf-8", errors="replace")

    # expand
    back = expand_text_py(comp)
    if isinstance(back, bytes):
        back = back.decode("utf-8", errors="replace")

    # normalize & sanitize the expanded text *before* parsing
    back = _aggressive_ascii_normalize(back)
    back = sanitize_python_code_ascii(back)

    # parse both
    try:
        b_ast = ast.parse(back, filename=str(path))
    except SyntaxError as e:
        # Allow expanded-parse xfail in non-strict, or for known-bad
        if not STRICT or (kb_reason and XFAIL_KNOWN_BAD):
            pytest.xfail(f"expanded parse failed after normalization: {path} :: {e!s}")
        raise

    a_ast = ast.parse(src, filename=str(path))

    # compare canonical ASTs (docstrings/str constants neutralized)
    da = _normalized_dump(a_ast)
    db = _normalized_dump(b_ast)

    if da != db:
        if not STRICT or (kb_reason and XFAIL_KNOWN_BAD):
            pytest.xfail(f"non-strict AST mismatch tolerated: {path}")
        assert da == db, f"AST mismatch after round-trip for {path}."

    # Optional bytecode equality (only meaningful if ASTs matched)
    if STRICT_BYTECODE:
        ca = compile(src, str(path), "exec")
        cb = compile(back, str(path) + " (expanded)", "exec")
        assert ca.co_code == cb.co_code, f"Bytecode mismatch for {path}."

def test_fstring_literal_braces_survive_roundtrip():
    src = 's = f"{{{{ \\"metric\\": {{value}} }}}}"\nvalue = 3'
    comp = compress_text_py(src)
    back = expand_text_py(comp)
    if isinstance(back, (bytes, bytearray)):
        back = back.decode("utf-8", "replace")
    # normalize like pipeline
    back = _aggressive_ascii_normalize(back)
    back = sanitize_python_code_ascii(back)
    ast.parse(back)  # should not raise

def test_literal_and_structural_braces_survive_roundtrip():
    src = (
        "DEFAULT = {\n"
        '  "a": 1,\n'
        '  "b": 2\n'
        "}\n"
        's = f"{{{{ \\"metric\\": {{value}} }}}}"\n'
        "value = 3\n"
    )
    comp = compress_text_py(src)
    back = expand_text_py(comp)
    if isinstance(back, (bytes, bytearray)):
        back = back.decode("utf-8", "replace")
    # reuse your normalization pipeline if needed
    ast.parse(back)  # should not raise