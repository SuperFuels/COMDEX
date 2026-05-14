#!/usr/bin/env python3
"""
Log-to-Photon Daemon - Unified Mode (Files + Directory)
------------------------------------------------------

✅ Watches one or more .log/.jsonl files OR a directory
✅ Streams each new line -> compress_to_glyphs()
✅ Emits .photo capsules into data/qqc_field/log_photos/

Usage examples:

# Watch directory
PYTHONPATH=. python backend/tools/log_to_photon_daemon.py --watch logs/

# Watch specific files
PYTHONPATH=. python backend/tools/log_to_photon_daemon.py --paths run.log events.jsonl

# Custom output dir
PYTHONPATH=. python backend/tools/log_to_photon_daemon.py --paths run.log --out data/photon_sci/logstream
"""

import argparse, time, json, os
from pathlib import Path
from typing import Dict

from backend.modules.glyphos.glyph_compressor import compress_to_glyphs

DEFAULT_OUT = Path("data/qqc_field/log_photos/")
DEFAULT_OUT.mkdir(parents=True, exist_ok=True)


def emit_capsule(line: str, source: str, out_dir: Path):
    """
    Compress a log line into a photon capsule and write .photo file.
    """
    if not line.strip():
        return

    pkt = compress_to_glyphs(line, source=source)
    ts = pkt["timestamp"].replace(":", "_").replace(".", "_")

    out_file = out_dir / f"log_{ts}_{Path(source).name}.photo"
    out_file.write_text(json.dumps(pkt, ensure_ascii=False, indent=2))

    print(f"🌀 log->photo: {out_file}")


def follow_file(path: Path, pos: int, out_dir: Path):
    """
    Read new content from file starting at pos.
    """
    with path.open("r", encoding="utf-8", errors="ignore") as f:
        f.seek(pos)
        for line in f:
            if line.strip():
                emit_capsule(line.strip(), str(path), out_dir)
        return f.tell()


def watch_files(files, out_dir: Path, interval: float):
    """
    Tail multiple individual files.
    """
    offsets: Dict[str, int] = {}

    # Start at EOF for each file
    for p in files:
        path = Path(p)
        offsets[str(path)] = path.stat().st_size if path.exists() else 0

    print(f"📡 Watching files: {files}")

    while True:
        for p in files:
            path = Path(p)
            if not path.exists():
                continue
            offsets[str(path)] = follow_file(path, offsets[str(path)], out_dir)
        time.sleep(interval)


def watch_dir(dir_path: Path, out_dir: Path):
    """
    Tail all .log and .jsonl files in a directory.
    """
    print(f"📡 Watching directory: {dir_path}")

    offsets = {}

    while True:
        for pattern in ("*.jsonl", "*.log"):
            for file in dir_path.glob(pattern):
                pos = offsets.get(file, 0)
                offsets[file] = follow_file(file, pos, out_dir)
        time.sleep(1)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--watch", help="Directory to watch for logs (.log/.jsonl)")
    parser.add_argument("--paths", nargs="+", help="Individual files to watch")
    parser.add_argument("--out", default=str(DEFAULT_OUT), help="Output directory for .photo files")
    parser.add_argument("--interval", type=float, default=1.0)

    args = parser.parse_args()
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    if args.watch:
        d = Path(args.watch)
        if not d.exists():
            raise RuntimeError(f"Watch directory does not exist: {d}")
        watch_dir(d, out_dir)

    elif args.paths:
        watch_files(args.paths, out_dir, args.interval)

    else:
        parser.error("Must specify either --watch or --paths")


if __name__ == "__main__":
    main()