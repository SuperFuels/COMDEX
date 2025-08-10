# backend/modules/collapse/collapse_trace_exporter.py
"""
📦 Collapse Trace Exporter
--------------------------------------
Exports HyperdriveEngine or SQI runtime state snapshots into `.dc.json`
format for symbolic replay, GHX visualization, or entanglement analysis.
"""

import os
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Tuple

EXPORT_DIR = Path("data/collapse_traces")
EXPORT_DIR.mkdir(parents=True, exist_ok=True)


def _safe_filename(stem: str) -> str:
    """Sanitize a filename stem (no path separators)."""
    return "".join(c for c in stem if c.isalnum() or c in ("-", "_")) or "trace"


def export_collapse_trace(state: Dict[str, Any], filename: str | None = None) -> str:
    """
    Export a collapse trace to disk in `.dc.json` format.

    Args:
        state: Engine or SQI state dictionary.
        filename: Optional filename stem or full name. If omitted, a timestamped
                  name is generated. If a stem is provided without extension,
                  `.dc.json` is appended.

    Returns:
        Full path to the saved file (str).
    """
    if filename is None:
        ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        filename = f"collapse_trace_{ts}.dc.json"
    else:
        # If only a stem was given, ensure the expected extension
        name = _safe_filename(Path(filename).stem)
        if not str(filename).endswith(".dc.json"):
            filename = f"{name}.dc.json"
        else:
            filename = f"{name}.dc.json"  # normalize stem anyway

    filepath = EXPORT_DIR / filename
    with filepath.open("w", encoding="utf-8") as f:
        json.dump(state, f, indent=4, ensure_ascii=False)

    print(f"💾 Collapse trace exported: {filepath}")
    return str(filepath)


def load_collapse_trace(filename: str) -> Dict[str, Any]:
    """
    Load a previously exported collapse trace from disk.

    Args:
        filename: Filename or full path to `.dc.json` trace.

    Returns:
        Loaded trace state (dict).
    """
    p = Path(filename)
    if not p.exists():
        p = EXPORT_DIR / filename
    if not p.exists():
        raise FileNotFoundError(f"Collapse trace not found: {p}")

    with p.open("r", encoding="utf-8") as f:
        trace = json.load(f)

    print(f"📂 Collapse trace loaded: {p}")
    return trace


# --- Listing helpers -------------------------------------------------------

def iter_collapse_trace_files(limit: int = 50) -> List[Tuple[str, float]]:
    """
    Return up to `limit` most recent collapse trace files (path, mtime).
    """
    if not EXPORT_DIR.exists():
        return []
    files = sorted(
        EXPORT_DIR.glob("*.dc.json"),
        key=lambda q: q.stat().st_mtime,
        reverse=True,
    )[: max(0, int(limit))]
    return [(str(p), p.stat().st_mtime) for p in files]


def get_recent_collapse_traces(limit: int = 50, load: bool = True) -> List[Dict[str, Any]]:
    """
    Return recent collapse traces. If load=True, parse JSON and include path/mtime.
    Otherwise returns metadata entries only.
    """
    results: List[Dict[str, Any]] = []
    for path, mtime in iter_collapse_trace_files(limit=limit):
        if load:
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if isinstance(data, dict):
                    data.setdefault("path", path)
                    data.setdefault("timestamp", mtime)
                    results.append(data)
                else:
                    results.append({"path": path, "timestamp": mtime, "data": data})
            except Exception:
                # Skip unreadable/corrupt files
                continue
        else:
            results.append({"path": path, "timestamp": mtime})
    return results


__all__ = [
    "export_collapse_trace",
    "load_collapse_trace",
    "iter_collapse_trace_files",
    "get_recent_collapse_traces",
]