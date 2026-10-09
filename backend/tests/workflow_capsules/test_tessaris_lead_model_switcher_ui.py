from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
INDEX = (ROOT / "desktop/mac/src/index.html").read_text(encoding="utf-8")
TOOLBAR = (ROOT / "desktop/mac/src/shell-toolbar.js").read_text(encoding="utf-8")
APP = (ROOT / "desktop/mac/src/app.js").read_text(encoding="utf-8")


def test_toolbar_has_a_workspace_model_switcher_next_to_pilot() -> None:
    switcher = INDEX.index('data-tessaris-model-switcher="true"')
    pilot = INDEX.index('data-tessaris-pilot-control="true"')

    assert switcher < pilot
    assert 'data-tessaris-active-model' in INDEX


def test_toolbar_allows_temporary_switching_without_inventing_a_default() -> None:
    assert 'textContent: "Choose a model"' in TOOLBAR
    assert "modelSelect.disabled = models.length === 0" in TOOLBAR
    assert "Connections remains the only surface that persists the workspace lead" in TOOLBAR
    assert 'source: returnsToDefault ? "connections_lead" : "toolbar_session_override"' in TOOLBAR
    assert "window.sessionStorage.removeItem(modelOverrideKey())" in TOOLBAR


def test_toolbar_keeps_installed_local_models_visible_and_binds_them_on_selection() -> None:
    assert 'item?.id === "local_model" && item?.installed === true' in TOOLBAR
    assert 'Available — select to start' in TOOLBAR
    assert '"http://127.0.0.1:8080/api/vault/local-models/select"' in TOOLBAR
    assert '"X-Aion-Vault-Intent": "select-local-model-v1"' in TOOLBAR


def test_connections_owns_the_persisted_lead_model_choice() -> None:
    assert 'data-aion-set-lead-model=' in APP
    assert '"http://127.0.0.1:8080/api/boardroom/providers/lead"' in APP
    assert 'provider.is_lead ? "Lead model" : "Use as lead"' in APP


def test_marketing_work_uses_the_current_toolbar_selection() -> None:
    assert "window.getTessarisActiveModelSelection?.()" in APP
    assert "selected_provider: activeModel?.provider_id || undefined" in APP
    assert "selected_model: activeModel?.model_id || undefined" in APP
