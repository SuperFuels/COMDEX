from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Optional


_HASH_RE = r"[0-9a-f]{7}"
_TEST_RE = r"[A-Z]{1,4}\d{2,3}"


@dataclass(frozen=True)
class Pillar:
    key: str          # e.g. "gravity"
    name: str         # e.g. "GRAVITY"
    root: Path

    @property
    def artifacts(self) -> Path:
        return self.root / "artifacts"

    @property
    def audit_registry(self) -> Path:
        return self.root / "AUDIT_REGISTRY.md"

    @property
    def docs(self) -> Path:
        return self.root / "docs"


def add_parser(subparsers) -> None:
    p = subparsers.add_parser("report", help="Generate a markdown report (summary or per-anchor)")
    p.add_argument(
        "target",
        nargs="?",
        default=None,
        help="optional: pillar or pillar:TESTID (e.g. gravity or gravity:G02)",
    )
    p.add_argument("--md", action="store_true", help="emit markdown (default)")
    p.add_argument("-o", "--out", default="", help="Output path (default: stdout)")
    p.set_defaults(fn=run)


# ---------------- repo discovery ----------------

def _find_repo_root() -> Path:
    env = os.getenv("TESSARIS_REPO_ROOT")
    if env:
        return Path(env).resolve()

    p = Path.cwd().resolve()
    for _ in range(12):
        if (p / ".git").exists():
            return p
        p = p.parent
    return Path.cwd().resolve()


def _run_cmd(cmd: list[str], cwd: Optional[Path] = None) -> str:
    try:
        r = subprocess.run(cmd, cwd=str(cwd) if cwd else None, capture_output=True, text=True, check=False)
        out = (r.stdout or "").strip()
        if out:
            return out
        return (r.stderr or "").strip()
    except Exception:
        return ""


def _git_head(repo: Path) -> str:
    return _run_cmd(["git", "rev-parse", "HEAD"], cwd=repo) or "unknown"


def _git_branch(repo: Path) -> str:
    b = _run_cmd(["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=repo)
    return b or "unknown"


def _git_is_dirty(repo: Path) -> bool:
    s = _run_cmd(["git", "status", "--porcelain"], cwd=repo)
    return bool(s.strip())


# ---------------- pillars / anchors ----------------

def _pillars(repo: Path) -> dict[str, Pillar]:
    names = [
        "ENERGY",
        "GRAVITY",
        "INERTIA",
        "MAGNETISM",
        "TUNNEL",
        "CONNECTIVITY",
        "THERMO",
        "MATTER",
        "BRIDGE",
    ]
    out: dict[str, Pillar] = {}
    for n in names:
        d = repo / n
        if d.exists():
            out[n.lower()] = Pillar(key=n.lower(), name=n, root=d)
    return out


def _read_text_safe(p: Path) -> str:
    try:
        return p.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return ""


def _extract_pins_from_text(text: str) -> list[tuple[str, str, str]]:
    """
    Returns (test_id, run_hash, path_str) for pinned artifact paths found in markdown-ish text.
    Matches:
      .../artifacts/.../<TESTID>/<HASH>/
    """
    out: list[tuple[str, str, str]] = []
    rx = re.compile(
        rf"(?:^|[\s`])(?P<path>[^`\s]+/artifacts/[^`\s]+/(?P<test>{_TEST_RE})/(?P<hash>{_HASH_RE})/)"
    )
    for m in rx.finditer(text):
        out.append((m.group("test"), m.group("hash"), m.group("path")))
    return out


def _iter_run_dirs(artifacts_root: Path) -> Iterable[Path]:
    if not artifacts_root.exists():
        return
    for rj in artifacts_root.rglob("run.json"):
        yield rj.parent


def _discover_anchors(repo: Path) -> list[tuple[str, str]]:
    """
    Anchors are (pillar_key, TESTID). Prefer AUDIT_REGISTRY pins + augment with on-disk run.json.
    """
    anchors: set[tuple[str, str]] = set()
    for pkey, p in _pillars(repo).items():
        if p.audit_registry.exists():
            pins = _extract_pins_from_text(_read_text_safe(p.audit_registry))
            for test_id, _, _ in pins:
                anchors.add((pkey, test_id))

        for run_dir in _iter_run_dirs(p.artifacts):
            test_id = run_dir.parent.name
            if re.fullmatch(_TEST_RE, test_id):
                anchors.add((pkey, test_id))

    return sorted(anchors, key=lambda x: (x[0], x[1]))


def _latest_run_dir(p: Pillar, test_id: str) -> Optional[Path]:
    if not p.artifacts.exists():
        return None

    cands: list[Path] = []
    for rj in p.artifacts.rglob("run.json"):
        d = rj.parent
        if d.parent.name == test_id:
            cands.append(d)

    if not cands:
        return None

    def _mtime(d: Path) -> float:
        meta = d / "meta.json"
        try:
            return meta.stat().st_mtime if meta.exists() else d.stat().st_mtime
        except Exception:
            return 0.0

    cands.sort(key=_mtime, reverse=True)
    return cands[0]


def _load_run_json(run_dir: Path) -> dict:
    try:
        return json.loads((run_dir / "run.json").read_text(encoding="utf-8"))
    except Exception:
        return {}


def _parse_target(target: Optional[str]) -> tuple[Optional[str], Optional[str]]:
    """
    Returns (pillar_key, test_id). Either may be None.
      None -> (None, None)
      "gravity" -> ("gravity", None)
      "gravity:G02" -> ("gravity", "G02")
    """
    if not target:
        return None, None
    t = target.strip()
    if ":" in t:
        pk, tid = t.split(":", 1)
        return pk.strip().lower(), tid.strip()
    return t.lower(), None


# ---------------- report ----------------

def run(args) -> int:
    repo = _find_repo_root()
    pillars = _pillars(repo)

    pkey, test_id = _parse_target(getattr(args, "target", None))

    # filter anchors
    anchors = _discover_anchors(repo)
    if pkey:
        if pkey not in pillars:
            raise SystemExit(f"unknown pillar: {pkey}")
        anchors = [(pk, tid) for (pk, tid) in anchors if pk == pkey]
    if test_id:
        anchors = [(pk, tid) for (pk, tid) in anchors if tid == test_id]

    now = datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    head = _git_head(repo)
    branch = _git_branch(repo)
    dirty = _git_is_dirty(repo)

    md: list[str] = []
    title = "Tessaris Report" if not (pkey or test_id) else f"Tessaris Report: {pkey}{(':' + test_id) if test_id else ''}"
    md.append(f"# {title}")
    md.append("")
    md.append(f"- Generated: {now}")
    md.append(f"- Repo: `{repo}`")
    md.append(f"- Git: `{branch}` @ `{head}`")
    md.append(f"- Working tree: `{'DIRTY' if dirty else 'CLEAN'}`")
    md.append("")

    if not anchors:
        md.append("_No matching anchors found._")
        text = "\n".join(md)
        if getattr(args, "out", ""):
            Path(args.out).write_text(text, encoding="utf-8")
            print(args.out)
        else:
            print(text)
        return 0

    # summary bullets
    md.append("## Latest runs")
    md.append("")
    for pk, tid in anchors:
        p = pillars[pk]
        latest = _latest_run_dir(p, tid)
        if not latest:
            md.append(f"- **{pk}:{tid}** _(no run on disk)_")
            continue

        runj = _load_run_json(latest)
        h = runj.get("run_hash", latest.name)
        ctrl = runj.get("controller", "unknown")
        seed = runj.get("seed", None)
        md.append(f"- **{pk}:{tid}** `{h}` controller=`{ctrl}` seed=`{seed}`")
    md.append("")

    # if single anchor requested, include a small detail block
    if pkey and test_id and len(anchors) == 1:
        pk, tid = anchors[0]
        p = pillars[pk]
        latest = _latest_run_dir(p, tid)
        md.append("## Details")
        md.append("")
        if latest:
            md.append(f"- Artifacts: `{latest}`")
            runj = _load_run_json(latest)
            # show a few scalar metrics if present
            scalars = []
            for k, v in runj.items():
                if isinstance(v, (int, float)) and k not in ("seed",):
                    scalars.append((k, float(v)))
            scalars.sort(key=lambda kv: kv[0])
            if scalars:
                md.append("")
                md.append("### Scalars")
                md.append("")
                for k, v in scalars[:16]:
                    md.append(f"- `{k}` = `{v}`")
        else:
            md.append("_No artifacts found for this anchor on disk._")
        md.append("")

    text = "\n".join(md)

    outp = getattr(args, "out", "")
    if outp:
        Path(outp).write_text(text, encoding="utf-8")
        print(outp)
    else:
        print(text)
    return 0