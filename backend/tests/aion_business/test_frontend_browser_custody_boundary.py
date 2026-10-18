from __future__ import annotations

from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[3]


def _read(relative: str) -> str:
    return (REPOSITORY_ROOT / relative).read_text(encoding="utf-8")


def test_customer_commands_goals_and_science_tabs_are_not_browser_authoritative():
    for relative in (
        "frontend/components/CommandBar.tsx",
        "frontend/components/SQS/SciGoalPanel.tsx",
        "frontend/pages/sci/SciPanelHost.tsx",
    ):
        source = _read(relative)
        assert "localStorage" not in source
        assert "sessionStorage" not in source
        assert "indexedDB" not in source


def test_primary_frontend_authentication_uses_cookie_session_not_browser_tokens():
    for relative in (
        "frontend/lib/api.ts",
        "frontend/lib/siwe.ts",
        "frontend/utils/auth.ts",
        "frontend/utils/authGuard.ts",
        "frontend/hooks/useAuthRedirect.ts",
        "frontend/pages/login.tsx",
        "frontend/pages/register.tsx",
        "frontend/pages/_app.tsx",
        "frontend/components/QuoteModal.tsx",
        "frontend/components/WalletConnect.tsx",
        "frontend/pages/contracts/index.tsx",
        "frontend/pages/deals/create/[product_id].tsx",
        "frontend/pages/deals/index.tsx",
    ):
        source = _read(relative)
        assert "localStorage" not in source
        assert "sessionStorage" not in source
        assert "token: data.token" not in source


def test_glyphnet_login_does_not_relay_session_token_to_loopback_or_persist_identity():
    for relative in (
        "frontend/src/glyphnet/components/TopBar.tsx",
        "frontend/src/glyphnet/components/GlyphNetNavbar.tsx",
    ):
        source = _read(relative)
        assert "localStorage" not in source
        assert "sessionStorage" not in source
        assert "token: data.token" not in source
        assert "/api/session/attach" not in source


def test_theme_toggle_uses_system_or_process_state_only():
    source = _read("frontend/components/DarkModeToggle.tsx")
    assert "localStorage" not in source
    assert "sessionStorage" not in source


def test_pilot_and_legacy_glyphnet_working_state_is_process_local():
    for relative in (
        "frontend/lib/pilot/pairing.ts",
        "frontend/src/glyphnet/components/GlyphChainPerfCard.tsx",
        "frontend/src/glyphnet/components/PhotonMonacoEditor.tsx",
        "frontend/src/glyphnet/components/QfcBioPage.tsx",
        "frontend/src/glyphnet/components/WalletPanel.tsx",
        "frontend/src/glyphnet/components/WaveInbox.tsx",
        "frontend/src/glyphnet/components/WaveOutbox.tsx",
        "frontend/src/glyphnet/lib/addressBook.ts",
        "frontend/src/glyphnet/routes/BridgePanel.tsx",
        "frontend/src/glyphnet/routes/ChatThread.tsx",
        "frontend/src/glyphnet/utils/identity.ts",
        "frontend/src/glyphnet/utils/nameService.ts",
        "frontend/src/glyphnet/utils/transport.ts",
        "frontend/src/glyphnet/hooks/useGlyphnet.ts",
        "frontend/src/glyphnet/hooks/useRadioHealth.ts",
        "frontend/src/glyphnet/lib/constants.ts",
        "frontend/pages/aion/multiverse.tsx",
        "frontend/tabs/cognition/phase7-calibration/Phase7CalibrationHUD.tsx",
    ):
        source = _read(relative)
        assert "localStorage" not in source
        assert "sessionStorage" not in source
        assert "indexedDB" not in source


def test_pilot_private_key_is_never_exported_to_application_storage():
    source = _read("frontend/lib/pilot/pairing.ts")
    identity_source = _read("frontend/src/glyphnet/utils/identity.ts")

    assert "extractable" not in source
    assert "protectedPrivate" in source
    assert 'false, ["sign"]' in source
    assert "privkey_b64" not in identity_source
    assert "processPrivateKey" in identity_source
