from __future__ import annotations

import hashlib
import json

from backend.scripts.aion_security_sentinel_agent import SecuritySentinel


def test_sentinel_writes_private_status_and_redacted_events(tmp_path):
    watched = tmp_path / "watched"; watched.mkdir(); (watched / "file.txt").write_text("safe")
    sentinel = SecuritySentinel(root=tmp_path / "state", watch_roots=[watched])
    sentinel.emit("test", "HIGH", "Test event", "password=do-not-store token:also-secret", "test")
    status = sentinel.cycle()
    assert status["state"] == "review"
    assert status["mode"] == "LOCAL_OBSERVE_ONLY"
    event_text = (tmp_path / "state" / "events.jsonl").read_text()
    assert "do-not-store" not in event_text and "also-secret" not in event_text
    assert ((tmp_path / "state" / "status.json").stat().st_mode & 0o777) == 0o600


def test_sentinel_detects_rapid_file_change_pattern(tmp_path):
    watched = tmp_path / "watched"; watched.mkdir()
    for index in range(60): (watched / f"{index}.txt").write_text("one")
    sentinel = SecuritySentinel(root=tmp_path / "state", watch_roots=[watched])
    sentinel._compare("files", sentinel.file_snapshot())
    for index in range(60): (watched / f"{index}.txt").write_text("two")
    sentinel._compare("files", sentinel.file_snapshot())
    events = (tmp_path / "state" / "events.jsonl").read_text()
    assert "Rapid file-change pattern detected" in events and "CRITICAL" in events


def test_sentinel_matches_approved_malware_digest_without_storing_path(tmp_path, monkeypatch):
    executable = tmp_path / "sample"; executable.write_bytes(b"known sample")
    value = hashlib.sha256(executable.read_bytes()).hexdigest()
    feed = tmp_path / "state" / "workspace"; feed.mkdir(parents=True)
    (feed / "vulnerability-feed.json").write_text(json.dumps({"malware_hashes": [{"sha256": value}]}))
    monkeypatch.setenv("TESSARIS_CYBERSECURITY_FEED_ROOT", str(tmp_path / "state"))
    sentinel = SecuritySentinel(root=tmp_path / "state")
    monkeypatch.setattr(sentinel, "_run", lambda *_args, **_kwargs: f"1 0 user {executable}\n")
    snapshot = sentinel.process_snapshot(); sentinel._previous["processes"] = snapshot
    assert sentinel.malware_hash_snapshot()["matches"] == [value]
    assert str(executable) not in json.dumps(snapshot)


def test_sentinel_baseline_does_not_alert(tmp_path):
    sentinel = SecuritySentinel(root=tmp_path / "state")
    sentinel._compare("usb", {"digest": "first"})
    assert not (tmp_path / "state" / "events.jsonl").exists()


def test_sentinel_flags_new_risky_attachment_without_reading_contents(tmp_path):
    watched = tmp_path / "Downloads"; watched.mkdir()
    sentinel = SecuritySentinel(root=tmp_path / "state", watch_roots=[watched])
    sentinel._compare("files", sentinel.file_snapshot())
    (watched / "invoice.pdf.command").write_text("not executed")
    sentinel._compare("files", sentinel.file_snapshot())
    event_text = (tmp_path / "state" / "events.jsonl").read_text()
    assert "Potentially risky downloaded file observed" in event_text
    assert "invoice.pdf.command" not in event_text


def test_sentinel_matches_hashed_network_indicator_without_storing_destination(tmp_path, monkeypatch):
    remote = "203.0.113.7:443"
    feed = tmp_path / "state" / "workspace"; feed.mkdir(parents=True)
    indicator = hashlib.sha256(remote.encode()).hexdigest()
    (feed / "vulnerability-feed.json").write_text(json.dumps({"malicious_endpoint_hashes": [indicator]}))
    monkeypatch.setenv("TESSARIS_CYBERSECURITY_FEED_ROOT", str(tmp_path / "state"))
    sentinel = SecuritySentinel(root=tmp_path / "state")
    monkeypatch.setattr(sentinel, "_run", lambda *_args, **_kwargs: f"COMMAND PID USER FD TYPE DEVICE SIZE/OFF NODE NAME\ncurl 1 user 1u IPv4 1 0t0 TCP 127.0.0.1:5555->{remote} (ESTABLISHED)\n")
    snapshot = sentinel.network_snapshot()
    assert snapshot["records"][0]["threat_match"] is True
    assert remote not in json.dumps(snapshot)
