from __future__ import annotations

import sys
import types

import pytest

from backend.modules.glyphvault.key_manager import KeyManager


def test_development_uses_unique_persistent_device_key(tmp_path, monkeypatch):
    monkeypatch.delenv("GLYPHVAULT_ENCRYPTION_KEY_HEX", raising=False)
    monkeypatch.delenv("GLYPHVAULT_KEY_FILE", raising=False)
    path = tmp_path / "glyphvault.key"
    first = KeyManager(runtime_mode="development", development_key_file=str(path))
    second = KeyManager(runtime_mode="development", development_key_file=str(path))
    assert first.key == second.key
    assert len(first.key) == 32
    assert first.source == "unique_development_device_file"
    assert first.key not in {b"0" * 32, b"\x00" * 32, b"0123456789abcdef0123456789abcdef"}


def test_production_fails_closed_without_customer_keystore(monkeypatch, tmp_path):
    monkeypatch.delenv("GLYPHVAULT_ENCRYPTION_KEY_HEX", raising=False)
    monkeypatch.delenv("GLYPHVAULT_KEY_FILE", raising=False)
    monkeypatch.setitem(sys.modules, "keyring", types.SimpleNamespace(get_password=lambda *_: None))
    with pytest.raises(RuntimeError, match="customer keystore key is required"):
        KeyManager(runtime_mode="production", development_key_file=str(tmp_path / "must-not-exist"))


def test_production_reads_platform_keystore_without_writing_key_file(monkeypatch, tmp_path):
    monkeypatch.delenv("GLYPHVAULT_ENCRYPTION_KEY_HEX", raising=False)
    monkeypatch.delenv("GLYPHVAULT_KEY_FILE", raising=False)
    monkeypatch.setitem(sys.modules, "keyring", types.SimpleNamespace(get_password=lambda *_: (b"k" * 32).hex()))
    path = tmp_path / "must-not-exist"
    manager = KeyManager(runtime_mode="production", development_key_file=str(path))
    assert manager.key == b"k" * 32
    assert manager.source == "platform_keychain"
    assert not path.exists()
