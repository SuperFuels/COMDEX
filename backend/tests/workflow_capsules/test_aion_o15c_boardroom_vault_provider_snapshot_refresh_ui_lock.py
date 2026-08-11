from pathlib import Path

APP = Path("desktop/mac/src/app.js")


def test_o15c_boardroom_vault_provider_snapshot_refresh_installed():
    text = APP.read_text(encoding="utf-8")

    assert "BEGIN AION O15C BOARDROOM VAULT PROVIDER SNAPSHOT REFRESH LOCK" in text
    assert "refreshVaultProvidersForBoardroomO15C" in text
    assert "/api/vault/ai-providers" in text
    assert "mergeConnectedProvidersIntoSnapshotO15C" in text


def test_o15c_merges_connected_gemini_into_boardroom_snapshot():
    text = APP.read_text(encoding="utf-8")

    assert "Gemini / Google" in text
    assert "seat_provider_${id}" in text
    assert "provider_source: \"o15c_vault_ai_provider_status\"" in text
    assert "getBoardroomSnapshot = wrapped" in text


def test_o15c_forces_spatial_renderer_update_after_vault_refresh():
    text = APP.read_text(encoding="utf-8")

    assert "TessarisDesktopBoardroomRenderer.updateBoardroom" in text
    assert "spatialBoardroomMount" in text
    assert "renderBoardroomSurfaceWithProviderRefreshO15C" in text


def test_main_provider_suite_is_connectable_from_the_vault():
    text = APP.read_text(encoding="utf-8")

    assert 'id: "meta"' in text
    assert 'id: "mistral"' in text
    assert 'id: "deepseek"' in text
    assert "data-aion-vault-ai-save" in text
    assert "data-aion-vault-ai-delete" in text
    assert "data-aion-vault-boardroom-member" in text
    assert "getAionSelectedBoardroomProviderIdsV1" in text
    assert "Receipt reading:" in text
