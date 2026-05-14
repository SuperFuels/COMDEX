#!/usr/bin/env python3
"""
Run an AION demo script YAML (Phase 6).

- Creates isolated DATA_ROOT (mktemp-style)
- Executes steps in order
- Verifies minimal expectations
- Prints artifact paths at end

Usage:
  PYTHONPATH=$PWD python backend/demo/run_demo.py backend/demo/phase6_script.yaml
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    import yaml  # type: ignore
except Exception as e:
    raise SystemExit("Missing dependency: pyyaml. Install with: pip install pyyaml") from e


@dataclass
class StepResult:
    id: str
    title: str
    ok: bool
    exit_code: int


def _expand(s: str, env: Dict[str, str]) -> str:
    # expand $VARS in strings
    return os.path.expandvars(s)


def _run_cmd(cmd: str, cwd: str, env: Dict[str, str]) -> int:
    p = subprocess.run(cmd, shell=True, cwd=cwd, env=env)
    return int(p.returncode)


def _read_text(p: Path) -> str:
    try:
        return p.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return ""


def _assert_stdout_contains(log_txt: str, needles: List[str]) -> Optional[str]:
    for n in needles:
        if n not in log_txt:
            return f"Missing stdout token: {n}"
    return None


def _assert_any_of(log_txt: str, needles: List[str]) -> Optional[str]:
    for n in needles:
        if n in log_txt:
            return None
    return f"Missing any-of stdout tokens: {needles}"


def _assert_files_exist(files: List[str], env: Dict[str, str]) -> Optional[str]:
    for f in files:
        fp = Path(_expand(f, env))
        if not fp.exists():
            return f"Missing expected file: {fp}"
    return None


def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: python backend/demo/run_demo.py backend/demo/phase6_script.yaml")
        return 2

    script_path = Path(sys.argv[1]).resolve()
    if not script_path.exists():
        print(f"Script not found: {script_path}")
        return 2

    cfg = yaml.safe_load(script_path.read_text(encoding="utf-8"))
    defaults = cfg.get("defaults", {}) or {}
    base_env = dict(os.environ)
    base_env.update({k: str(v) for k, v in (defaults.get("env", {}) or {}).items()})

    # Isolated DATA_ROOT unless already set
    if not base_env.get("DATA_ROOT"):
        base_env["DATA_ROOT"] = tempfile.mkdtemp(prefix="aion_demo_")

    cwd = str(Path(defaults.get("cwd", ".")).resolve())

    steps = cfg.get("steps", []) or []
    results: List[StepResult] = []

    print(f"[DEMO] Script: {cfg.get('id')} — {cfg.get('title')}")
    print(f"[DEMO] DATA_ROOT={base_env['DATA_ROOT']}")
    print("")

    for i, step in enumerate(steps, start=1):
        sid = step.get("id", f"step{i}")
        title = step.get("title", sid)
        commands = step.get("run", []) or []

        log_file = Path(base_env["DATA_ROOT"]) / "sessions" / f"demo_step_{i:02d}_{sid}.log.txt"
        log_file.parent.mkdir(parents=True, exist_ok=True)

        print(f"[{i}/{len(steps)}] {sid}: {title}")
        all_ok = True
        last_rc = 0

        with open(log_file, "w", encoding="utf-8") as lf:
            for cmd in commands:
                cmd2 = _expand(str(cmd), base_env)
                lf.write(f"$ {cmd2}\n")
                lf.flush()
                p = subprocess.run(
                    cmd2,
                    shell=True,
                    cwd=cwd,
                    env=base_env,
                    stdout=lf,
                    stderr=subprocess.STDOUT,
                )
                last_rc = int(p.returncode)
                if last_rc != 0:
                    all_ok = False
                    break

        # expectations
        exp = step.get("expect", {}) or {}
        log_txt = _read_text(log_file)

        # exit_code expectation
        if "exit_code" in exp and int(exp["exit_code"]) != last_rc:
            all_ok = False

        # stdout_contains
        if all_ok and exp.get("stdout_contains"):
            err = _assert_stdout_contains(log_txt, list(exp["stdout_contains"]))
            if err:
                all_ok = False

        # stdout_any_of
        if all_ok and exp.get("stdout_any_of"):
            err = _assert_any_of(log_txt, list(exp["stdout_any_of"]))
            if err:
                all_ok = False

        # files_exist
        if all_ok and exp.get("files_exist"):
            err = _assert_files_exist(list(exp["files_exist"]), base_env)
            if err:
                all_ok = False

        results.append(StepResult(id=sid, title=title, ok=all_ok, exit_code=last_rc))
        print(f"  -> {'OK' if all_ok else 'FAIL'} (rc={last_rc}) log={log_file}")

        if not all_ok:
            print("\n[DEMO] Failed step. Tail of log:\n")
            tail = "\n".join(log_txt.splitlines()[-40:])
            print(tail)
            return 1

    # Print artifacts
    print("\n[DEMO] All steps OK.")
    print("[DEMO] Key artifacts:")
    for a in (cfg.get("artifacts", []) or []):
        ap = Path(_expand(str(a), base_env))
        print(f"  - {ap}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())