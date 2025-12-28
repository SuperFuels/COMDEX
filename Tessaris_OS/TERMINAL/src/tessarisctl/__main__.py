from __future__ import annotations
import time
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
from tessarisctl.commands import artifacts_gc

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


def _latest_n_run_dirs(p: Pillar, test_id: str, n: int) -> list[Path]:
    root = p.artifacts
    if not root.exists():
        return []

    cands: list[Path] = []
    for rj in root.rglob("run.json"):
        d = rj.parent
        if d.parent.name == test_id:
            cands.append(d)

    if not cands:
        return []

    def _mtime(d: Path) -> float:
        meta = d / "meta.json"
        return meta.stat().st_mtime if meta.exists() else d.stat().st_mtime

    cands.sort(key=_mtime, reverse=True)
    return cands[: max(0, int(n))]


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


# ---------------- git helpers ----------------

def _git(repo: Path, *args: str) -> tuple[int, str]:
    r = subprocess.run(
        ["git", "-C", str(repo), *args],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        check=False,
    )
    return int(r.returncode), (r.stdout or "").strip()


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


def cmd_status(repo: Path) -> int:
    pillars = _pillars(repo)
    print(f"repo: {repo}")
    print(f"python: {sys.version.split()[0]}  platform: {platform.platform()}")

    rc, branch = _git(repo, "rev-parse", "--abbrev-ref", "HEAD")
    if rc == 0 and branch:
        print(f"git: {branch}")
    rc, porcelain = _git(repo, "status", "--porcelain")
    if rc == 0:
        dirty = 1 if porcelain.strip() else 0
        changed = len([ln for ln in porcelain.splitlines() if ln.strip()])
        print(f"working-tree: {'DIRTY' if dirty else 'CLEAN'} ({changed} change(s))")

    print("pillars:")
    for k, p in sorted(pillars.items(), key=lambda kv: kv[0]):
        flags = []
        if p.src.exists():
            flags.append("src")
        if p.tests.exists():
            flags.append("tests")
        if p.audit_registry.exists():
            flags.append("audit")
        if p.artifacts.exists():
            flags.append("artifacts")
        print(f"  - {k}:{p.name} [{', '.join(flags) if flags else 'missing'}]")

    return 0


def _find_trailing_space_paths(repo: Path) -> list[Path]:
    out: list[Path] = []
    for p in repo.rglob("*"):
        # skip .git contents
        if ".git" in p.parts:
            continue
        if p.name.endswith(" "):
            out.append(p)
    return out


def cmd_doctor(repo: Path, quick: bool) -> int:
    bad = 0
    pillars = _pillars(repo)

    # 1) obvious filesystem hazards
    trailing = _find_trailing_space_paths(repo)
    if trailing:
        bad += 1
        print("FAIL trailing-space paths detected:")
        for p in trailing[:200]:
            print(f"  - {p}")
        if len(trailing) > 200:
            print(f"  ... and {len(trailing) - 200} more")

    # 2) basic structure
    for k, p in pillars.items():
        if not p.src.exists():
            bad += 1
            print(f"FAIL missing src/: {p.name} ({k})")
        if not p.tests.exists():
            bad += 1
            print(f"FAIL missing tests/: {p.name} ({k})")

    # 3) compile tessarisctl entrypoint (fast sanity)
    entry = repo / "Tessaris_OS" / "TERMINAL" / "src" / "tessarisctl" / "__main__.py"
    if entry.exists():
        r = subprocess.run([sys.executable, "-m", "py_compile", str(entry)], check=False)
        if r.returncode != 0:
            bad += 1
            print("FAIL py_compile tessarisctl/__main__.py")
    else:
        bad += 1
        print(f"FAIL missing: {entry}")

    # 4) registry verify (unless quick)
    if not quick:
        rc = cmd_registry_verify(repo)
        if rc != 0:
            bad += 1

    if bad == 0:
        print("OK doctor")
        return 0
    return 2


def _pinned_run_dirs(repo: Path, p: Pillar) -> set[Path]:
    keep: set[Path] = set()
    if not p.audit_registry.exists():
        return keep
    pins = _extract_pins_from_text(_read_text_safe(p.audit_registry))
    for test_id, h, path_str in pins:
        rel = path_str.lstrip("./")
        d = (repo / rel).resolve()
        # normalize to run dir (…/<TESTID>/<HASH>)
        if d.exists():
            keep.add(d)
    return keep


def cmd_artifacts_gc(
    repo: Path,
    pillar: Optional[str],
    days: int,
    dry_run: bool,
    keep_latest: int,
    keep_pinned: bool,
) -> int:
    pillars = _pillars(repo)

    # choose pillars to scan
    if pillar:
        key = pillar.strip().lower()
        if key not in pillars:
            raise SystemExit(f"unknown pillar: {pillar}")
        targets: dict[str, Pillar] = {key: pillars[key]}
    else:
        targets = pillars

    keep: set[Path] = set()

    # keep pinned
    if keep_pinned:
        for _, p in targets.items():
            keep |= _pinned_run_dirs(repo, p)

    # keep latest N per discovered anchor (per pillar)
    for pkey, p in targets.items():
        for _, test_id in [a for a in _discover_anchors(repo) if a[0] == pkey]:
            for d in _latest_n_run_dirs(p, test_id, keep_latest):
                keep.add(d.resolve())

    cutoff = (time.time() - (max(0, int(days)) * 86400)) if days is not None else 0.0

    removed = 0
    scanned = 0
    would_delete = 0

    for _, p in targets.items():
        for run_dir in _iter_run_dirs(p.artifacts):
            scanned += 1
            rd = run_dir.resolve()

            if rd in keep:
                continue

            # age filter (only delete things older than N days)
            try:
                mtime = rd.stat().st_mtime
            except FileNotFoundError:
                continue
            if cutoff and mtime >= cutoff:
                continue

            if dry_run:
                would_delete += 1
                print(f"DRY-RUN delete: {rd}")
                continue

            shutil.rmtree(rd, ignore_errors=True)
            removed += 1
            print(f"deleted: {rd}")

    if dry_run:
        print(f"artifacts gc (dry-run): scanned={scanned} would_delete={would_delete} kept={len(keep)}")
        return 0

    print(f"artifacts gc: scanned={scanned} deleted={removed} kept={len(keep)}")
    return 0


def cmd_report(repo: Path, md: bool, target: str = "") -> int:
    pillars = _pillars(repo)

    # If target provided, only report that one anchor.
    if target:
        if ":" not in target:
            raise SystemExit("use: report pillar:TESTID (e.g. report gravity:G02)")
        pkey, test_id = target.split(":", 1)
        pkey = pkey.strip().lower()
        test_id = test_id.strip()
        anchors = [(pkey, test_id)]
    else:
        anchors = _discover_anchors(repo)

    if md:
        title = f"# Tessaris Report: {target}" if target else "# Tessaris Report"
        print(title)
        print("")

    for pkey, test_id in anchors:
        if pkey not in pillars:
            if md:
                print(f"- **{pkey}:{test_id}** — _unknown pillar_")
            else:
                print(f"{pkey}:{test_id}: unknown pillar")
            continue

        p = pillars[pkey]
        latest = _latest_run_dir(p, test_id)
        if not latest:
            if md:
                print(f"- **{pkey}:{test_id}** — _no run found_")
            else:
                print(f"{pkey}:{test_id}: no run found")
            continue

        rj = latest / "run.json"
        if not rj.exists():
            if md:
                print(f"- **{pkey}:{test_id}** — _missing run.json_ ({latest})")
            else:
                print(f"{pkey}:{test_id}: missing run.json ({latest})")
            continue

        run = json.loads(rj.read_text(encoding="utf-8"))
        run_hash = run.get("run_hash", latest.name)
        ctrl = run.get("controller", "unknown")
        seed = run.get("seed", None)

        if md:
            print(f"- **{pkey}:{test_id}** `{run_hash}` controller=`{ctrl}` seed=`{seed}`")
        else:
            print(f"{pkey}:{test_id} {run_hash} controller={ctrl} seed={seed}")

    return 0


# ---------------- main ----------------

def main(argv: Optional[list[str]] = None) -> int:
    repo = _find_repo_root()

    ap = argparse.ArgumentParser(prog="tessarisctl")
    sub = ap.add_subparsers(dest="cmd", required=True)

    # list
    sp = sub.add_parser("list", help="list available anchors (pillar:TESTID)")
    sp.set_defaults(fn=lambda a: cmd_list(repo))

    # status
    sp = sub.add_parser("status", help="show repo + pillars + basic health")
    sp.set_defaults(fn=lambda a: cmd_status(repo))

    # doctor
    sp = sub.add_parser("doctor", help="health checks (registry verify, path hazards, basic compile)")
    sp.add_argument("--quick", action="store_true", help="skip slower checks (e.g. registry verify)")
    sp.set_defaults(fn=lambda a: cmd_doctor(repo, a.quick))

    # report
    sp = sub.add_parser("report", help="summarize latest runs (optionally for one anchor)")
    sp.add_argument("target", nargs="?", default="", help="optional: e.g. gravity:G02")
    sp.add_argument("--md", action="store_true", help="emit markdown")
    sp.set_defaults(fn=lambda a: cmd_report(repo, a.md, a.target))

    # run
    sp = sub.add_parser("run", help="run an anchor via pytest (pillar:TESTID)")
    sp.add_argument("target", help="e.g. bridge:BG01")
    sp.add_argument("--seed", type=int, default=None)
    sp.add_argument("--no-artifacts", action="store_true")
    sp.set_defaults(fn=lambda a: cmd_run(repo, a.target, a.seed, a.no_artifacts))

    # artifacts
    sp = sub.add_parser("artifacts", help="artifacts utilities")
    sub2 = sp.add_subparsers(dest="subcmd", required=True)

    sp2 = sub2.add_parser("open", help="open latest artifact folder for anchor")
    sp2.add_argument("target", help="e.g. gravity:G01")
    sp2.set_defaults(fn=lambda a: cmd_artifacts_open(repo, a.target))

    sp2 = sub2.add_parser("gc", help="garbage-collect old artifact runs")
    sp2.add_argument("--pillar", default=None, help="limit to one pillar (e.g. gravity)")
    sp2.add_argument("--days", type=int, default=14, help="only delete runs older than N days (default: 14)")
    sp2.add_argument("--apply", action="store_true", help="actually delete (otherwise dry-run)")
    sp2.add_argument("--keep-latest", type=int, default=2, help="keep N latest per anchor (default: 2)")
    sp2.add_argument("--no-keep-pinned", action="store_true", help="do not keep pinned runs from AUDIT_REGISTRY")
    sp2.set_defaults(
        fn=lambda a: cmd_artifacts_gc(
            repo,
            pillar=a.pillar,
            days=a.days,
            dry_run=(not a.apply),
            keep_latest=a.keep_latest,
            keep_pinned=(not a.no_keep_pinned),
        )
    )

    # registry
    sp = sub.add_parser("registry", help="registry utilities")
    sub3 = sp.add_subparsers(dest="subcmd", required=True)

    sp3 = sub3.add_parser("verify", help="verify pinned hashes exist + are evidenced")
    sp3.set_defaults(fn=lambda a: cmd_registry_verify(repo))

    args = ap.parse_args(argv)
    return int(args.fn(args))


if __name__ == "__main__":
    raise SystemExit(main())