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

