from __future__ import annotations

import argparse
import json
import os
import platform
import secrets
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Dict


SERVICE_SCHEMA = "aion.sovereign_installed_service.v1"
ENDPOINT_SCHEMA = "tessaris.node-health-endpoint.v1"


def default_brain_root() -> Path:
    configured = os.environ.get("TESSARIS_PILOT_BRAIN_ROOT")
    if configured:
        return Path(configured).expanduser()
    system = platform.system()
    if system == "Darwin":
        return Path.home() / "Library" / "Application Support" / "Pilot Brain"
    if system == "Windows":
        base = Path(os.environ.get("LOCALAPPDATA") or (Path.home() / "AppData" / "Local"))
        return base / "Tessaris" / "Pilot Brain"
    base = Path(os.environ.get("XDG_DATA_HOME") or (Path.home() / ".local" / "share"))
    return base / "tessaris" / "pilot-brain"


def default_node_state_root() -> Path:
    """Return disposable node state outside the app and Business Vault roots."""

    configured = os.environ.get("TESSARIS_NODE_STATE_ROOT")
    if configured:
        return Path(configured).expanduser()
    system = platform.system()
    if system == "Darwin":
        return Path.home() / "Library" / "Application Support" / "Tessaris Node"
    if system == "Windows":
        base = Path(
            os.environ.get("PROGRAMDATA")
            or os.environ.get("LOCALAPPDATA")
            or (Path.home() / "AppData" / "Local")
        )
        return base / "Tessaris Node"
    runtime_root = os.environ.get("XDG_RUNTIME_DIR")
    if runtime_root:
        return Path(runtime_root) / "tessaris-node"
    state_root = Path(os.environ.get("XDG_STATE_HOME") or (Path.home() / ".local" / "state"))
    return state_root / "tessaris" / "node"


def prepare_node_state_root(root: str | Path | None = None) -> Path:
    """Create an owner-only Node state root outside application/update/Vault roots."""

    candidate = Path(root) if root is not None else default_node_state_root()
    resolved = candidate.expanduser().resolve(strict=False)
    protected_values = (
        os.environ.get("TESSARIS_APPLICATION_ROOT"),
        os.environ.get("TESSARIS_UPDATE_ROOT"),
        os.environ.get("TESSARIS_BUSINESS_VAULT_ROOT"),
        os.environ.get("TESSARIS_BUSINESS_VAULT_PATH"),
    )
    for value in protected_values:
        if not str(value or "").strip():
            continue
        protected = Path(str(value)).expanduser().resolve(strict=False)
        try:
            overlap = (
                os.path.commonpath((str(resolved), str(protected))) == str(resolved)
                or os.path.commonpath((str(resolved), str(protected))) == str(protected)
            )
        except ValueError:
            overlap = False
        if overlap:
            raise ValueError("node_state_root_overlaps_protected_root")
    resolved.mkdir(parents=True, exist_ok=True)
    try:
        resolved.chmod(0o700)
    except OSError:
        pass
    return resolved


def default_health_endpoint_path() -> Path:
    return default_node_state_root() / "health-endpoint.json"


def _write_endpoint_record(path: Path, *, host: str, port: int) -> dict[str, Any]:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        path.parent.chmod(0o700)
    except OSError:
        pass
    record = {
        "schema_version": ENDPOINT_SCHEMA,
        "host": host,
        "port": int(port),
        "pid": os.getpid(),
        "instance_id": secrets.token_hex(16),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "content_free": True,
    }
    temporary = path.with_name(f".{path.name}.{record['instance_id']}.tmp")
    temporary.write_text(
        json.dumps(record, sort_keys=True, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )
    try:
        temporary.chmod(0o600)
    except OSError:
        pass
    temporary.replace(path)
    try:
        path.chmod(0o600)
    except OSError:
        pass
    return record


def remove_endpoint_record(path: str | Path, *, instance_id: str) -> None:
    """Remove only the locator created by this exact service instance."""

    endpoint_path = Path(path)
    try:
        current = json.loads(endpoint_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return
    if current.get("instance_id") != instance_id:
        return
    try:
        endpoint_path.unlink()
    except FileNotFoundError:
        pass


def public_status(root: str | Path) -> Dict[str, Any]:
    brain_root = Path(root).resolve()
    setup_path = brain_root / "setup.json"
    identity_path = brain_root / "brain" / "brain_identity.json"
    supervisor_path = brain_root / "system" / "supervisor.json"
    setup: Dict[str, Any] = {}
    supervisor: Dict[str, Any] = {}
    if setup_path.is_file():
        try:
            setup = json.loads(setup_path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            setup = {}
    if supervisor_path.is_file():
        try:
            supervisor = json.loads(supervisor_path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            supervisor = {}
    ready = setup.get("state") == "ready" and identity_path.is_file()
    return {
        "schema_version": SERVICE_SCHEMA,
        "ok": True,
        "service": "pilot-sovereign-brain",
        "state": "ready" if ready else "setup_required",
        "brain_present": ready,
        "supervisor_status": supervisor.get("status") or "not_initialized",
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "secrets_exposed": False,
    }


def build_handler(root: str | Path):
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802
            if self.path not in {"/health", "/status"}:
                self.send_error(404)
                return
            payload = json.dumps(public_status(root), sort_keys=True).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def do_POST(self) -> None:  # noqa: N802
            self.send_error(405)

        def log_message(self, *_: Any) -> None:
            return

    return Handler


def create_health_server(
    *,
    root: str | Path,
    host: str = "127.0.0.1",
    port: int = 0,
    endpoint_path: str | Path | None = None,
) -> tuple[ThreadingHTTPServer, dict[str, Any], Path]:
    if host not in {"127.0.0.1", "localhost", "::1"}:
        raise ValueError("Installed brain health service must remain on loopback")
    if not isinstance(port, int) or port < 0 or port > 65535:
        raise ValueError("Installed brain health service port is invalid")
    record_path = Path(endpoint_path) if endpoint_path is not None else default_health_endpoint_path()
    brain_root = Path(root).expanduser().resolve()
    if record_path.expanduser().resolve().is_relative_to(brain_root):
        raise ValueError("Node endpoint state must remain outside the Business Vault root")
    server = ThreadingHTTPServer((host, port), build_handler(root))
    try:
        record = _write_endpoint_record(
            record_path,
            host=host,
            port=int(server.server_port),
        )
    except Exception:
        server.server_close()
        raise
    return server, record, record_path


def serve(
    *,
    root: str | Path,
    host: str = "127.0.0.1",
    port: int = 0,
    endpoint_path: str | Path | None = None,
) -> None:
    server, endpoint, record_path = create_health_server(
        root=root,
        host=host,
        port=port,
        endpoint_path=endpoint_path,
    )
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
        remove_endpoint_record(record_path, instance_id=str(endpoint["instance_id"]))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="pilot-brain-service")
    parser.add_argument("--root", type=Path, default=default_brain_root())
    parser.add_argument("--port", type=int, default=0)
    parser.add_argument("--port-file", type=Path, default=default_health_endpoint_path())
    args = parser.parse_args(argv)
    serve(root=args.root, port=args.port, endpoint_path=args.port_file)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
