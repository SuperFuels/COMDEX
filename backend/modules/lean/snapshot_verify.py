from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO = Path("/workspaces/COMDEX")
WS = REPO / "backend/modules/lean/workspace"
OUT = WS / "Generated"
LED = REPO / "data/ledger/lean_snapshots.jsonl"

IMPORTS = [
    "Tessaris.Symatics.Prelude",
    "Tessaris.Symatics.Axioms",
    "Tessaris.Symatics.Tactics",
]


# -----------------------------
# utils
# -----------------------------
def canon(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_hex(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def short_hash_hex(hex_str: str, n: int = 16) -> str:
    return hex_str[:n]


def _lean_env() -> dict[str, str]:
    """
    Keep Lean/Lake caches in /tmp (codespaces disk pressure).
    Ensure ELAN_HOME/bin is on PATH for subprocesses.
    """
    env = os.environ.copy()
    env.setdefault("ELAN_HOME", "/tmp/.elan")
    env.setdefault("LAKE_HOME", "/tmp/.lake")
    env.setdefault("XDG_CACHE_HOME", "/tmp/.cache")
    env.setdefault("TMPDIR", "/tmp")
    env["PATH"] = f"{env['ELAN_HOME']}/bin:" + env.get("PATH", "")
    return env


def run_cmd(cmd: list[str], cwd: Path | None = None) -> tuple[int, str, str]:
    try:
        proc = subprocess.run(
            cmd,
            cwd=str(cwd) if cwd else None,
            capture_output=True,
            text=True,
            env=_lean_env(),
        )
        return proc.returncode, (proc.stdout or "").strip(), (proc.stderr or "").strip()
    except FileNotFoundError as e:
        return 127, "", str(e)
    except Exception as e:
        return 1, "", f"{type(e).__name__}: {e}"


def get_git_rev() -> str:
    rc, out, _ = run_cmd(["git", "rev-parse", "HEAD"], cwd=REPO)
    return out if rc == 0 and out else "unknown"


def get_tool_versions() -> dict[str, str]:
    versions: dict[str, str] = {}

    rc, out, err = run_cmd(["elan", "--version"], cwd=WS)
    versions["elan"] = out if rc == 0 and out else (f"unknown ({err})" if err else "unknown")

    rc, out, err = run_cmd(["lake", "--version"], cwd=WS)
    versions["lake"] = out if rc == 0 and out else (f"unknown ({err})" if err else "unknown")

    rc, out, err = run_cmd(["lake", "env", "lean", "--version"], cwd=WS)
    versions["lean"] = out if rc == 0 and out else (f"unknown ({err})" if err else "unknown")

    env = _lean_env()
    versions["ELAN_HOME"] = env.get("ELAN_HOME", "")
    versions["LAKE_HOME"] = env.get("LAKE_HOME", "")
    versions["XDG_CACHE_HOME"] = env.get("XDG_CACHE_HOME", "")
    versions["TMPDIR"] = env.get("TMPDIR", "")
    return versions


def compute_proof_hash(snapshot: dict, spec_version: str, git_rev: str) -> str:
    payload = {"snapshot": snapshot, "spec_version": spec_version, "git_rev": git_rev}
    return sha256_hex(canon(payload))


def ensure_out_dir() -> None:
    """
    OUT must be a *real* directory.
    If it's a broken symlink or a file, fix it.
    """
    if OUT.is_symlink() and not OUT.exists():
        OUT.unlink()
    if OUT.exists() and not OUT.is_dir():
        OUT.unlink()
    OUT.mkdir(parents=True, exist_ok=True)


def write_snapshot_lean(snapshot: dict, spec_version: str, proof_hash_hex: str) -> Path:
    ensure_out_dir()

    h16 = short_hash_hex(proof_hash_hex, 16)
    p = OUT / f"snapshot_{h16}.lean"

    steps = int(snapshot.get("steps", 1024))
    dt_ms = int(snapshot.get("dt_ms", 16))

    scenario = str(snapshot.get("scenario", "BG01"))
    kappa = float(snapshot.get("kappa", 0.0))
    chi = float(snapshot.get("chi", 0.0))
    sigma = float(snapshot.get("sigma", 0.0))
    alpha = float(snapshot.get("alpha", 0.0))

    txt = f"""\
import {IMPORTS[0]}
import {IMPORTS[1]}
import {IMPORTS[2]}
import Init

noncomputable section

namespace Tessaris.Snapshot

def spec_version : String := "{spec_version}"
def proof_hash   : String := "{proof_hash_hex}"

-- embedded params (checked)
def steps : Nat := {steps}
def dt_ms : Nat := {dt_ms}

-- scenario/knobs (embedded for proof identity)
def scenario : String := "{scenario}"
def kappa : Float := {kappa}
def chi   : Float := {chi}
def sigma : Float := {sigma}
def alpha : Float := {alpha}

theorem steps_pos : steps > 0 := by decide
theorem dt_pos    : dt_ms > 0 := by decide

def A0 : SProp := True
def B0 : SProp := (steps > dt_ms)
def φ0 : Phase := zero_phase

theorem rewrite_inv_phase :
  (A0 ⋈[φ0] (A0 ⋈[-φ0] B0)) ↔ B0 :=
  SymaticsAxioms.inv_phase (A := A0) (B := B0) (φ := φ0)

theorem rewrite_inv_phase_comm :
  ((A0 ⋈[-φ0] B0) ⋈[-φ0] A0) ↔ B0 := by
  have h_comm :
    (A0 ⋈[φ0] (A0 ⋈[-φ0] B0)) ↔ ((A0 ⋈[-φ0] B0) ⋈[-φ0] A0) :=
    SymaticsAxioms.comm_phi (A := A0) (B := (A0 ⋈[-φ0] B0)) (φ := φ0)

  have h_inv :
    (A0 ⋈[φ0] (A0 ⋈[-φ0] B0)) ↔ B0 :=
    SymaticsAxioms.inv_phase (A := A0) (B := B0) (φ := φ0)

  exact Iff.trans h_comm.symm h_inv

theorem rewrite_neutral_bot :
  (A0 ⋈[φ0] ⊥) ↔ A0 :=
  SymaticsAxioms.neutral_phi (A := A0) (φ := φ0)

end Tessaris.Snapshot
"""
    p.write_text(txt, encoding="utf-8")
    return p


def run_lean(file: Path) -> tuple[bool, str, str, int, int]:
    t0 = time.time()
    proc = subprocess.run(
        ["lake", "env", "lean", str(file)],
        cwd=str(WS),
        capture_output=True,
        text=True,
        env=_lean_env(),
    )
    elapsed_ms = int((time.time() - t0) * 1000)
    return proc.returncode == 0, (proc.stdout or ""), (proc.stderr or ""), proc.returncode, elapsed_ms


def tail_lines(s: str, n: int = 40) -> list[str]:
    lines = (s or "").splitlines()
    return lines[-n:] if lines else []


def append_ledger(entry: dict) -> None:
    LED.parent.mkdir(parents=True, exist_ok=True)
    with LED.open("a", encoding="utf-8") as f:
        f.write(canon(entry) + "\n")


def verify_snapshot(
    steps: int,
    dt_ms: int,
    spec_version: str = "v1",
    scenario: str = "BG01",
    kappa: float = 0.0,
    chi: float = 0.0,
    sigma: float = 0.0,
    alpha: float = 0.0,
) -> dict:
    snap = {
        "steps": int(steps),
        "dt_ms": int(dt_ms),
        "scenario": str(scenario),
        "kappa": float(kappa),
        "chi": float(chi),
        "sigma": float(sigma),
        "alpha": float(alpha),
    }

    git_rev = get_git_rev()
    versions = get_tool_versions()

    proof_hash_hex = compute_proof_hash(snap, spec_version, git_rev)
    lf = write_snapshot_lean(snap, spec_version, proof_hash_hex)

    ok, out, err, rc, elapsed_ms = run_lean(lf)

    cert = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "kind": "lean_snapshot_verify",
        "ok": bool(ok),
        "returncode": int(rc),
        "elapsed_ms": int(elapsed_ms),
        "spec_version": spec_version,
        "git_rev": git_rev,
        "proof_hash": proof_hash_hex,
        "proof_hash_short": short_hash_hex(proof_hash_hex, 16),
        "lean_file": str(lf),
        "imports": IMPORTS,
        "params": snap,
        "versions": versions,
        "stdout_tail": tail_lines(out, 40),
        "stderr_tail": tail_lines(err, 40),
        "axioms_used": [
            "SymaticsAxioms.inv_phase",
            "SymaticsAxioms.comm_phi",
            "SymaticsAxioms.neutral_phi",
        ],
        "deps": {"workspace": str(WS)},
    }

    append_ledger(cert)
    return cert


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--steps", type=int, default=1024)
    ap.add_argument("--dt-ms", type=int, default=16)
    ap.add_argument("--spec-version", type=str, default="v1")

    ap.add_argument("--scenario", type=str, default="BG01")
    ap.add_argument("--kappa", type=float, default=0.0)
    ap.add_argument("--chi", type=float, default=0.0)
    ap.add_argument("--sigma", type=float, default=0.0)
    ap.add_argument("--alpha", type=float, default=0.0)

    ap.add_argument("--json", action="store_true", help="print JSON cert to stdout")
    args = ap.parse_args()

    cert = verify_snapshot(
        args.steps,
        args.dt_ms,
        args.spec_version,
        scenario=args.scenario,
        kappa=args.kappa,
        chi=args.chi,
        sigma=args.sigma,
        alpha=args.alpha,
    )

    ok = bool(cert["ok"])
    rc = int(cert["returncode"])

    if args.json:
        print(canon(cert))
    else:
        print(
            f"[lean] ok={ok} file={cert['lean_file']} rc={rc} proof={cert['proof_hash_short']} "
            f"elapsed_ms={cert['elapsed_ms']}"
        )
        if not ok:
            print("\n".join(cert["stderr_tail"]))

    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())