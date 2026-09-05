from __future__ import annotations

import pytest

from backend.modules.aion_fabric.google_oauth import PersonaGoogleOAuth
from backend.modules.aion_fabric.private_identity import ProductionPrivateIdentity


def test_persona_pkce_state_scope_and_opaque_vault_binding(tmp_path):
    identities = ProductionPrivateIdentity(tmp_path); owner = identities.onboard(display_name="Owner")
    oauth = PersonaGoogleOAuth(tmp_path, identities=identities)
    started = oauth.begin(persona_id=owner["persona_id"], services=["calendar", "email_send"], client_id="pilot.apps.googleusercontent.com", redirect_uri="http://127.0.0.1:49152/oauth/callback")
    assert "code_challenge_method=S256" in started["authorization_url"]
    assert started["embedded_browser_forbidden"] is True
    with pytest.raises(PermissionError):
        oauth.complete(authorization_id=started["authorization_id"], state_token="wrong", code="code", token_exchange=lambda *_: {}, vault_store=lambda *_: "vault://bad")
    seen = {}
    def vault_store(persona_id, tokens):
        seen["persona"] = persona_id; seen["tokens"] = tokens; return "vault://macos-keychain/pilot-google-owner"
    result = oauth.complete(
        authorization_id=started["authorization_id"], state_token=started["state"], code="code",
        token_exchange=lambda pending, _code: {"access_token": "access", "refresh_token": "refresh", "expires_in": 3600, "token_type": "Bearer", "scope": " ".join(pending["scopes"])},
        vault_store=vault_store,
    )
    assert result["raw_tokens_retained_in_fabric"] is False
    assert oauth.snapshot(persona_id=owner["persona_id"])["raw_tokens_exposed"] is False
    assert seen["persona"] == owner["persona_id"]
