# -*- coding: utf-8 -*-
from __future__ import annotations
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

from backend.utils.code_sanitize import sanitize_python_code_ascii

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

# ----------------------------- loader -----------------------------------

class PhotonSourceLoader(importlib.abc.SourceLoader):
    """
    Loads and expands *.photon / *.pthon modules:
      1) code glyph tokens -> Python tokens
      2) Symatics ops -> runtime calls (optional)
      3) normalize + sanitize (ASCII-safe tokens)
    Then compiles the expanded Python.
    """
    def __init__(self, fullname: str, path: str):
        self.fullname = fullname
        self.path = path

    def get_filename(self, fullname: str) -> str:  # noqa: ARG002
        return self.path

    def get_data(self, path: str) -> bytes:  # type: ignore[override]
        return Path(path).read_bytes()

    def source_to_code(self, data: bytes, path: str, _opt: Any = None):  # type: ignore[override]
        raw = _to_str(data)

        # Bypass: import raw Photon text (debug)
        if os.getenv("PHOTON_IMPORT_BYPASS", "0") == "1":
            py_src = raw
        else:
            # 1) expand code-glyph tokens -> Python tokens
            py_src = _expand_python_tokens(raw)
            # 2) expand Symatics ops -> runtime calls (optional)
            py_src = _maybe_expand_symatics_ops(py_src)

            # Strict mode: ensure no code-glyphs remain
            if os.getenv("PHOTON_IMPORT_STRICT", "0") == "1":
                from backend.modules.photonlang.adapters.python_tokens import contains_code_glyphs
                if contains_code_glyphs(py_src):
                    raise SyntaxError("PHOTON_IMPORT_STRICT: code glyphs remain after expansion")

            # 3) normalize & sanitize like tests do
            py_src = _normalize(py_src)
            py_src = sanitize_python_code_ascii(py_src)

        return compile(py_src, path, "exec", dont_inherit=True, optimize=-1)

    def create_module(self, spec):  # noqa: D401
        """Default module creation."""
        return None

    def exec_module(self, module: ModuleType) -> None:
        code = self.get_code(module.__name__)
        exec(code, module.__dict__)

# ----------------------------- registration --------------------------------

def register_photon_importer() -> None:
    """
    Install a FileFinder path hook that supports *.photon/*.pthon alongside
    the default Python/extension loaders. Keeps default behavior intact.
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

    if not any(getattr(h, "_tessaris_photon_hook", False) for h in sys.path_hooks):
        sys.path_hooks.insert(0, hook)
        sys.path_importer_cache.clear()

def unregister_photon_importer() -> None:
    """
    Remove the Photon path hook and clear the importer cache so future imports
    use default behavior only.
    """
    # Drop our sentinel-marked hooks
    sys.path_hooks[:] = [h for h in sys.path_hooks if not getattr(h, "_tessaris_photon_hook", False)]
    # Clear importer cache so Python rebuilds FileFinders without our hook
    sys.path_importer_cache.clear()

# Register at import time (idempotent by sentinel)
register_photon_importer()

__all__ = ["register_photon_importer", "unregister_photon_importer", "PhotonSourceLoader"]