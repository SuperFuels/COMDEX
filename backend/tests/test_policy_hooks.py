# backend/tests/test_policy_hooks.py
import os, sys, importlib, hashlib, textwrap
import pytest

# Ensure the .photon importer is registered for these tests
import backend.modules.photonlang.importer as _photon_importer  # side-effect: installs finder

def _write(tmp_path, name, body):
    p = tmp_path / name
    p.write_text(textwrap.dedent(body), encoding="utf-8")
    return p

def _add_to_path(tmp_path, monkeypatch):
    monkeypatch.syspath_prepend(str(tmp_path))

def _flush_import(name: str):
    sys.modules.pop(name, None)
    importlib.invalidate_caches()

def test_host_deny_blocks_import(monkeypatch, tmp_path):
    _add_to_path(tmp_path, monkeypatch)
    _write(tmp_path, "deny_os.photon", """
        import os
        def ok(): return 1
    """)
    monkeypatch.setenv("PHOTON_HOST_DENY", "os")
    monkeypatch.delenv("PHOTON_HOST_ALLOW", raising=False)
    monkeypatch.delenv("PHOTON_SIG_SHA256", raising=False)
    _flush_import("deny_os")

    with pytest.raises(ImportError):
        importlib.import_module("deny_os")

def test_sig_sha256_mismatch_raises(monkeypatch, tmp_path):
    _add_to_path(tmp_path, monkeypatch)
    raw = """
        # trivial module
        x = 7
        def val(): return x
    """
    _write(tmp_path, "bad_sig.photon", raw)
    monkeypatch.setenv("PHOTON_SIG_SHA256", "0"*64)
    monkeypatch.delenv("PHOTON_HOST_DENY", raising=False)
    monkeypatch.delenv("PHOTON_HOST_ALLOW", raising=False)
    _flush_import("bad_sig")

    with pytest.raises(ImportError):
        importlib.import_module("bad_sig")

def test_sig_sha256_match_allows(monkeypatch, tmp_path):
    _add_to_path(tmp_path, monkeypatch)
    raw = """
        y = 41
        def inc(): return y + 1
    """
    path = _write(tmp_path, "good_sig.photon", raw)

    # ✅ Hash the exact bytes the importer will read
    hexhash = hashlib.sha256(path.read_bytes()).hexdigest()

    monkeypatch.setenv("PHOTON_SIG_SHA256", hexhash)
    monkeypatch.delenv("PHOTON_HOST_DENY", raising=False)
    monkeypatch.delenv("PHOTON_HOST_ALLOW", raising=False)
    _flush_import("good_sig")

    m = importlib.import_module("good_sig")
    assert m.inc() == 42