from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
RADIO_SERVER = ROOT / "Glyph_Net_Browser" / "radio-node" / "server.ts"
RADIO_PACKAGE = ROOT / "Glyph_Net_Browser" / "radio-node" / "package.json"


def test_radio_bridge_has_no_default_secret_and_requires_replay_safe_authentication():
    source = RADIO_SERVER.read_text(encoding="utf-8")
    assert 'process.env.RADIO_BRIDGE_TOKEN || ""' in source
    assert '"dev-bridge"' not in source
    assert 'process.env.REQUIRE_BRIDGE_SIG ?? "true"' in source
    assert '"v2,<tsMs>,<nonce>,<hmacHex>"' in source
    assert "seenBridgeNonces" in source
    assert "wave-bridge|${ts}|${nonce}" in source
    assert "const ok = Boolean(sig) && tokenOkWithOptionalSig(token, sig);" in source


def test_radio_bridge_does_not_accept_credentials_in_websocket_query_strings():
    source = RADIO_SERVER.read_text(encoding="utf-8")
    auth_start = source.index("function authTokenFromWS")
    auth_end = source.index("function sigFromWS", auth_start)
    sig_end = source.index("//", auth_end)
    credential_helpers = source[auth_start:sig_end]
    assert ".searchParams" not in credential_helpers
    assert 'req.headers["authorization"]' in credential_helpers
    assert 'req.headers["x-bridge-token"]' in credential_helpers
    assert 'req.headers["x-bridge-sig"]' in credential_helpers


def test_physical_serial_driver_is_real_and_mock_routes_are_explicitly_gated():
    source = RADIO_SERVER.read_text(encoding="utf-8")
    assert "SerialPort" in source
    assert "RF_SERIAL_DEV" in source
    assert "connectSerial" in source
    assert "AUTO_DISABLE_MOCK_ON_REAL_LINK" in source
    assert "ENABLE_RF_MOCK_DEV_ROUTES" in source
    assert 'return res.status(404).json({ ok: false, error: "not found" })' in source


def test_radio_node_uses_current_non_vulnerable_express_major():
    package = RADIO_PACKAGE.read_text(encoding="utf-8")
    assert '"express": "^5.2.1"' in package
