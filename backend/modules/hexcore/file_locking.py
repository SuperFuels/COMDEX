"""Small POSIX file-lock helpers for persistent AION services and ledgers."""
from __future__ import annotations

import fcntl
import os
from contextlib import contextmanager
from pathlib import Path
from typing import BinaryIO, Iterator


@contextmanager
def exclusive_file_lock(path: Path) -> Iterator[None]:
    """Hold an exclusive advisory lock for the duration of one state transaction."""
    path.parent.mkdir(parents=True, exist_ok=True)
    handle = path.open("a+b")
    try:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        yield
    finally:
        fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
        handle.close()


def acquire_process_lock(path: Path) -> BinaryIO | None:
    """Return a held non-blocking process lock, or ``None`` if already owned."""
    path.parent.mkdir(parents=True, exist_ok=True)
    handle = path.open("a+b")
    try:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        handle.close()
        return None
    handle.seek(0)
    handle.truncate()
    handle.write(f"{os.getpid()}\n".encode("ascii"))
    handle.flush()
    os.fsync(handle.fileno())
    return handle
