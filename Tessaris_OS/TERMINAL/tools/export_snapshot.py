from __future__ import annotations

import json
import zipfile
from pathlib import Path
from typing import Optional

from tessaris_terminal.contract import REQUIRED_FILES, OPTIONAL_FILES, read_json


def guess_repro_cmd(run_dir: Path) -> str:
    # Try to infer pillar from path. Example:
    # BRIDGE/artifacts/programmable_bridge/BG01/<hash>
    # MATTER/artifacts/programmable_matter/MT02/<hash>
    parts = run_dir.parts
    # find "<PILLAR>/artifacts" in the path
    pillar = None
    for i in range(len(parts) - 1):
        if parts[i+1] == "artifacts":
            pillar = parts[i]
            break
    test_id = read_json(run_dir / "run.json").get("test_id", "UNKNOWN")
    if pillar:
        return (
f"cd /workspaces/COMDEX || exit 1\n"
f"env PYTHONPATH=$PWD/{pillar}/src python -m pytest \\\n"
f"  {pillar}/tests -q\n"
f"# (filter down to {test_id} test file if desired)\n"
        )
    return "cd /workspaces/COMDEX || exit 1\n# repro command unknown (could not infer pillar)\n"


def main() -> None:
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("run_dir", help="path to a specific run folder containing run.json")
    ap.add_argument("--out", default=None, help="output zip path (default: <run_hash>_snapshot.zip)")
    args = ap.parse_args()

    run_dir = Path(args.run_dir)
    if not (run_dir / "run.json").exists():
        raise SystemExit(f"not a run dir: {run_dir} (missing run.json)")

    run = read_json(run_dir / "run.json")
    run_hash = run.get("run_hash") or run_dir.name
    out = Path(args.out) if args.out else Path(f"{run_hash}_snapshot.zip")

    repro = guess_repro_cmd(run_dir)

    with zipfile.ZipFile(out, "w", compression=zipfile.ZIP_DEFLATED) as z:
        # core files
        for fn in REQUIRED_FILES:
            z.write(run_dir / fn, arcname=f"{run_hash}/{fn}")

        # optional Phase0+ files
        for fn in OPTIONAL_FILES:
            p = run_dir / fn
            if p.exists():
                z.write(p, arcname=f"{run_hash}/{fn}")

        # future: frames folder
        frames = run_dir / "frames"
        if frames.exists() and frames.is_dir():
            for fp in sorted(frames.glob("*.png")):
                z.write(fp, arcname=f"{run_hash}/frames/{fp.name}")

        # repro + manifest
        z.writestr(f"{run_hash}/REPRO.txt", repro)
        manifest = {"run_dir": str(run_dir), "run_hash": run_hash}
        z.writestr(f"{run_hash}/MANIFEST.json", json.dumps(manifest, indent=2))

    print(f"OK: wrote {out}")


if __name__ == "__main__":
    main()
