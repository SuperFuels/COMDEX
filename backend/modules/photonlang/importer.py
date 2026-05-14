# -*- coding: utf-8 -*-
from __future__ import annotations
from textwrap import dedent
import ast
import hashlib

"""
Photon importer: load modules written in compressed Photon form.

Features
- Recognizes *.photon and *.pthon files (modules and packages).
- Expands Photon glyph tokens -> Python tokens.
- Optionally expands Symatics ops (if translator is present).
- Normalizes ASCII punctuation like the test pipeline.
- Sanitizes code tokens to ASCII-safe forms.

Env flags
- PHOTON_IMPORT=1         : (used by runtime wrapper) auto-installs importer
- PHOTON_IMPORT_BYPASS=1  : compile raw .photon text as-is (debug)
- PHOTON_IMPORT_STRICT=1  : error if any code-glyphs remain after expansion
"""

import os
import re
import sys
import unicodedata
import importlib.abc
import importlib.machinery
import importlib.util
from pathlib import Path
from types import ModuleType
from typing import Any

# ----------------------------- helpers ---------------------------------

def _expand_python_tokens(src: str) -> str:
    """Expand code glyphs -> pure Python tokens (reversible)."""
    from backend.modules.photonlang.adapters.python_tokens import expand_text_py
    return expand_text_py(src)

def _maybe_expand_symatics_ops(src: str) -> str:
    """
    Optional: expand Symatics ops (⊕, μ, ↔, ⟲, π, ...) into Python calls.
    If translator layer isn't present, just return src unchanged.
    """
    try:
        from backend.modules.photonlang.translator import expand_symatics_ops  # type: ignore
        return expand_symatics_ops(src)
    except Exception:
        return src

def _to_str(data: bytes | str) -> str:
    if isinstance(data, (bytes, bytearray)):
        return data.decode("utf-8", errors="replace")
    return str(data)

# --- normalization + sanitize (mirror test pipeline) --------------------

# from backend.utils.code_sanitize import sanitize_python_code_ascii

_ASCII_TABLE = {
    # dashes/minus
    ord("−"): "-", ord("–"): "-", ord("—"): "-", ord("‒"): "-",
    0x2010: "-", 0x2011: "-", 0x2212: "-", 0x00AD: "",

    # spaces & joiners
    ord("\u00A0"): " ",  # NBSP
    ord("\u202F"): " ",  # NNBSP
    ord("\u2009"): " ", ord("\u200A"): " ", ord("\u2007"): " ",
    ord("\u2060"): "",   # word joiner
    0x2000: " ", 0x2001: " ",

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
    0x00B7: "*",
    0x2215: "/", 0x2044: "/",
    0x2217: "*", 0x22C5: "*",
    0x00F7: "/",
}

_OP_REPLS = [
    (r"[≤≦]", "<="),
    (r"[≥≧]", ">="),
    (r"≠", "!="),
    (r"[×∗·]", "*"),
    (r"[÷∕]", "/"),
]

def _normalize(src: str) -> str:
    # 1) NFKC fold (ｅ → e, － → -)
    s = unicodedata.normalize("NFKC", src)
    # 2) direct codepoint translations
    s = s.translate(_ASCII_TABLE)
    # 3) regex multi-char operator replacements
    for pat, repl in _OP_REPLS:
        s = re.sub(pat, repl, s)
    # 4) join dotted attribute access / floats: "np . linspace" → "np.linspace"
    s = re.sub(r'([A-Za-z0-9_])\s*\.\s*([A-Za-z0-9_])', r'\1.\2', s)
    # 5) glue scientific notation: "1 e − 9" → "1e-9"
    s = re.sub(
        r'(?<=\d)\s*([eE])\s*([+\-]?)\s*(\d+)',
        lambda m: f"{m.group(1).lower()}{m.group(2)}{m.group(3)}",
        s,
    )
    return s

def _policy_check(raw_src: str, py_src: str, path: str) -> None:
    """
    Enforce simple, dependency-free policy:
      • Host import allow-list (via PHOTON_HOST_ALLOW / PHOTON_HOST_DENY)
      • Optional SHA256 gating (PHOTON_SIG_SHA256 or companion .sha256 file)
    """
    # ---- signature / integrity (optional) ----
    expected_hex = os.getenv("PHOTON_SIG_SHA256", "").strip().lower()
    if not expected_hex:
        sig_path = path + ".sha256"
        if os.path.exists(sig_path):
            try:
                expected_hex = Path(sig_path).read_text(encoding="utf-8").strip().lower()
            except Exception:
                expected_hex = ""

    if expected_hex:
        got = hashlib.sha256(raw_src.encode("utf-8")).hexdigest().lower()
        if got != expected_hex:
            raise ImportError(f"SHA256 mismatch for {path} (policy)")

    # ---- host import allow/deny (optional; defaults are lenient but safe) ----
    allow_csv = os.getenv(
        "PHOTON_HOST_ALLOW",
        # allow common stdlib + our own tree
        "backend,math,random,re,typing,dataclasses,json,collections,functools,itertools"
    )
    deny_csv = os.getenv("PHOTON_HOST_DENY", "")

    allow = [p.strip() for p in allow_csv.split(",") if p.strip()]
    deny  = [p.strip() for p in deny_csv.split(",") if p.strip()]

    def _ok(mod: str) -> bool:
        if any(mod == d or mod.startswith(d + ".") for d in deny):
            return False
        return any(mod == a or mod.startswith(a + ".") for a in allow)

    try:
        tree = ast.parse(py_src, filename=path)
    except SyntaxError:
        # Let the normal compiler raise; policy isn’t the blocker here.
        return

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for n in node.names:
                m = n.name
                # top-level package (keep full too, so prefixes work)
                head = m.split(".", 1)[0]
                if not _ok(m) and not _ok(head):
                    raise ImportError(f"host import not allowed by policy: {m}")
        elif isinstance(node, ast.ImportFrom):
            # relative imports within package are allowed
            if getattr(node, "level", 0):
                continue
            m = node.module or ""
            head = m.split(".", 1)[0] if m else ""
            if m and not _ok(m) and not _ok(head):
                raise ImportError(f"host import not allowed by policy: from {m} import …")

# ----------------------------- loader -----------------------------------

class PhotonSourceLoader(importlib.abc.SourceLoader):
    def __init__(self, fullname: str, path: str):
        self.fullname = fullname
        self.path = path

    def get_filename(self, fullname: str) -> str:  # noqa: ARG002
        return self.path

    def get_data(self, path: str) -> bytes:  # type: ignore[override]
        return Path(path).read_bytes()

    def source_to_code(self, data: bytes, path: str, _opt: Any = None):  # <-- INSIDE CLASS
        raw = _to_str(data)

        if os.getenv("PHOTON_IMPORT_BYPASS", "0") == "1":
            py_src = raw
        else:
            py_src = _expand_python_tokens(raw)
            py_src = _maybe_expand_symatics_ops(py_src)

            if os.getenv("PHOTON_IMPORT_STRICT", "0") == "1":
                from backend.modules.photonlang.adapters.python_tokens import contains_code_glyphs
                if contains_code_glyphs(py_src):
                    raise SyntaxError("PHOTON_IMPORT_STRICT: code glyphs remain after expansion")

            # normalize + sanitize (lazy import for sanitize)
            py_src = _normalize(py_src)
            try:
                from backend.utils.code_sanitize import sanitize_python_code_ascii as _sanitize
            except Exception:
                def _sanitize(s: str) -> str: return s
            py_src = _sanitize(py_src)
            py_src = dedent(py_src).lstrip()

            _policy_check(raw, py_src, path)

            prolog_injected = ("__OPS__" not in raw) and ("__OPS__" in py_src)
            self._photonmap = {
                "source": path,
                "version": 1,
                "mapping": "identity-lines",
                "line_offset": 1 if prolog_injected else 0,
            }

        return compile(py_src, path, "exec", dont_inherit=True, optimize=-1)

    def create_module(self, spec):
        return None

    def exec_module(self, module: ModuleType) -> None:
        code = self.get_code(module.__name__)
        pmap = getattr(self, "_photonmap", None)
        if pmap is not None:
            module.__dict__["__photonmap__"] = pmap
        exec(code, module.__dict__)

# ----------------------------- registration --------------------------------
# ----------------------------- registration (meta-finder) ----------------------
class PhotonMetaFinder(importlib.abc.MetaPathFinder):
    SUFFIXES = (".photon", ".pthon")

    def find_spec(self, fullname, path, target=None):  # type: ignore[override]
        search_paths = path if path is not None else sys.path
        rel = fullname.replace(".", "/")

        for base in search_paths:
            basepath = Path(base)
            try:
                # Package: <base>/<rel>/__init__.<ext>
                for ext in self.SUFFIXES:
                    pkg_init = basepath / rel / ("__init__" + ext)
                    if pkg_init.is_file():
                        loader = PhotonSourceLoader(fullname, str(pkg_init))
                        return importlib.util.spec_from_file_location(
                            fullname, str(pkg_init), loader=loader,
                            submodule_search_locations=[str(pkg_init.parent)]
                        )
                # Module: <base>/<rel>.<ext>
                for ext in self.SUFFIXES:
                    mod = basepath / (rel + ext)
                    if mod.is_file():
                        loader = PhotonSourceLoader(fullname, str(mod))
                        return importlib.util.spec_from_file_location(
                            fullname, str(mod), loader=loader
                        )
            except Exception:
                continue
        return None

# ... keep everything above unchanged ...

# ----------------------------- registration --------------------------------
def register_photon_importer() -> bool:
    """
    Install a FileFinder path hook that supports *.photon/*.pthon alongside
    the default Python/extension loaders. Startup-safe and idempotent.
    """
    from importlib.machinery import (
        FileFinder,
        SourceFileLoader,
        SourcelessFileLoader,
        ExtensionFileLoader,
        SOURCE_SUFFIXES,
        BYTECODE_SUFFIXES,
        EXTENSION_SUFFIXES,
    )

    loader_details = (
        (PhotonSourceLoader, [".photon", ".pthon"]),
        (SourceFileLoader, list(SOURCE_SUFFIXES)),
        (SourcelessFileLoader, list(BYTECODE_SUFFIXES)),
        (ExtensionFileLoader, list(EXTENSION_SUFFIXES)),
    )

    hook = FileFinder.path_hook(*loader_details)
    setattr(hook, "_tessaris_photon_hook", True)  # sentinel

    # Idempotent insert; DO NOT touch importlib caches here.
    if not any(getattr(h, "_tessaris_photon_hook", False) for h in sys.path_hooks):
        sys.path_hooks.insert(0, hook)
    return True


def unregister_photon_importer() -> bool:
    before = len(sys.path_hooks)
    sys.path_hooks[:] = [h for h in sys.path_hooks if not getattr(h, "_tessaris_photon_hook", False)]
    # no cache clearing; importlib will rebuild lazily
    return len(sys.path_hooks) != before


def refresh_importers() -> None:
    """
    Safely re-scan sys.path so *.photon suffixes are recognized for entries
    that already had a FileFinder cached before our hook was installed.
    """
    import importlib as _il
    _il.invalidate_caches()
    try:
        keys = list(sys.path_importer_cache.keys())
    except Exception:
        return
    for k in keys:
        try:
            sys.path_importer_cache.pop(k, None)
        except Exception:
            # Never break import pipeline on refresh
            pass


def install() -> bool:
    return register_photon_importer()


def uninstall() -> bool:
    return unregister_photon_importer()

__all__ = [
    "register_photon_importer",
    "unregister_photon_importer",
    "refresh_importers",
    "PhotonSourceLoader",
    "install",
    "uninstall",
]