from __future__ import annotations

from typing import Any, Dict
import os
import hashlib
import shutil
from pathlib import Path

from .artifacts_manifest import finalize_run_artifacts
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


def _ensure_run_local_verify_files(run_dir: Path, run_id: str) -> None:
    """
    The UI runs these from inside the run folder:
      - sha256sum -c checksums/$RUN_ID.sha256
      - sha256sum -c ARTIFACTS_INDEX.sha256

    So every run dir must contain:
      - checksums/<RUN_ID>.sha256   (list of run-local files)
      - ARTIFACTS_INDEX.sha256      (sha list that verifies ARTIFACTS_INDEX.md)
    """
    artifacts_sha = run_dir / "ARTIFACTS.sha256"
    artifacts_index_md = run_dir / "ARTIFACTS_INDEX.md"

    # If finalize_run_artifacts didn't create these for some reason, do best-effort.
    if not artifacts_index_md.exists():
        # Minimal index (still satisfies sha256sum -c ARTIFACTS_INDEX.sha256)
        _write_text(
            artifacts_index_md,
            f"# RUN ARTIFACTS_INDEX\nrun_dir: {run_dir.as_posix()}\n",
        )

    if not artifacts_sha.exists():
        # Best-effort: hash the common run-local artifacts if present.
        candidates = [
            run_dir / "CONFIG.json",
            run_dir / "GIT_REV.txt",
            run_dir / "METRICS.json",
            run_dir / "REPLAY_BUNDLE.json",
            run_dir / "TRACE.jsonl",
            artifacts_index_md,
        ]
        lines: list[str] = []
        for p in candidates:
            if p.exists():
                lines.append(f"{_sha256_file(p)}  {p.name}\n")
        _write_text(artifacts_sha, "".join(lines))

    # 1) checksums/<RUN_ID>.sha256 (UI expects this name/location)
    (run_dir / "checksums").mkdir(parents=True, exist_ok=True)
    shutil.copyfile(artifacts_sha, run_dir / "checksums" / f"{run_id}.sha256")

    # 2) ARTIFACTS_INDEX.sha256 (hash-of-index list)
    idx_sum = _sha256_file(artifacts_index_md)
    _write_text(run_dir / "ARTIFACTS_INDEX.sha256", f"{idx_sum}  ARTIFACTS_INDEX.md\n")


def write_artifacts(
    *,
    repo_root: str,
    phase_root: str,
    run_id: str,
    config: Dict[str, Any],
    metrics: Dict[str, Any],
    trace: Any,
    replay_bundle: Dict[str, Any],
    ledger_rows: Any = None,
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

    # Run-local artifacts
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

    # Optional SQI fabric export (server-free KG write-intents)
    sqi_kg_writes_path = run_dir / "SQI_KG_WRITES.jsonl"

    # Optional deterministic ledger export (JSONL)
    ledger_path = run_dir / "LEDGER.jsonl"
    ledger_written = False
    if isinstance(ledger_rows, list) and ledger_rows:
        try:
            from .ledger_feed import write_ledger_jsonl

            write_ledger_jsonl(ledger_path, ledger_rows)
            ledger_written = True
        except Exception:
            ledger_written = False

    repro = f"""#!/usr/bin/env bash
set -euo pipefail
cd "{repo_root}"
python -m backend.genome_engine.run_genomics_benchmark --config "{(run_dir / "CONFIG.json").as_posix()}"
"""
    _write_text(run_dir / "cmd" / "repro.sh", repro)
    os.chmod((run_dir / "cmd" / "repro.sh").as_posix(), 0o755)

    # Phase-level ARTIFACTS_INDEX.md
    idx: list[str] = []
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
    if sqi_kg_writes_path.exists():
        idx.append(f"- runs/{run_id}/SQI_KG_WRITES.jsonl\n")
    if ledger_written and ledger_path.exists():
        idx.append(f"- runs/{run_id}/LEDGER.jsonl\n")
    _write_text(root / "ARTIFACTS_INDEX.md", "".join(idx))

    # Phase-level ARTIFACTS_INDEX.sha256
    idx_sum = _sha256_file(root / "ARTIFACTS_INDEX.md")
    ptr_sum = _sha256_file(root / "runs" / "LATEST_RUN_ID.txt")
    _write_text(
        root / "ARTIFACTS_INDEX.sha256",
        f"{idx_sum}  ARTIFACTS_INDEX.md\n{ptr_sum}  runs/LATEST_RUN_ID.txt\n",
    )

    # Phase-level run checksum bundle (used by AUDIT verify)
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
    if sqi_kg_writes_path.exists():
        files.append(sqi_kg_writes_path)
    if ledger_written and ledger_path.exists():
        files.append(ledger_path)

    files = list(dict.fromkeys(files))  # stable de-dupe
    (root / "checksums").mkdir(parents=True, exist_ok=True)
    lines: list[str] = []
    for p in files:
        rel = p.relative_to(root).as_posix()
        lines.append(f"{_sha256_file(p)}  {rel}\n")
    _write_text(root / "checksums" / f"{run_id}.sha256", "".join(lines))

    # Run-local index + sha (API/UI expects these inside the run dir)
    finalize_run_artifacts(run_dir)

    # Critical UI fix: emit run-local verify files the UI commands reference
    _ensure_run_local_verify_files(run_dir, run_id)

    return {"git_rev": git_rev, "phase_root": str(root), "run_dir": str(run_dir)}


def get_git_rev(repo_root: str) -> str:
    """Public helper for consistent git_rev provenance."""
    return _git_rev(Path(repo_root))
