#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
from pathlib import Path


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def main() -> int:
    root = Path(__file__).resolve().parent
    manifest = json.loads((root / "offline-integrity-manifest.json").read_text(encoding="utf-8"))
    failures: list[str] = []
    expected = {str(record["path"]) for record in manifest.get("files", [])}
    for record in manifest.get("files", []):
        path = root / str(record["path"])
        if not path.is_file():
            failures.append(f"missing: {record['path']}")
        elif path.stat().st_size != int(record["bytes"]):
            failures.append(f"wrong size: {record['path']}")
        elif digest(path) != record["sha256"]:
            failures.append(f"wrong digest: {record['path']}")
    ignored_roots = {".pilot-offline-venv"}
    ignored_files = {"offline-integrity-manifest.json", "offline-ollama.log", ".DS_Store"}
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        relative = path.relative_to(root).as_posix()
        if relative in expected or relative in ignored_files or relative.split("/", 1)[0] in ignored_roots:
            continue
        failures.append(f"unexpected: {relative}")
    if failures:
        print("Pilot offline package verification failed.")
        for failure in failures[:20]:
            print(f"- {failure}")
        return 1
    print(f"Pilot offline package verified: {len(manifest['files'])} files")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
