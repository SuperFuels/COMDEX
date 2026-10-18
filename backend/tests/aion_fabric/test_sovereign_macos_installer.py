from __future__ import annotations

import json
import threading
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path

import pytest

from backend.modules.aion_business.runtime.sovereign_installed_service import (
    ENDPOINT_SCHEMA,
    build_handler,
    create_health_server,
    public_status,
    remove_endpoint_record,
)


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


def test_dynamic_health_endpoint_record_is_content_free_and_instance_owned(tmp_path: Path) -> None:
    endpoint_path = tmp_path / "node-state" / "health-endpoint.json"
    server, endpoint, written_path = create_health_server(
        root=tmp_path / "business-vault-must-not-appear",
        host="127.0.0.1",
        port=0,
        endpoint_path=endpoint_path,
    )
    try:
        persisted = json.loads(endpoint_path.read_text(encoding="utf-8"))
        assert written_path == endpoint_path
        assert persisted["schema_version"] == ENDPOINT_SCHEMA
        assert persisted["port"] == server.server_port
        assert persisted["port"] > 0
        assert persisted["host"] == "127.0.0.1"
        assert persisted["content_free"] is True
        assert str(tmp_path) not in json.dumps(persisted)
        remove_endpoint_record(endpoint_path, instance_id="different-service-instance")
        assert endpoint_path.is_file()
    finally:
        server.server_close()
        remove_endpoint_record(endpoint_path, instance_id=str(endpoint["instance_id"]))
    assert not endpoint_path.exists()


def test_health_server_rejects_public_bind_and_invalid_port(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="loopback"):
        create_health_server(root=tmp_path, host="0.0.0.0", endpoint_path=tmp_path / "a.json")
    with pytest.raises(ValueError, match="port is invalid"):
        create_health_server(root=tmp_path, port=70000, endpoint_path=tmp_path / "b.json")
    vault_root = tmp_path / "business-vault"
    with pytest.raises(ValueError, match="outside the Business Vault"):
        create_health_server(
            root=vault_root,
            port=0,
            endpoint_path=vault_root / "health-endpoint.json",
        )


def test_macos_builder_declares_native_app_and_launch_agent() -> None:
    source = (ROOT / "scripts/build_aion_sovereign_brain_macos_pkg.py").read_text(encoding="utf-8")
    assert "Pilot Setup.app" in source
    assert "Library/LaunchAgents" in source
    assert "sovereign_installed_service" in source
    assert '"--port", "0"' in source
    assert '"--port", "8776"' not in source
    assert "pkgbuild" in source
