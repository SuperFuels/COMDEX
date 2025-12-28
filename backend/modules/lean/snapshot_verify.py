from __future__ import annotations
import argparse, hashlib, json, os, subprocess
from pathlib import Path
from datetime import datetime, timezone

REPO = Path("/workspaces/COMDEX")
WS   = REPO / "backend/modules/lean/workspace"
OUT  = WS / "Generated"
LED  = REPO / "data/ledger/lean_snapshots.jsonl"

def canon(obj) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)

def shorthash(obj) -> str:
    return hashlib.sha256(canon(obj).encode("utf-8")).hexdigest()[:16]

def write_snapshot(snapshot: dict) -> Path:
    OUT.mkdir(parents=True, exist_ok=True)
    h = shorthash(snapshot)
    p = OUT / f"snapshot_{h}.lean"
    steps = int(snapshot.get("steps", 1024))
    dt_ms = int(snapshot.get("dt_ms", 16))

    # Imports are YOUR real skeleton
    txt = f"""\
import Tessaris.Symatics.Prelude
import Tessaris.Symatics.Axioms
import Tessaris.Symatics.Tactics
import Init

namespace Tessaris.Snapshot

def snapshot_hash : String := "{h}"

-- embedded params (proof obligations that are actually checked)
def steps : Nat := {steps}
def dt_ms : Nat := {dt_ms}

theorem steps_pos : steps > 0 := by decide
theorem dt_pos : dt_ms > 0 := by decide

-- placeholder: hook a real invariant here next
-- e.g. “rewrite equivalence”, “constraint set satisfied”, etc.

end Tessaris.Snapshot
"""
    p.write_text(txt, encoding="utf-8")
    return p

def run_lean(file: Path) -> tuple[bool, str, str, int]:
    proc = subprocess.run(
        ["lake", "env", "lean", str(file)],
        cwd=str(WS),
        capture_output=True,
        text=True,
        env=os.environ.copy(),
    )
    return (proc.returncode == 0, proc.stdout, proc.stderr, proc.returncode)

def ledger(snapshot: dict, lean_file: Path, ok: bool, rc: int, out: str, err: str):
    entry = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "kind": "lean_snapshot_verify",
        "ok": ok,
        "snapshot_hash": lean_file.stem.replace("snapshot_", ""),
        "lean_file": str(lean_file),
        "params": {k: snapshot.get(k) for k in ("steps", "dt_ms")},
        "returncode": rc,
        "stderr_tail": err.splitlines()[-20:],
    }
    LED.parent.mkdir(parents=True, exist_ok=True)
    with LED.open("a", encoding="utf-8") as f:
        f.write(canon(entry) + "\n")

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--steps", type=int, default=1024)
    ap.add_argument("--dt-ms", type=int, default=16)
    args = ap.parse_args()

    snap = {"steps": args.steps, "dt_ms": args.dt_ms}
    lf = write_snapshot(snap)
    ok, out, err, rc = run_lean(lf)
    ledger(snap, lf, ok, rc, out, err)

    print(f"[lean] ok={ok} file={lf} rc={rc}")
    if not ok:
        print(err)
    return 0 if ok else 1

if __name__ == "__main__":
    raise SystemExit(main())
