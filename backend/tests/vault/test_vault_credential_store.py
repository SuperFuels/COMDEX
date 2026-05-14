from backend.modules.vault.credential_schema import gmail_oauth_credential
from backend.modules.vault.credential_store import InMemoryVaultCredentialStore


def test_store_detects_connected_workspace_user_credential() -> None:
    store = InMemoryVaultCredentialStore()

    store.upsert(
        gmail_oauth_credential(
            business_id="costa-conexion",
            workspace_id="costa-conexion",
            owner_user_id="user_1",
            secret_ref="secret://gmail/user_1",
            status="connected",
        )
    )

    assert store.has_connected_credential(
        business_id="costa-conexion",
        workspace_id="costa-conexion",
        owner_user_id="user_1",
        connector_id="gmail",
        credential_key="vault.gmail.credentials",
    ) is True


def test_store_does_not_leak_credentials_across_users() -> None:
    store = InMemoryVaultCredentialStore()

    store.upsert(
        gmail_oauth_credential(
            business_id="costa-conexion",
            workspace_id="costa-conexion",
            owner_user_id="marketing_user",
            secret_ref="secret://gmail/marketing_user",
            status="connected",
        )
    )

    assert store.has_connected_credential(
        business_id="costa-conexion",
        workspace_id="costa-conexion",
        owner_user_id="sales_user",
        connector_id="gmail",
        credential_key="vault.gmail.credentials",
    ) is False


def test_store_missing_credential_is_not_connected() -> None:
    store = InMemoryVaultCredentialStore()

    store.upsert(
        gmail_oauth_credential(
            business_id="costa-conexion",
            workspace_id="costa-conexion",
            owner_user_id="user_1",
        )
    )

    assert store.has_connected_credential(
        business_id="costa-conexion",
        workspace_id="costa-conexion",
        owner_user_id="user_1",
        connector_id="gmail",
        credential_key="vault.gmail.credentials",
    ) is False


def test_store_lists_only_workspace_credentials() -> None:
    store = InMemoryVaultCredentialStore()

    store.upsert(
        gmail_oauth_credential(
            business_id="costa-conexion",
            workspace_id="workspace_a",
            owner_user_id="user_1",
            secret_ref="secret://gmail/user_1",
            status="connected",
        )
    )
    store.upsert(
        gmail_oauth_credential(
            business_id="costa-conexion",
            workspace_id="workspace_b",
            owner_user_id="user_2",
            secret_ref="secret://gmail/user_2",
            status="connected",
        )
    )

    records = store.list_for_workspace(
        business_id="costa-conexion",
        workspace_id="workspace_a",
    )

    assert len(records) == 1
    assert records[0].scope.owner_user_id == "user_1"
