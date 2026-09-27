from __future__ import annotations

import ast
import os
from pathlib import Path
import sqlite3

import pytest

from backend.modules.aion_business.runtime.aion_flow_session_authority import (
    AionFlowSessionAuthority,
)


SECRET = b"signed-desktop-session-test-secret-32-bytes-minimum"
NOW = 1_790_000_000
ROOT = Path(__file__).resolve().parents[3]


def _authority(tmp_path: Path, **overrides) -> AionFlowSessionAuthority:
    return AionFlowSessionAuthority(
        secret=SECRET,
        clock=lambda: NOW,
        replay_store_path=tmp_path / "security" / "desktop-session.replay.sqlite3",
        persistent_replay=True,
        **overrides,
    )


def _signed(authority: AionFlowSessionAuthority, *, nonce: str = "nonce_0123456789abcdef") -> dict[str, str]:
    return authority.sign_for_test(
        method="POST",
        target="/api/aion/business/legal-signing/list",
        body=b"{}",
        device_id="desktop-device-1",
        person_id="owner-1",
        workspace_id="workspace-a",
        issued_at=NOW,
        nonce=nonce,
    )


def _verify(authority: AionFlowSessionAuthority, headers: dict[str, str]) -> None:
    authority.verify(
        method="POST",
        target="/api/aion/business/legal-signing/list",
        body=b"{}",
        headers=headers,
    )


def test_persistent_replay_store_rejects_nonce_after_authority_restart(tmp_path):
    first = _authority(tmp_path)
    headers = _signed(first)
    _verify(first, headers)

    restarted = _authority(tmp_path)
    with pytest.raises(PermissionError, match="signed_aion_flow_session_replayed"):
        _verify(restarted, headers)


def test_replay_store_persists_only_nonce_hash_with_private_permissions(tmp_path):
    authority = _authority(tmp_path)
    raw_nonce = "private_nonce_0123456789abcdef"
    _verify(authority, _signed(authority, nonce=raw_nonce))

    store = authority.replay_store_path
    assert store.exists()
    assert os.stat(store).st_mode & 0o777 == 0o600
    assert raw_nonce.encode("utf-8") not in store.read_bytes()
    with sqlite3.connect(store) as connection:
        rows = connection.execute(
            "SELECT nonce_hash, expires_at, created_at FROM used_nonces"
        ).fetchall()
    assert len(rows) == 1
    assert len(rows[0][0]) == 64
    assert rows[0][1] == NOW + authority.maximum_age_seconds
    assert rows[0][2] == NOW


def test_replay_store_is_bounded_and_fails_closed_at_capacity(tmp_path):
    authority = _authority(tmp_path, maximum_replay_entries=100)
    for index in range(100):
        nonce = f"nonce_{index:016d}"
        _verify(authority, _signed(authority, nonce=nonce))

    with pytest.raises(
        PermissionError,
        match="signed_aion_flow_session_replay_store_capacity_exceeded",
    ):
        _verify(authority, _signed(authority, nonce="nonce_capacity_0000000001"))


def test_unavailable_persistent_replay_store_fails_closed(tmp_path):
    store_as_directory = tmp_path / "replay-store-is-a-directory"
    store_as_directory.mkdir()
    authority = AionFlowSessionAuthority(
        secret=SECRET,
        clock=lambda: NOW,
        replay_store_path=store_as_directory,
        persistent_replay=True,
    )
    with pytest.raises(RuntimeError, match="aion_flow_replay_store_unavailable"):
        _verify(authority, _signed(authority))


@pytest.mark.parametrize(
    ("header", "value", "expected"),
    [
        ("x-aion-flow-device-id", "device\nforged", "identity_invalid"),
        ("x-aion-flow-body-sha256", "not-a-digest", "body_hash_invalid"),
        ("x-aion-flow-signature", "not-a-signature", "signature_invalid"),
        ("x-aion-flow-nonce", "short", "nonce_invalid"),
    ],
)
def test_signed_session_rejects_malformed_security_headers(
    tmp_path, header: str, value: str, expected: str
):
    authority = _authority(tmp_path)
    headers = _signed(authority)
    headers[header] = value
    with pytest.raises(PermissionError, match=expected):
        _verify(authority, headers)


def test_signed_session_rejects_invalid_or_oversized_targets(tmp_path):
    authority = _authority(tmp_path)
    for target in ("api/no-leading-slash", "/" + "x" * 4096):
        body = b"{}"
        headers = authority.sign_for_test(
            method="POST",
            target=target,
            body=body,
            device_id="desktop-device-1",
            person_id="owner-1",
            workspace_id="workspace-a",
            issued_at=NOW,
        )
        with pytest.raises(PermissionError, match="target_invalid"):
            authority.verify(method="POST", target=target, body=body, headers=headers)


def test_electron_signer_allows_only_the_three_protected_route_families():
    source = (ROOT / "desktop/mac/electron/main.js").read_text(encoding="utf-8")
    function = source[source.index("function signAionFlowRequest"):source.index("\nfunction wait", source.index("function signAionFlowRequest"))]

    for prefix in (
        "/api/workflow-capsules/aion-flow/",
        "/api/aion/business/legal-signing/",
        "/api/aion/business/glyphchain-admin/",
    ):
        assert f'"{prefix}"' in function
    assert "outside the signed boundary" in function
    assert "/api/aion/business/finance" not in function


def _decorated_routes(path: Path, router_name: str) -> list[tuple[str, str]]:
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source)
    routes: list[tuple[str, str]] = []
    for node in tree.body:
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        for decorator in node.decorator_list:
            if not isinstance(decorator, ast.Call) or not isinstance(decorator.func, ast.Attribute):
                continue
            owner = decorator.func.value
            if not isinstance(owner, ast.Name) or owner.id != router_name:
                continue
            if decorator.func.attr not in {"get", "post", "put", "patch", "delete"}:
                continue
            route = decorator.args[0].value if decorator.args and isinstance(decorator.args[0], ast.Constant) else ""
            routes.append((str(route), ast.get_source_segment(source, node) or ""))
    return routes


def test_all_private_legal_and_glyphchain_admin_routes_require_signed_session():
    legal = ROOT / "backend/modules/aion_business/api/legal_signing_api.py"
    glyphchain = ROOT / "backend/modules/aion_business/api/glyphchain_admin_api.py"

    legal_routes = _decorated_routes(legal, "router")
    assert len(legal_routes) >= 50
    public_token_routes = {"/sign/{token}", "/sign/{token}/decline"}
    for route, function in legal_routes:
        if route in public_token_routes:
            assert "Depends(require_legal_session)" not in function
        else:
            assert "Depends(require_legal_session)" in function, route

    glyphchain_routes = _decorated_routes(glyphchain, "router")
    assert len(glyphchain_routes) >= 20
    for route, function in glyphchain_routes:
        assert "Depends(require_signed_desktop_admin)" in function, route
