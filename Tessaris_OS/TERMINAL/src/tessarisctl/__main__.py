from __future__ import annotations

import argparse
import json
import os
import platform
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Optional


@dataclass(frozen=True)
class Pillar:
    name: str
    root: Path

    @property
    def src(self) -> Path:
        return self.root / "src"

    @property
    def tests(self) -> Path:
        return self.root / "tests"

    @property
    def artifacts(self) -> Path:
        return self.root / "artifacts"

    @property
    def audit_registry(self) -> Path:
        return self.root / "AUDIT_REGISTRY.md"

    @property
    def docs(self) -> Path:
        return self.root / "docs"


# ---------------- repo / pillars ----------------

def _find_repo_root() -> Path:
    env = os.getenv("TESSARIS_REPO_ROOT")
    if env:
        return Path(env).resolve()

    p = Path.cwd().resolve()
    for _ in range(10):
        if (p / ".git").exists():
            return p
        p = p.parent
    return Path.cwd().resolve()


def _pillars(repo: Path) -> dict[str, Pillar]:
    # canonical pillar dirs in this repo
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
            out[n.lower()] = Pillar(n, d)
    return out


def _iter_run_dirs(artifacts_root: Path) -> Iterable[Path]:
    if not artifacts_root.exists():
        return
    # run dirs are parents of run.json
    for rj in artifacts_root.rglob("run.json"):
        yield rj.parent


def _read_text_safe(p: Path) -> str:
    try:
        return p.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return ""


# ---------------- anchors ----------------

_HASH_RE = r"[0-9a-f]{7}"
_TEST_RE = r"[A-Z]{1,4}\d{2,3}"


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


def _discover_anchors(repo: Path) -> list[tuple[str, str]]:
    """
    Prefer anchors from AUDIT_REGISTRY.md (stable), then augment with anchors present on disk.
    Output: [(pillar_key, TESTID), ...] where pillar_key is lowercase pillar dir name.
    """
    anchors: set[tuple[str, str]] = set()
    for pkey, p in _pillars(repo).items():
        # 1) AUDIT_REGISTRY.md pins
        if p.audit_registry.exists():
            for test_id, _, _ in _extract_pins_from_text(_read_text_safe(p.audit_registry)):
                anchors.add((pkey, test_id))

        # 2) Anything present on disk (run.json)
        for run_dir in _iter_run_dirs(p.artifacts):
            test_id = run_dir.parent.name
            if re.fullmatch(_TEST_RE, test_id):
                anchors.add((pkey, test_id))

    return sorted(anchors, key=lambda x: (x[0], x[1]))


def _latest_run_dir(p: Pillar, test_id: str) -> Optional[Path]:
    root = p.artifacts
    if not root.exists():
        return None

    cands: list[Path] = []
    for rj in root.rglob("run.json"):
        d = rj.parent
        if d.parent.name == test_id:
            cands.append(d)

    if not cands:
        return None

    def _mtime(d: Path) -> float:
        meta = d / "meta.json"
        return meta.stat().st_mtime if meta.exists() else d.stat().st_mtime

    cands.sort(key=_mtime, reverse=True)
    return cands[0]


def _snapshot_run_dirs(p: Pillar) -> set[Path]:
    if not p.artifacts.exists():
        return set()
    return set(_iter_run_dirs(p.artifacts))


# ---------------- filesystem / opening ----------------

def _open_path(path: Path) -> None:
    s = str(path.resolve())
    system = platform.system().lower()
    if system == "darwin":
        subprocess.run(["open", s], check=False)
        return
    if system.startswith("win"):
        subprocess.run(["explorer", s], check=False)
        return
    if shutil.which("xdg-open"):
        subprocess.run(["xdg-open", s], check=False)
        return
    print(s)


# ---------------- pytest running ----------------

def _find_pytests_for_anchor(tests_root: Path, test_id: str) -> list[Path]:
    if not tests_root.exists():
        return []
    hits: list[Path] = []
    pat = re.compile(rf'["\']{re.escape(test_id)}["\']')
    for fp in tests_root.rglob("test_*.py"):
        s = _read_text_safe(fp)
        if test_id in s or pat.search(s):
            hits.append(fp)
    return sorted(hits)


def _run_pytest(p: Pillar, test_id: Optional[str], seed: Optional[int], no_artifacts: bool) -> int:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(p.src.resolve())

    # advisory knobs (won’t break anything if ignored)
    if seed is not None:
        env["TESSARIS_SEED"] = str(int(seed))

    if no_artifacts:
        env["TESSARIS_WRITE_ARTIFACTS"] = "0"
        env["TESSARIS_EMIT_TELEMETRY"] = "0"
        env["TESSARIS_EMIT_FIELD"] = "0"
    else:
        env.setdefault("TESSARIS_EMIT_TELEMETRY", "1")
        env.setdefault("TESSARIS_EMIT_FIELD", "1")

    args = [sys.executable, "-m", "pytest"]
    if test_id:
        files = _find_pytests_for_anchor(p.tests, test_id)
        args += [str(f) for f in files] if files else [str(p.tests)]
    else:
        args += [str(p.tests)]
    args += ["-q"]

    print("RUN:", " ".join(args))
    r = subprocess.run(args, env=env)
    return int(r.returncode)


def _print_run_summary(run_dir: Path) -> None:
    rj = run_dir / "run.json"
    if not rj.exists():
        print("no run.json:", run_dir)
        return

    run = json.loads(rj.read_text(encoding="utf-8"))
    test_id = run.get("test_id", run_dir.parent.name)
    run_hash = run.get("run_hash", run_dir.name)
    ctrl = run.get("controller", "unknown")
    seed = run.get("seed", None)

    scalars: list[tuple[str, float]] = []
    for k, v in run.items():
        if isinstance(v, (int, float)) and k not in ("seed",):
            scalars.append((k, float(v)))
    scalars.sort(key=lambda kv: kv[0])

    print(f"{test_id} {run_hash} controller={ctrl} seed={seed}")
    for k, v in scalars[:12]:
        print(f"  {k} = {v}")


# ---------------- commands ----------------

def cmd_list(repo: Path) -> int:
    for p, tid in _discover_anchors(repo):
        print(f"{p}:{tid}")
    return 0


def cmd_run(repo: Path, target: str, seed: Optional[int], no_artifacts: bool) -> int:
    pillars = _pillars(repo)
    if ":" in target:
        pkey, test_id = target.split(":", 1)
        test_id = test_id.strip()
    else:
        pkey, test_id = target, ""
    pkey = pkey.strip().lower()

    if pkey not in pillars:
        raise SystemExit(f"unknown pillar: {pkey}")

    p = pillars[pkey]

    before = _snapshot_run_dirs(p) if no_artifacts else set()

    rc = _run_pytest(p, test_id or None, seed=seed, no_artifacts=no_artifacts)
    if rc != 0:
        return rc

    if no_artifacts:
        after = _snapshot_run_dirs(p)
        created = sorted(after - before)
        for d in created:
            shutil.rmtree(d, ignore_errors=True)
        print(f"no-artifacts: removed {len(created)} new run dir(s)")
        return 0

    if test_id:
        latest = _latest_run_dir(p, test_id)
        if latest:
            _print_run_summary(latest)
            print("latest artifacts:", latest)
    return 0


def cmd_artifacts_open(repo: Path, target: str) -> int:
    pillars = _pillars(repo)
    if ":" not in target:
        raise SystemExit("use: pillar:TESTID (e.g. bridge:BG01)")
    pkey, test_id = target.split(":", 1)
    pkey = pkey.strip().lower()
    test_id = test_id.strip()

    if pkey not in pillars:
        raise SystemExit(f"unknown pillar: {pkey}")

    p = pillars[pkey]
    latest = _latest_run_dir(p, test_id)
    if not latest:
        raise SystemExit(f"no run found for {p.name}:{test_id}")

    print(latest)
    _open_path(latest)
    return 0


def cmd_registry_verify(repo: Path) -> int:
    """
    Verify:
      - pinned artifact paths in AUDIT_REGISTRY.md exist on disk and contain run.json
      - each pinned hash appears at least twice across AUDIT_REGISTRY.md + docs/*.md
        (i.e., not only inside the path literal; must be mentioned in an evidence/summary line)
    """
    bad = 0
    pillars = _pillars(repo)

    for _, p in pillars.items():
        audit = p.audit_registry
        if not audit.exists():
            continue

        audit_text = _read_text_safe(audit)
        pins = _extract_pins_from_text(audit_text)
        if not pins:
            continue

        docs_text = ""
        if p.docs.exists():
            for md in p.docs.rglob("*.md"):
                docs_text += _read_text_safe(md) + "\n"

        # de-dupe pins so verify output is clean
        seen: set[tuple[str, str, str]] = set()
        for test_id, h, path_str in pins:
            key = (test_id, h, path_str)
            if key in seen:
                continue
            seen.add(key)

            rel = path_str.lstrip("./")
            disk = (repo / rel).resolve()

            ok = disk.exists() and (disk / "run.json").exists()
            if not ok:
                bad += 1
                print(f"FAIL missing on disk: {disk}")

            mentions = audit_text.count(h) + docs_text.count(h)
            if mentions < 2:
                bad += 1
                print(f"FAIL not evidenced (hash only appears {mentions}x): {p.name} {test_id} {h}")

    if bad == 0:
        print("OK registry verify")
        return 0
    return 2


# ---------------- main ----------------

def main(argv: Optional[list[str]] = None) -> int:
    repo = _find_repo_root()

    ap = argparse.ArgumentParser(prog="tessarisctl")
    sub = ap.add_subparsers(dest="cmd", required=True)

    sp = sub.add_parser("list", help="list available anchors (pillar:TESTID)")
    sp.set_defaults(fn=lambda a: cmd_list(repo))

    sp = sub.add_parser("run", help="run an anchor via pytest (pillar:TESTID)")
    sp.add_argument("target", help="e.g. bridge:BG01")
    sp.add_argument("--seed", type=int, default=None)
    sp.add_argument("--no-artifacts", action="store_true")
    sp.set_defaults(fn=lambda a: cmd_run(repo, a.target, a.seed, a.no_artifacts))

    sp = sub.add_parser("artifacts", help="artifacts utilities")
    sub2 = sp.add_subparsers(dest="subcmd", required=True)

    sp2 = sub2.add_parser("open", help="open latest artifact folder for anchor")
    sp2.add_argument("target", help="e.g. gravity:G01")
    sp2.set_defaults(fn=lambda a: cmd_artifacts_open(repo, a.target))

    sp = sub.add_parser("registry", help="registry utilities")
    sub3 = sp.add_subparsers(dest="subcmd", required=True)

    sp3 = sub3.add_parser("verify", help="verify pinned hashes exist + are evidenced")
    sp3.set_defaults(fn=lambda a: cmd_registry_verify(repo))

    args = ap.parse_args(argv)
    return int(args.fn(args))


if __name__ == "__main__":
    raise SystemExit(main())