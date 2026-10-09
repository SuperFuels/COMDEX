from pathlib import Path


APP = Path("desktop/mac/src/app.js")


def source() -> str:
    return APP.read_text()


def test_communications_is_a_canonical_sidebar_route() -> None:
    text = source()
    assert '{ key: "communications", label: "Communications" }' in text
    assert 'communications: "communications"' in text
    assert 'state.activeTab === "communications"' in text
    assert "renderAionCommunicationsSurface()" in text


def test_communications_has_the_four_bounded_subtabs() -> None:
    text = source()
    for label in ("Website", "Inbox & Email", "Agent Network", "Phone & Channels"):
        assert f'label: "{label}"' in text


def test_communications_reuses_preserved_systems() -> None:
    text = source()
    assert "renderAionWebsiteIntakeInstallationPanel()" in text
    assert "renderBoardroomA2ASetupPanel(snapshot)" in text
    assert "renderAionPhase18CommercialTicketPanel()" in text


def test_communications_keeps_capability_claims_honest() -> None:
    text = source()
    assert "Live-capable" in text
    assert "Reserved / preview" in text
    assert "real public handshake remains disabled" in text
    assert "public widget hosting must be deployed" in text


def test_communications_does_not_mount_inside_spatial_boardroom() -> None:
    text = source()
    boardroom_start = text.index("function renderBoardroomSurface()")
    communications_start = text.index("function renderAionCommunicationsSurface()")
    boardroom_block = text[boardroom_start:communications_start]
    assert "renderAionCommunicationsSurface" not in boardroom_block


def test_communications_uses_the_inset_command_centre_layout() -> None:
    text = source()
    styles_start = text.index("function installAionCommunicationsWorkspaceStyles()")
    styles_end = text.index("installAionCommunicationsWorkspaceStyles();", styles_start)
    styles = text[styles_start:styles_end]

    assert "padding:16px 32px 80px 96px !important" in styles
    assert "border-top:4px solid #1687d9" in styles
    assert ".aion-comms-tabs { display:flex; gap:28px" in styles
    assert "border-radius:12px !important" in styles


def test_communications_styling_keeps_existing_actions_and_routes() -> None:
    text = source()
    for action in (
        "copyAionCommunicationsValue",
        "openAionCommunicationsRoute('vault')",
        "openAionCommunicationsRoute('live_agents', 'sales')",
        "openAionCommunicationsRoute('live_agents', 'support')",
        "openAionCommunicationsRoute('operations_agents')",
    ):
        assert action in text
