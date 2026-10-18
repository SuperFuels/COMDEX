from pathlib import Path

APP = Path("desktop/mac/src/app.js")

def source() -> str:
    return APP.read_text()

def test_phase17l_vault_connector_fallback_exists() -> None:
    text = source()
    assert "function renderAionPhase17LSimpleVaultConnectorPanel" in text
    assert "data-aion-phase17l-vault-connector-fallback" in text
    assert "Fallback panel active" in text

def test_operations_flow_no_longer_renders_the_legacy_connector_panel() -> None:
    text = source()
    surface_index = text.find("function renderOperationsFlowSurface")
    surface_end = text.find("function readAionBusinessFoundationStorage", surface_index)
    surface = text[surface_index:surface_end]
    assert surface_index != -1
    assert "renderAionPhase17LSimpleVaultConnectorPanel()" not in surface
