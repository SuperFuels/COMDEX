from pathlib import Path

APP = Path("desktop/mac/src/app.js")

def source() -> str:
    return APP.read_text()

def test_phase17l_vault_connector_fallback_exists() -> None:
    text = source()
    assert "function renderAionPhase17LSimpleVaultConnectorPanel" in text
    assert "data-aion-phase17l-vault-connector-fallback" in text
    assert "Fallback panel active" in text

def test_operations_flow_can_call_phase17l_connector_panel() -> None:
    text = source()
    call_index = text.find("renderAionPhase17LSimpleVaultConnectorPanel")
    surface_index = text.find("function renderOperationsFlowSurface")
    assert call_index != -1
    assert surface_index != -1
    assert call_index < surface_index
