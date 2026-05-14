from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple
import hashlib
import os
import time


@dataclass(frozen=True)
class ArtifactInfo:
    rel: str
    abs: str
    bytes: int
    sha256: str
    mtime_utc: str


def _sha256_file(p: Path, chunk: int = 1024 * 1024) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        while True:
            b = f.read(chunk)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def _iso_utc(ts: float) -> str:
    # ISO-ish without pulling datetime (keep deps tiny)
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(ts))


def _iter_files(run_dir: Path) -> Iterable[Path]:
    # only top-level files in the run dir (matches your API "files" map)
    for p in sorted(run_dir.iterdir()):
        if p.is_file():
            yield p


def finalize_run_artifacts(
    run_dir: str | Path,
    *,
    title: str = "GX1 Run Artifacts",
    exclude_names: Optional[Iterable[str]] = None,
) -> Tuple[Path, Path, List[ArtifactInfo]]:
    """
    Writes:
      - ARTIFACTS_INDEX.md
      - ARTIFACTS.sha256

    Policy:
      - excludes ARTIFACTS.sha256 itself from hashing list
      - includes ARTIFACTS_INDEX.md in ARTIFACTS.sha256
    """
    rd = Path(run_dir).resolve()
    rd.mkdir(parents=True, exist_ok=True)

    exclude = set(exclude_names or [])
    exclude.add("ARTIFACTS.sha256")  # never hash itself

    # 1) hash everything currently present except index/sha (index not written yet)
    infos: List[ArtifactInfo] = []
    for p in _iter_files(rd):
        if p.name in exclude:
            continue
        if p.name == "ARTIFACTS_INDEX.md":
            continue  # we'll write it fresh below
        st = p.stat()
        infos.append(
            ArtifactInfo(
                rel=p.name,
                abs=str(p),
                bytes=int(st.st_size),
                sha256=_sha256_file(p),
                mtime_utc=_iso_utc(st.st_mtime),
            )
        )

    # 2) write index
    index_path = rd / "ARTIFACTS_INDEX.md"
    lines: List[str] = []
    lines.append(f"# {title}")
    lines.append("")
    lines.append(f"- run_dir: `{rd}`")
    lines.append(f"- generated_utc: `{_iso_utc(time.time())}`")
    lines.append("")
    lines.append("## Files")
    lines.append("")
    lines.append("| file | bytes | sha256 | mtime_utc |")
    lines.append("|---|---:|---|---|")
    for a in infos:
        lines.append(f"| `{a.rel}` | {a.bytes} | `{a.sha256}` | `{a.mtime_utc}` |")
    lines.append("")
    index_path.write_text("\n".join(lines), encoding="utf-8")

    # 3) hash the index too (and append to list)
    st_i = index_path.stat()
    index_info = ArtifactInfo(
        rel=index_path.name,
        abs=str(index_path),
        bytes=int(st_i.st_size),
        sha256=_sha256_file(index_path),
        mtime_utc=_iso_utc(st_i.st_mtime),
    )
    infos_with_index = infos + [index_info]

    # 4) write sha256 file (sha256sum-compatible)
    sha_path = rd / "ARTIFACTS.sha256"
    sha_lines = [f"{a.sha256}  {a.rel}" for a in infos_with_index]
    sha_path.write_text("\n".join(sha_lines) + "\n", encoding="utf-8")

    return index_path, sha_path, infos_with_index
