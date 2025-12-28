from __future__ import annotations

import argparse
import os
import re
import shutil
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Optional


_HASH_RE = r"[0-9a-f]{7}"
_TEST_RE = r"[A-Z]{1,4}\d{2,3}"


@dataclass(frozen=True)
class Pin:
    test_id: str
    run_hash: str
    path: Path  # run dir (…/<TESTID>/<HASH>)


def add_parser(subparsers) -> None:
    # Adds: tessarisctl artifacts gc ...
    ap = subparsers.add_parser("artifacts", help="artifacts utilities")
    sub = ap.add_subparsers(dest="subcmd", required=True)

    gc = sub.add_parser("gc", help="garbage-collect artifact run dirs (dry-run by default)")
    gc.add_argument("--root", default=".", help="repo root (default: .)")
    gc.add_argument("--days", type=int, default=14, help="delete unpinned run dirs older than N days")
    gc.add_argument("--apply", action="store_true", help="actually delete (otherwise dry-run)")
    gc.add_argument("--dry-run", action="store_true", help="force dry-run (overrides --apply)")
    gc.add_argument("--limit", type=int, default=0, help="only show/delete first N candidates (0 = no limit)")
    gc.set_defaults(fn=gc_main)


def _find_repo_root(root_arg: str) -> Path:
    # prefer explicit --root; fall back to walking upward to a .git
    root = Path(root_arg).resolve()
    if (root / ".git").exists():
        return root
    p = Path.cwd().resolve()
    for _ in range(12):
        if (p / ".git").exists():
            return p
        p = p.parent
    return root


def _iter_audit_files(repo: Path) -> Iterable[Path]:
    # one level deep: GRAVITY/AUDIT_REGISTRY.md etc.
    yield from repo.glob("*/AUDIT_REGISTRY.md")


def _read_text_safe(p: Path) -> str:
    try:
        return p.read_text(encoding="utf-8", errors="ignore").replace("\r\n", "\n").replace("\r", "\n")
    except Exception:
        return ""


_PIN_RX = re.compile(
    rf"(?P<path>(?:/[^`\s]+|[^`\s]+)?/artifacts/[^`\s]+/(?P<test>{_TEST_RE})/(?P<hash>{_HASH_RE})/?)"
)


def _collect_pins(repo: Path) -> dict[Path, Pin]:
    """
    Returns mapping: run_dir_abs -> Pin
    Accepts pinned paths with or without trailing slash and with absolute or relative paths.
    """
    out: dict[Path, Pin] = {}
    for audit in _iter_audit_files(repo):
        text = _read_text_safe(audit)
        for m in _PIN_RX.finditer(text):
            raw = m.group("path").strip().strip("`").strip('"').strip("'")
            raw = raw.rstrip("/")  # normalize to run dir
            p = Path(raw)

            # normalize to absolute under repo if relative
            if not p.is_absolute():
                p = (repo / p).resolve()
            else:
                p = p.resolve()

            pin = Pin(test_id=m.group("test"), run_hash=m.group("hash"), path=p)
            out[p] = pin
    return out


def _iter_run_dirs_under_artifacts(repo: Path) -> Iterable[Path]:
    """
    A "run dir" is the parent of run.json anywhere under **/artifacts/**.
    """
    for rj in repo.rglob("run.json"):
        try:
            # ensure it's under an artifacts tree
            if "artifacts" not in rj.parts:
                continue
            yield rj.parent.resolve()
        except Exception:
            continue


def _run_dir_mtime(run_dir: Path) -> float:
    # prefer meta.json, else run.json, else dir
    meta = run_dir / "meta.json"
    if meta.exists():
        try:
            return meta.stat().st_mtime
        except Exception:
            pass
    rj = run_dir / "run.json"
    if rj.exists():
        try:
            return rj.stat().st_mtime
        except Exception:
            pass
    try:
        return run_dir.stat().st_mtime
    except Exception:
        return time.time()


def gc_main(args) -> int:
    repo = _find_repo_root(getattr(args, "root", "."))
    os.chdir(repo)

    days = int(getattr(args, "days", 14))
    apply = bool(getattr(args, "apply", False))
    dry_run = bool(getattr(args, "dry_run", False)) or (not apply)
    limit = int(getattr(args, "limit", 0))

    cutoff = time.time() - (days * 86400)

    pins = _collect_pins(repo)  # abs run_dir -> Pin
    pinned_dirs = set(pins.keys())

    scanned = 0
    candidates: list[Path] = []
    kept = 0

    for run_dir in _iter_run_dirs_under_artifacts(repo):
        scanned += 1

        # never delete pinned dirs
        if run_dir in pinned_dirs:
            kept += 1
            continue

        # only delete "old enough"
        if _run_dir_mtime(run_dir) >= cutoff:
            kept += 1
            continue

        candidates.append(run_dir)

    # optional limit (for safety/preview)
    if limit > 0:
        candidates = candidates[:limit]

    # report
    if dry_run:
        for p in candidates:
            print(f"DRY-RUN delete: {p}")
        print(f"artifacts gc (dry-run): scanned={scanned} would_delete={len(candidates)} kept={kept} pinned={len(pinned_dirs)}")
        return 0

    deleted = 0
    for p in candidates:
        shutil.rmtree(p, ignore_errors=True)
        print(f"deleted: {p}")
        deleted += 1

    print(f"artifacts gc: scanned={scanned} deleted={deleted} kept={kept} pinned={len(pinned_dirs)}")
    return 0