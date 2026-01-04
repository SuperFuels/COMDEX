from __future__ import annotations

from typing import Any, Dict
import os
import hashlib
from pathlib import Path

from .stable_json import stable_stringify


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _write_text(path: Path, s: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(s, encoding="utf-8")


def _git_rev(repo_root: Path) -> str:
    git_dir = repo_root / ".git"
    head = git_dir / "HEAD"
    if not head.exists():
        return "UNKNOWN"
    ref = head.read_text(encoding="utf-8").strip()
    if ref.startswith("ref:"):
        ref_path = git_dir / ref.split(":", 1)[1].strip()
        if ref_path.exists():
            return ref_path.read_text(encoding="utf-8").strip()
    return ref[:64] if ref else "UNKNOWN"


def write_artifacts(
    *,
    repo_root: str,
    phase_root: str,
    run_id: str,
    config: Dict[str, Any],
    metrics: Dict[str, Any],
    trace: Any,
    replay_bundle: Dict[str, Any],
) -> Dict[str, str]:
    repo = Path(repo_root)
    root = Path(phase_root)
    run_dir = root / "runs" / run_id
    git_rev = _git_rev(repo)

    _write_text(root / "GIT_REV.txt", git_rev + "\n")
    _write_text(root / "runs" / "LATEST_RUN_ID.txt", run_id + "\n")

    # AUDIT_REGISTRY.md (phase-level)
    audit = f"""# AUDIT_REGISTRY — P21_GX1 (v0.4)

RUN_ID: {run_id}
GIT_REV: {git_rev}

## Verify
```bash
cd /workspaces/COMDEX || exit 1
ROOT="docs/Artifacts/v0.4/P21_GX1"
RUN_ID="$(cat "$ROOT/runs/LATEST_RUN_ID.txt")"
( cd "$ROOT" && sha256sum -c "checksums/$RUN_ID.sha256" )
( cd "$ROOT" && sha256sum -c "ARTIFACTS_INDEX.sha256" )
```
"""
    _write_text(root / "AUDIT_REGISTRY.md", audit)

    # Evidence block (phase-level)
    (root / "docs").mkdir(parents=True, exist_ok=True)
    evidence = f"""# P21_GX1_EVIDENCE_BLOCK (v0.4)

This phase records a deterministic genomics benchmark run (GX1) and its artifact ladder.

## Canonical entrypoint
```bash
python -m backend.genome_engine.run_genomics_benchmark --config <CONFIG.json>
```

## Latest run
RUN_ID: {run_id}
GIT_REV: {git_rev}

## Verify
```bash
cd "/workspaces/COMDEX" || exit 1
ROOT="docs/Artifacts/v0.4/P21_GX1"
RUN_ID="$(cat "$ROOT/runs/LATEST_RUN_ID.txt")"
( cd "$ROOT" && sha256sum -c "checksums/$RUN_ID.sha256" )
( cd "$ROOT" && sha256sum -c "ARTIFACTS_INDEX.sha256" )
```

## Notes
- Computational benchmark harness with engineered baselines.
- No wetlab / biological efficacy claim is made by this phase.
"""
    evidence_path = root / "docs" / "P21_GX1_EVIDENCE_BLOCK.md"
    _write_text(evidence_path, evidence)

    _write_text(run_dir / "GIT_REV.txt", git_rev + "\n")
    _write_text(run_dir / "CONFIG.json", stable_stringify(config) + "\n")
    _write_text(run_dir / "METRICS.json", stable_stringify(metrics) + "\n")

    trace_path = run_dir / "TRACE.jsonl"
    trace_path.parent.mkdir(parents=True, exist_ok=True)
    with trace_path.open("w", encoding="utf-8") as f:
        if isinstance(trace, list):
            for ev in trace:
                f.write(stable_stringify(ev) + "\n")
        else:
            f.write(stable_stringify(trace) + "\n")

    _write_text(run_dir / "REPLAY_BUNDLE.json", stable_stringify(replay_bundle) + "\n")

    repro = f"""#!/usr/bin/env bash
set -euo pipefail
cd "{repo_root}"
python -m backend.genome_engine.run_genomics_benchmark --config "{(run_dir / "CONFIG.json").as_posix()}"
"""
    _write_text(run_dir / "cmd" / "repro.sh", repro)
    os.chmod((run_dir / "cmd" / "repro.sh").as_posix(), 0o755)

    idx = []
    idx.append("# ARTIFACTS_INDEX — P21_GX1 (Genomics benchmark)\n")
    idx.append(f"RUN_ID: {run_id}\n\n")
    idx.append("## Contents\n")
    idx.append("- GIT_REV.txt\n")
    idx.append("- AUDIT_REGISTRY.md\n")
    idx.append("- runs/LATEST_RUN_ID.txt\n")
    idx.append("- ARTIFACTS_INDEX.md\n")
    idx.append("- ARTIFACTS_INDEX.sha256\n")
    idx.append("- docs/P21_GX1_EVIDENCE_BLOCK.md\n")
    idx.append(f"- checksums/{run_id}.sha256\n\n")
    idx.append("## Run bundle\n")
    idx.append(f"- runs/{run_id}/GIT_REV.txt\n")
    idx.append(f"- runs/{run_id}/cmd/repro.sh\n")
    idx.append(f"- runs/{run_id}/CONFIG.json\n")
    idx.append(f"- runs/{run_id}/METRICS.json\n")
    idx.append(f"- runs/{run_id}/TRACE.jsonl\n")
    idx.append(f"- runs/{run_id}/REPLAY_BUNDLE.json\n")
    _write_text(root / "ARTIFACTS_INDEX.md", "".join(idx))

    idx_sum = _sha256_file(root / "ARTIFACTS_INDEX.md")
    ptr_sum = _sha256_file(root / "runs" / "LATEST_RUN_ID.txt")
    _write_text(
        root / "ARTIFACTS_INDEX.sha256",
        f"{idx_sum}  ARTIFACTS_INDEX.md\n{ptr_sum}  runs/LATEST_RUN_ID.txt\n",
    )

    files = [
        root / "GIT_REV.txt",
        root / "AUDIT_REGISTRY.md",
        evidence_path,
        root / "runs" / "LATEST_RUN_ID.txt",
        run_dir / "GIT_REV.txt",
        run_dir / "cmd" / "repro.sh",
        run_dir / "CONFIG.json",
        run_dir / "METRICS.json",
        run_dir / "TRACE.jsonl",
        run_dir / "REPLAY_BUNDLE.json",
        root / "ARTIFACTS_INDEX.md",
        root / "ARTIFACTS_INDEX.sha256",
    ]
    # Keep manifest stable if duplicates ever creep in.
    files = list(dict.fromkeys(files))

    (root / "checksums").mkdir(parents=True, exist_ok=True)
    lines = []
    for p in files:
        rel = p.relative_to(root).as_posix()
        lines.append(f"{_sha256_file(p)}  {rel}\n")
    _write_text(root / "checksums" / f"{run_id}.sha256", "".join(lines))

    return {"git_rev": git_rev, "phase_root": str(root), "run_dir": str(run_dir)}


def get_git_rev(repo_root: str) -> str:
    """Public helper for consistent git_rev provenance."""
    return _git_rev(Path(repo_root))
