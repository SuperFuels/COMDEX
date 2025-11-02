# -*- coding: utf-8 -*-
from __future__ import annotations
import os, sys, traceback
from types import TracebackType
from typing import Iterable, List, Optional

ENV = os.getenv("PHOTON_TB", "1").lower()
_ENABLED = ENV not in {"0", "false", "no"}

def _offset_for_file(filename: str) -> int:
    """Look up line_offset from any loaded module's __photonmap__."""
    try:
        import importlib.util, pathlib
        want = str(pathlib.Path(filename).resolve())
    except Exception:
        want = filename
    for m in list(sys.modules.values()):
        try:
            pmap = getattr(m, "__photonmap__", None)
            mf = getattr(m, "__file__", None)
            if not pmap or not mf:
                continue
            if str(mf) == want or str(pmap.get("source")) == want:
                return int(pmap.get("line_offset", 0))
        except Exception:
            continue
    return 0

def _adjust_frame_summary(fs: traceback.FrameSummary) -> traceback.FrameSummary:
    off = _offset_for_file(fs.filename)
    if off:
        # fs is immutable-ish; build a new one with adjusted lineno
        return traceback.FrameSummary(
            fs.filename, max(1, fs.lineno - off), fs.name, line=fs.line
        )
    return fs

def _format_exc(exc_type, exc, tb: Optional[TracebackType]) -> str:
    # Build adjusted stack
    frames = traceback.extract_tb(tb) if tb else []
    frames2 = [ _adjust_frame_summary(f) for f in frames ]
    lines: List[str] = []
    lines.append("Traceback (most recent call last):\n")
    lines.extend(traceback.format_list(frames2))
    lines.extend(traceback.format_exception_only(exc_type, exc))
    return "".join(lines)

def _excepthook(exc_type, exc, tb):
    try:
        sys.stderr.write(_format_exc(exc_type, exc, tb))
    except Exception:
        # Fallback to Python's default if anything goes wrong
        sys.__excepthook__(exc_type, exc, tb)

def install() -> None:
    if not _ENABLED:
        return
    # idempotent
    if getattr(sys, "_photon_tb_installed", False):
        return
    sys.excepthook = _excepthook
    sys._photon_tb_installed = True

# Optional helper for tests/tools
def format_exception(e: BaseException) -> str:
    return _format_exc(type(e), e, e.__traceback__)