from pathlib import Path


APP = Path("desktop/mac/src/app.js")


def source() -> str:
    return APP.read_text()


def operations_flow_surface() -> str:
    text = source()
    start = text.index("function renderOperationsFlowSurface()")
    end = text.index("\nfunction readAionBusinessFoundationStorage", start)
    return text[start:end]


def test_operations_flow_does_not_embed_workflow_tabs_or_business_dashboard() -> None:
    block = operations_flow_surface()

    assert "renderAppTabs()" not in block
    assert "renderDashboardBodyOnly()" not in block
    assert "renderAionPhase17LSimpleVaultConnectorPanel()" not in block
    assert 'class="surface-header"' not in block
    assert "DESKTOP · OPERATIONS FLOW" not in block
    assert 'id="operationsFlowMount"' not in block


def test_operations_flow_does_not_duplicate_the_coo_loop_with_a_system_map() -> None:
    block = operations_flow_surface()

    assert "renderAionCooCommandCentreV1()" in block
    assert "renderOperationsFlowModeToggle()" not in block
    assert "operating system map" not in block


def test_operations_flow_is_not_classified_as_train_agent_workflow_chrome() -> None:
    text = source()

    forbidden_route_pairs = (
        'route === "operations_flow" || route === "operations_agents"',
        'route === "operations_agents" || route === "operations_flow"',
        'active === "operations_flow" || active === "operations_agents"',
        'activeTabForChrome === "operations_flow" || activeTabForChrome === "operations_agents"',
    )

    for forbidden in forbidden_route_pairs:
        assert forbidden not in text


def test_operations_flow_receives_the_shared_executive_header() -> None:
    text = source()
    start = text.index("const AION_SHARED_EXECUTIVE_HEADER_TABS_V1")
    end = text.index("function renderAionSharedPageExecutiveHeaderV1", start)
    shared_routes = text[start:end]

    assert '"operations_flow"' in shared_routes
    assert 'route === "operations_flow" ? "operations" : ""' in text
