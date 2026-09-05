from __future__ import annotations

import argparse
import json
import os
import platform
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Dict


SERVICE_SCHEMA = "aion.sovereign_installed_service.v1"


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


def serve(*, root: str | Path, host: str = "127.0.0.1", port: int = 8776) -> None:
    if host not in {"127.0.0.1", "localhost", "::1"}:
        raise ValueError("Installed brain health service must remain on loopback")
    server = ThreadingHTTPServer((host, port), build_handler(root))
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="pilot-brain-service")
    parser.add_argument("--root", type=Path, default=default_brain_root())
    parser.add_argument("--port", type=int, default=8776)
    args = parser.parse_args(argv)
    serve(root=args.root, port=args.port)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
