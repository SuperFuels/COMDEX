from pathlib import Path
import multiprocessing
import sqlite3
import threading
import time

import pytest

from backend.modules.aion_cognition.sqlite_connection import (
    begin_batch,
    close_thread_connections,
    connect,
    connect_read_only,
    end_batch,
)


def _component_connection(database: Path) -> sqlite3.Connection:
    return connect(database)


def test_connection_context_commits_and_reuses_a_bounded_handle(tmp_path: Path) -> None:
    database = tmp_path / "learning.sqlite3"
    try:
        with _component_connection(database) as first:
            first.execute("CREATE TABLE evidence(value TEXT NOT NULL)")
            first.execute("INSERT INTO evidence VALUES('retained')")
        with _component_connection(database) as second:
            assert second.execute("SELECT value FROM evidence").fetchone() == ("retained",)
        assert first is second
    finally:
        close_thread_connections()


def test_connection_context_rolls_back_without_discarding_reusable_handle(tmp_path: Path) -> None:
    database = tmp_path / "learning.sqlite3"
    with sqlite3.connect(database) as setup:
        setup.execute("CREATE TABLE evidence(value TEXT NOT NULL)")

    try:
        with pytest.raises(RuntimeError, match="stop"):
            with _component_connection(database) as connection:
                connection.execute("INSERT INTO evidence VALUES('discarded')")
                raise RuntimeError("stop")
        assert connection.execute("SELECT COUNT(*) FROM evidence").fetchone()[0] == 0
    finally:
        close_thread_connections()


def test_explicit_cleanup_closes_cached_handles(tmp_path: Path) -> None:
    connection = _component_connection(tmp_path / "learning.sqlite3")
    close_thread_connections()
    with pytest.raises(sqlite3.ProgrammingError, match="closed database"):
        connection.execute("SELECT 1")


def _hold_transaction(database: str, ready: multiprocessing.Queue) -> None:
    from backend.modules.aion_cognition.sqlite_connection import connect
    with connect(database, timeout=3) as connection:
        connection.execute("INSERT INTO evidence VALUES('first')")
        ready.put(True)
        time.sleep(.25)


def _hold_read_context(database: str, ready: multiprocessing.Queue) -> None:
    from backend.modules.aion_cognition.sqlite_connection import connect_read_only
    with connect_read_only(database, timeout=3) as connection:
        connection.execute("SELECT COUNT(*) FROM evidence").fetchone()
        ready.put(True)
        time.sleep(.4)


def test_separate_process_writers_are_serialised(tmp_path: Path) -> None:
    database = tmp_path / "learning.sqlite3"
    with sqlite3.connect(database) as setup:
        setup.execute("CREATE TABLE evidence(value TEXT NOT NULL)")
    ready: multiprocessing.Queue = multiprocessing.Queue()
    process = multiprocessing.Process(target=_hold_transaction, args=(str(database), ready))
    process.start()
    assert ready.get(timeout=2) is True
    started = time.monotonic()
    try:
        with _component_connection(database) as connection:
            connection.execute("INSERT INTO evidence VALUES('second')")
        assert time.monotonic() - started >= .15
        with sqlite3.connect(database) as check:
            assert check.execute("SELECT COUNT(*) FROM evidence").fetchone()[0] == 2
    finally:
        process.join(timeout=2)
        if process.is_alive():
            process.terminate()


def test_cross_process_reader_finishes_before_writer_starts(tmp_path: Path) -> None:
    database = tmp_path / "learning.sqlite3"
    with sqlite3.connect(database) as setup:
        setup.execute("CREATE TABLE evidence(value TEXT NOT NULL)")
    ready: multiprocessing.Queue = multiprocessing.Queue()
    process = multiprocessing.Process(target=_hold_read_context, args=(str(database), ready))
    process.start()
    assert ready.get(timeout=2) is True
    started = time.monotonic()
    try:
        with _component_connection(database) as connection:
            connection.execute("INSERT INTO evidence VALUES('writer-not-starved')")
        assert time.monotonic() - started >= .3
    finally:
        close_thread_connections()
        process.join(timeout=2)
        if process.is_alive():
            process.terminate()


def test_nested_component_transactions_are_reentrant(tmp_path: Path) -> None:
    database = tmp_path / "learning.sqlite3"

    def first_component() -> sqlite3.Connection:
        return connect(database)

    def second_component() -> sqlite3.Connection:
        return connect(database)

    try:
        with first_component() as first:
            first.execute("CREATE TABLE evidence(value TEXT NOT NULL)")
            first.execute("INSERT INTO evidence VALUES('outer')")
            with second_component() as second:
                second.execute("INSERT INTO evidence VALUES('inner')")
        with sqlite3.connect(database) as check:
            assert check.execute("SELECT COUNT(*) FROM evidence").fetchone()[0] == 2
    finally:
        close_thread_connections()


def test_process_local_writer_wait_is_bounded(tmp_path: Path, monkeypatch) -> None:
    database = tmp_path / "learning.sqlite3"
    with sqlite3.connect(database) as setup:
        setup.execute("CREATE TABLE evidence(value TEXT NOT NULL)")
    monkeypatch.setenv("AION_SQLITE_PROCESS_GATE_TIMEOUT", "0.1")
    occupied = threading.Event()

    def holder() -> None:
        try:
            with connect(database) as connection:
                connection.execute("INSERT INTO evidence VALUES('held')")
                occupied.set()
                time.sleep(.35)
        finally:
            close_thread_connections()

    thread = threading.Thread(target=holder)
    thread.start()
    assert occupied.wait(timeout=1)
    try:
        with pytest.raises(sqlite3.OperationalError, match="process transaction gate timed out"):
            with connect(database) as connection:
                connection.execute("INSERT INTO evidence VALUES('must-retry')")
    finally:
        close_thread_connections()
        thread.join(timeout=1)


def test_read_only_summaries_can_run_concurrently(tmp_path: Path) -> None:
    database = tmp_path / "learning.sqlite3"
    with sqlite3.connect(database) as setup:
        setup.execute("CREATE TABLE evidence(value TEXT NOT NULL)")
    both_inside = threading.Barrier(2)
    finished: list[int] = []

    def reader(index: int) -> None:
        try:
            with connect_read_only(database, timeout=3) as connection:
                connection.execute("SELECT COUNT(*) FROM evidence").fetchone()
                both_inside.wait(timeout=1)
                time.sleep(.1)
                finished.append(index)
        finally:
            close_thread_connections()

    threads = [threading.Thread(target=reader, args=(index,)) for index in range(2)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=2)
    assert sorted(finished) == [0, 1]


def test_read_only_context_releases_shared_lock_for_writer(tmp_path: Path) -> None:
    database = tmp_path / "learning.sqlite3"
    with sqlite3.connect(database) as setup:
        setup.execute("CREATE TABLE evidence(value TEXT NOT NULL)")

    try:
        with connect_read_only(database, timeout=3) as reader:
            assert reader.execute("SELECT COUNT(*) FROM evidence").fetchone()[0] == 0
        started = time.monotonic()
        with connect(database, timeout=3) as writer:
            writer.execute("INSERT INTO evidence VALUES('writer-proceeded')")
        assert time.monotonic() - started < .5
    finally:
        close_thread_connections()


def test_batched_contexts_commit_once_and_roll_back_as_a_unit(tmp_path: Path) -> None:
    database = tmp_path / "learning.sqlite3"
    connection = connect(database, timeout=3)
    try:
        with connection:
            connection.execute("CREATE TABLE evidence(value TEXT NOT NULL)")
        begin_batch(connection)
        with connection:
            connection.execute("INSERT INTO evidence VALUES('one')")
        with connection:
            connection.execute("INSERT INTO evidence VALUES('two')")
        end_batch(connection, success=True)
        assert connection.execute("SELECT COUNT(*) FROM evidence").fetchone()[0] == 2

        begin_batch(connection)
        with connection:
            connection.execute("INSERT INTO evidence VALUES('discarded')")
        end_batch(connection, success=False)
        assert connection.execute("SELECT COUNT(*) FROM evidence").fetchone()[0] == 2
    finally:
        close_thread_connections()


def test_same_process_reader_finishes_before_sibling_writer_starts(tmp_path: Path) -> None:
    database = tmp_path / "learning.sqlite3"
    with sqlite3.connect(database) as setup:
        setup.execute("CREATE TABLE evidence(value TEXT NOT NULL)")
    reader_ready = threading.Event()
    release_reader = threading.Event()
    writer_finished = threading.Event()

    def reader() -> None:
        try:
            with connect(database, timeout=3) as connection:
                connection.execute("SELECT COUNT(*) FROM evidence").fetchone()
                reader_ready.set()
                assert release_reader.wait(timeout=2)
        finally:
            close_thread_connections()

    def writer() -> None:
        try:
            with connect(database, timeout=3) as connection:
                connection.execute("INSERT INTO evidence VALUES('after-reader')")
            writer_finished.set()
        finally:
            close_thread_connections()

    reader_thread = threading.Thread(target=reader)
    writer_thread = threading.Thread(target=writer)
    reader_thread.start()
    assert reader_ready.wait(timeout=2)
    writer_thread.start()
    time.sleep(.1)
    assert writer_finished.is_set() is False
    release_reader.set()
    reader_thread.join(timeout=2)
    writer_thread.join(timeout=2)

    assert writer_finished.is_set() is True
    with sqlite3.connect(database) as check:
        assert check.execute("SELECT COUNT(*) FROM evidence").fetchone()[0] == 1
