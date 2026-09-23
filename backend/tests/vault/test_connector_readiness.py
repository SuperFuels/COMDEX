from backend.modules.vault.connector_readiness import ConnectorReadinessService
from backend.modules.vault.credential_schema import gmail_oauth_credential
from backend.modules.vault.credential_store import InMemoryVaultCredentialStore


def test_connector_readiness_reports_missing_credential() -> None:
    service = ConnectorReadinessService(InMemoryVaultCredentialStore())

    result = service.check(
        business_id="costa-conexion",
        workspace_id="costa-conexion",
        owner_user_id="user_1",
        connector_id="gmail",
        credential_key="vault.gmail.credentials",
    )

    assert result.ready is False
    assert result.reason == "credential_missing"


def test_connector_readiness_reports_connected_gmail() -> None:
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

    result = ConnectorReadinessService(store).check(
        business_id="costa-conexion",
        workspace_id="costa-conexion",
        owner_user_id="user_1",
        connector_id="gmail",
        credential_key="vault.gmail.credentials",
        required_scopes=[
            "https://www.googleapis.com/auth/gmail.readonly",
            "https://www.googleapis.com/auth/gmail.compose",
        ],
    )

    assert result.ready is True
    assert result.reason == "connector_ready"


def test_connector_readiness_blocks_missing_scope() -> None:
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

    result = ConnectorReadinessService(store).check(
        business_id="costa-conexion",
        workspace_id="costa-conexion",
        owner_user_id="user_1",
        connector_id="gmail",
        credential_key="vault.gmail.credentials",
        required_scopes=[
            "https://www.googleapis.com/auth/gmail.send",
        ],
    )

    assert result.ready is False
    assert result.reason == "missing_required_scopes"


def test_connector_readiness_does_not_cross_user_boundary() -> None:
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

    result = ConnectorReadinessService(store).check(
        business_id="costa-conexion",
        workspace_id="costa-conexion",
        owner_user_id="sales_user",
        connector_id="gmail",
        credential_key="vault.gmail.credentials",
    )

    assert result.ready is False
    assert result.reason == "credential_missing"
