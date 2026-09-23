from pathlib import Path


def test_vault_contains_guided_twilio_and_retell_setup() -> None:
    source = Path("desktop/mac/src/aion_telephony_vault.js").read_text(encoding="utf-8")
    app = Path("desktop/mac/src/app.js").read_text(encoding="utf-8")

    assert "Connect your AI call centre" in source
    assert "Twilio supplies the number" in source
    assert "Retell speaks, listens" in source
    assert "Standard API key" in source
    assert "sip:sip.retellai.com" in source
    assert "Saving changes" not in source
    assert "Connecting services does not start a call" in source
    assert "/api/vault/telephony/" in source
    assert "AionTelephonyVault.render" in app
    assert "global.AionTelephonyVault = { state, render, load, refresh, open }" in source


def test_telephony_setup_script_is_packaged() -> None:
    index = Path("desktop/mac/src/index.html").read_text(encoding="utf-8")
    assert '<script src="./aion_telephony_vault.js"></script>' in index
