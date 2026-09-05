from __future__ import annotations

import json
import threading
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path

import pytest

from backend.modules.aion_business.runtime.sovereign_installed_service import build_handler, public_status


ROOT = Path(__file__).resolve().parents[3]


def test_installed_service_reports_setup_required_without_leaking_paths(tmp_path: Path) -> None:
    result = public_status(tmp_path)
    assert result["state"] == "setup_required"
    assert result["secrets_exposed"] is False
    assert str(tmp_path) not in json.dumps(result)


def test_installed_service_reports_ready_from_canonical_files(tmp_path: Path) -> None:
    (tmp_path / "brain").mkdir()
    (tmp_path / "brain/brain_identity.json").write_text("{}", encoding="utf-8")
    (tmp_path / "system").mkdir()
    (tmp_path / "system/supervisor.json").write_text('{"status":"healthy"}', encoding="utf-8")
    (tmp_path / "setup.json").write_text('{"state":"ready"}', encoding="utf-8")
    result = public_status(tmp_path)
    assert result["state"] == "ready"
    assert result["supervisor_status"] == "healthy"


def test_health_server_is_loopback_read_only(tmp_path: Path) -> None:
    server = ThreadingHTTPServer(("127.0.0.1", 0), build_handler(tmp_path))
    worker = threading.Thread(target=server.serve_forever, daemon=True)
    worker.start()
    try:
        address = f"http://127.0.0.1:{server.server_port}"
        with urllib.request.urlopen(address + "/health", timeout=2) as response:
            body = json.loads(response.read())
        assert body["ok"] is True
        request = urllib.request.Request(address + "/status", data=b"{}", method="POST")
        with pytest.raises(urllib.error.HTTPError) as error:
            urllib.request.urlopen(request, timeout=2)
        assert error.value.code == 405
    finally:
        server.shutdown()
        server.server_close()


def test_macos_builder_declares_native_app_and_launch_agent() -> None:
    source = (ROOT / "scripts/build_aion_sovereign_brain_macos_pkg.py").read_text(encoding="utf-8")
    assert "Pilot Setup.app" in source
    assert "Library/LaunchAgents" in source
    assert "sovereign_installed_service" in source
    assert "pkgbuild" in source
