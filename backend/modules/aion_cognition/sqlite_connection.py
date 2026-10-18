"""Bounded SQLite connections for Aion's persistent learning services.

The standard :class:`sqlite3.Connection` context manager commits or rolls
back a transaction, but it does not close the connection.  Creating a new
connection for every short transaction therefore leaked handles.  Conversely,
opening and closing the SD-card database for every statement is prohibitively
slow.  This module keeps one connection per database and thread: handles stay
bounded, nested components cannot compete with themselves, and independent
worker threads retain their own transaction channel.
"""
from __future__ import annotations

from pathlib import Path
import os
import re
import sqlite3
import threading
import time
from typing import Any
from urllib.parse import quote

try:
    import fcntl
except ImportError:  # pragma: no cover - Windows development fallback
    fcntl = None


_LOCAL = threading.local()
_GATES_LOCK = threading.Lock()
_PROCESS_GATES: dict[str, threading.RLock] = {}


def _process_gate(path: str) -> threading.RLock:
    with _GATES_LOCK:
        return _PROCESS_GATES.setdefault(path, threading.RLock())


def _lock_depths() -> dict[str, int]:
    depths = getattr(_LOCAL, "lock_depths", None)
    if depths is None:
        depths = {}
        _LOCAL.lock_depths = depths
    return depths


class _CoordinatedConnection(sqlite3.Connection):
    """Connection whose context transaction is coordinated across processes.

    Aion deliberately uses rollback journalling on removable media. SQLite's
    busy timeout handles short collisions, but the reader, spider, teacher and
    practice workers can all reach commit together.  A small advisory lock
    prevents that thundering herd without moving the database off the SD card.
    Every mixed transaction context takes the exclusive cross-process gate;
    explicit read-only contexts take a shared lock. Long reporting queries and
    migrations use dedicated read-only or bounded paths, so serialization does
    not allow an uncoordinated reader to starve an SD-card commit.
    """

    _aion_lock_path: str = ""
    _aion_lock_timeout: float = 30.0
    _aion_read_only: bool = False
    _aion_lock_handle: Any = None
    _aion_gate: threading.RLock | None = None
    _aion_gate_acquired: bool = False
    _aion_context_depth: int = 0
    _aion_batch_depth: int = 0
    _aion_batch_failed: bool = False

    @staticmethod
    def _mutates(statement: object) -> bool:
        return bool(re.match(
            r"^\s*(?:INSERT|UPDATE|DELETE|REPLACE|CREATE|ALTER|DROP|VACUUM|REINDEX|"
            r"BEGIN\s+(?:IMMEDIATE|EXCLUSIVE))\b",
            str(statement or ""), re.I,
        ))

    def _acquire_process_gate(self) -> None:
        """Prevent a process-local reader/writer lock inversion."""
        if self._aion_read_only or not self._aion_lock_path or self._aion_gate_acquired:
            return
        gate = _process_gate(self._aion_lock_path)
        process_timeout = min(
            max(0.1, self._aion_lock_timeout),
            max(0.1, float(os.getenv("AION_SQLITE_PROCESS_GATE_TIMEOUT", "5"))),
        )
        if not gate.acquire(timeout=process_timeout):
            raise sqlite3.OperationalError("Aion SQLite process transaction gate timed out")
        self._aion_gate = gate
        self._aion_gate_acquired = True

    def _acquire_aion_lock(self) -> None:
        if not self._aion_lock_path or self._aion_lock_handle is not None:
            return
        self._acquire_process_gate()
        depths = _lock_depths()
        depth = depths.get(self._aion_lock_path, 0)
        depths[self._aion_lock_path] = depth + 1
        if fcntl is None or depth:
            return
        handle = open(self._aion_lock_path, "a+b")
        deadline = time.monotonic() + max(0.1, self._aion_lock_timeout)
        while True:
            try:
                operation = fcntl.LOCK_SH if self._aion_read_only else fcntl.LOCK_EX
                fcntl.flock(handle.fileno(), operation | fcntl.LOCK_NB)
                self._aion_lock_handle = handle
                return
            except BlockingIOError:
                if time.monotonic() >= deadline:
                    handle.close()
                    depths.pop(self._aion_lock_path, None)
                    gate, self._aion_gate = self._aion_gate, None
                    self._aion_gate_acquired = False
                    if gate is not None:
                        gate.release()
                    raise sqlite3.OperationalError("Aion SQLite transaction gate timed out")
                time.sleep(0.025)

    def _release_aion_lock(self) -> None:
        # Read-only connections deliberately do not take the process-local
        # exclusive gate, but they still own a shared advisory file handle
        # which must be unlocked at the end of every context.
        if not self._aion_gate_acquired and self._aion_lock_handle is None:
            return
        handle, self._aion_lock_handle = self._aion_lock_handle, None
        depths = _lock_depths()
        if handle is not None:
            depth = max(0, depths.get(self._aion_lock_path, 1) - 1)
            if depth:
                depths[self._aion_lock_path] = depth
            else:
                depths.pop(self._aion_lock_path, None)
        try:
            if handle is not None and fcntl is not None:
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
        finally:
            if handle is not None:
                handle.close()
            gate, self._aion_gate = self._aion_gate, None
            self._aion_gate_acquired = False
            if gate is not None:
                gate.release()

    def __enter__(self) -> "_CoordinatedConnection":
        # Acquire before SQLite begins any transaction. This prevents a reader
        # from appearing after a writer owns the advisory gate but before that
        # writer can promote its rollback-journal lock at commit time.
        self._acquire_aion_lock()
        self._aion_context_depth += 1
        try:
            return super().__enter__()
        except BaseException:
            self._aion_context_depth = max(0, self._aion_context_depth - 1)
            if self._aion_context_depth == 0:
                self._release_aion_lock()
            raise

    def execute(self, sql: str, parameters: Any = (), /) -> sqlite3.Cursor:
        if self._mutates(sql):
            self._acquire_aion_lock()
        return super().execute(sql, parameters)

    def executemany(self, sql: str, parameters: Any, /) -> sqlite3.Cursor:
        if self._mutates(sql):
            self._acquire_aion_lock()
        return super().executemany(sql, parameters)

    def executescript(self, sql_script: str, /) -> sqlite3.Cursor:
        if self._mutates(sql_script):
            self._acquire_aion_lock()
        return super().executescript(sql_script)

    def __exit__(self, exc_type: Any, exc: Any, traceback: Any) -> bool:
        if self._aion_batch_depth:
            self._aion_context_depth = max(0, self._aion_context_depth - 1)
            self._aion_batch_failed = self._aion_batch_failed or exc_type is not None
            return False
        try:
            return bool(super().__exit__(exc_type, exc, traceback))
        finally:
            self._aion_context_depth = max(0, self._aion_context_depth - 1)
            if self._aion_context_depth == 0:
                self._release_aion_lock()

    def close(self) -> None:
        self._release_aion_lock()
        super().close()

    def begin_aion_batch(self) -> None:
        self._aion_batch_depth += 1

    def end_aion_batch(self, *, success: bool) -> None:
        if not self._aion_batch_depth:
            return
        self._aion_batch_failed = self._aion_batch_failed or not success
        self._aion_batch_depth -= 1
        if self._aion_batch_depth:
            return
        failed, self._aion_batch_failed = self._aion_batch_failed, False
        try:
            if self.in_transaction:
                if failed:
                    self.rollback()
                else:
                    self.commit()
        finally:
            self._aion_context_depth = 0
            self._release_aion_lock()


def _database_lock_path(database: object, *, uri: bool) -> str:
    value = str(database)
    if uri and value.startswith("file:"):
        value = value[5:].split("?", 1)[0]
    if value == ":memory:" or value.startswith("file::memory:"):
        return ""
    path = Path(value).expanduser()
    return str(path.with_name(f".{path.name}.aion-transaction.lock"))


def _cache() -> dict[tuple[str, bool], sqlite3.Connection]:
    cache = getattr(_LOCAL, "connections", None)
    if cache is None:
        cache = {}
        _LOCAL.connections = cache
    return cache


def connect(
    database: object, *, timeout: float = 30, gate_timeout: float | None = None,
    **kwargs: object,
) -> sqlite3.Connection:
    """Return the current thread's reusable connection for this database."""

    uri = bool(kwargs.get("uri", False))
    # One connection per database and thread prevents nested components from
    # opening competing transactions against the same rollback journal.
    key = (str(database), uri)
    cache = _cache()
    connection = cache.get(key)
    if connection is not None:
        try:
            connection.execute("SELECT 1")
            return connection
        except sqlite3.ProgrammingError:
            cache.pop(key, None)
    factory = kwargs.pop("factory", _CoordinatedConnection)
    connection = sqlite3.connect(database, timeout=timeout, factory=factory, **kwargs)
    if isinstance(connection, _CoordinatedConnection):
        connection._aion_lock_path = _database_lock_path(database, uri=uri)
        # SD-card schema checks and bounded reading writes can occasionally
        # exceed SQLite's ordinary busy window.  Waiting here serialises the
        # learning lanes without turning a healthy long transaction into a
        # failed teacher, gym or discourse cycle.
        configured_gate_timeout = (
            float(gate_timeout) if gate_timeout is not None
            else float(os.getenv("AION_SQLITE_GATE_TIMEOUT", "120"))
        )
        connection._aion_lock_timeout = max(float(timeout), configured_gate_timeout)
        connection._aion_read_only = bool(uri and "mode=ro" in str(database))
    cache[key] = connection
    return connection


def connect_read_only(
    database: object, *, timeout: float = 30, gate_timeout: float | None = None,
    **kwargs: object,
) -> sqlite3.Connection:
    """Return a shared-lock connection for reporting and evidence reads.

    This explicit API prevents read transactions from being promoted to writes
    and lets expensive progress summaries coexist without blocking every
    learning worker behind the dashboard.
    """

    path = Path(str(database)).expanduser().resolve()
    uri = f"file:{quote(str(path), safe='/')}?mode=ro"
    kwargs["uri"] = True
    return connect(uri, timeout=timeout, gate_timeout=gate_timeout, **kwargs)


def begin_batch(connection: sqlite3.Connection) -> None:
    """Defer nested context commits until one bounded service batch ends."""
    if isinstance(connection, _CoordinatedConnection):
        connection.begin_aion_batch()


def end_batch(connection: sqlite3.Connection, *, success: bool) -> None:
    """Commit or roll back a batch started with :func:`begin_batch`."""
    if isinstance(connection, _CoordinatedConnection):
        connection.end_aion_batch(success=success)


def close_thread_connections() -> None:
    """Close reusable connections owned by the current thread."""

    cache = _cache()
    for connection in cache.values():
        try:
            connection.close()
        except sqlite3.Error:
            pass
    cache.clear()
