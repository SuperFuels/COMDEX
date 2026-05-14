from backend.modules.vault.credential_schema import (
    CredentialScope,
    VaultCredential,
    gmail_oauth_credential,
)


def test_vault_credential_public_dict_never_exposes_secret_ref_value() -> None:
    credential = VaultCredential(
        credential_id="cred_1",
        connector_id="gmail",
        credential_key="vault.gmail.credentials",
        credential_type="oauth_token",
        scope=CredentialScope(
            business_id="costa-conexion",
            workspace_id="costa-conexion",
            owner_user_id="user_1",
        ),
        status="connected",
        secret_ref="secret://gmail/user_1",
    )

    public = credential.safe_public_dict()

    assert public["connected"] is True
    assert public["has_secret_ref"] is True
    assert "secret_ref" not in public
    assert "secret://gmail/user_1" not in str(public)


def test_private_record_contains_secret_ref_but_not_raw_secret_value() -> None:
    credential = VaultCredential(
        credential_id="cred_1",
        connector_id="gmail",
        credential_key="vault.gmail.credentials",
        credential_type="oauth_token",
        scope=CredentialScope(
            business_id="costa-conexion",
            workspace_id="costa-conexion",
            owner_user_id="user_1",
        ),
        status="connected",
        secret_ref="secret://gmail/user_1",
    )

    private = credential.to_private_record()

    assert private["secret_ref"] == "secret://gmail/user_1"
    assert "access_token" not in private
    assert "refresh_token" not in private
    assert "password" not in private


def test_gmail_oauth_credential_uses_oauth_not_password() -> None:
    credential = gmail_oauth_credential(
        business_id="costa-conexion",
        workspace_id="costa-conexion",
        owner_user_id="user_1",
        secret_ref="secret://gmail/user_1",
        status="connected",
    )

    assert credential.connector_id == "gmail"
    assert credential.credential_key == "vault.gmail.credentials"
    assert credential.credential_type == "oauth_token"
    assert credential.is_connected() is True
    assert credential.live_send_enabled is False
    assert credential.live_write_enabled is False
    assert "https://www.googleapis.com/auth/gmail.readonly" in credential.scopes
    assert "https://www.googleapis.com/auth/gmail.compose" in credential.scopes
    assert "https://www.googleapis.com/auth/gmail.send" not in credential.scopes


def test_missing_credential_requires_reconnect() -> None:
    credential = gmail_oauth_credential(
        business_id="costa-conexion",
        workspace_id="costa-conexion",
        owner_user_id="user_1",
    )

    assert credential.status == "missing"
    assert credential.is_connected() is False
    assert credential.requires_reconnect() is True
