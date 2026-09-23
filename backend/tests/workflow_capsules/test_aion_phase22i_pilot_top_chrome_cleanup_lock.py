from pathlib import Path

TEXT = Path("desktop/mac/src/app.js").read_text(encoding="utf-8")


def test_phase22i_removed_top_runtime_banner_source():
    start = TEXT.index("function renderGlobalStatusBanner")
    end = TEXT.index("function renderStatusBadge", start)
    block = TEXT[start:end]

    assert 'return "";' in block
    assert "Local runtime" not in block
    assert "Local backend ready" not in block
    assert "AION Pilot available from the AION tab" not in block
    assert "Use Pilot Cockpit for mission composer" not in block


def test_phase22i_removed_live_agent_counter_strip_source():
    start = TEXT.index("function renderLiveAgentsStatsStrip")
    end = TEXT.index("function renderLiveAgentHero", start)
    block = TEXT[start:end]

    assert 'return "";' in block
    assert "QUEUED" not in block
    assert "RUNNING" not in block
    assert "WAITING" not in block
    assert "FAILED" not in block
    assert "RUNS" not in block


def test_phase22i_removed_aion_operator_identity_chrome_text():
    start = TEXT.index("function renderAionWorkspaceSurface")
    end = TEXT.index("function renderAgentCommandHeader", start)
    block = TEXT[start:end]

    forbidden = [
        "Native AION operator cockpit for mission planning, safe work, artifacts, approvals, blocked actions, proof and replay.",
        "AION OPERATOR IDENTITY",
        "agent_marketing_operator_v1 is the native AION runtime operator. Pilot is not UI automation.",
        "AION Pilot native runtime",
        "Preview / plan-gated",
        "No live external side effects without exact approval",
    ]

    for marker in forbidden:
        assert marker not in block


def test_phase22i_required_render_functions_still_exist():
    required = [
        "function renderAppTabs",
        "function renderLiveAgentsSurface",
        "function renderAionWorkspaceSurface",
        "function renderAionPilotCockpitPanel",
        "function renderAionPilotSimpleTaskStream",
    ]

    for marker in required:
        assert marker in TEXT


def test_phase22i_pilot_core_still_present():
    required = [
        "It drafts the plan, you choose the human approval stages, and Pilot executes the safe work between them.",
        "Run next safe output",
        "Advanced details: safety, reasoning, proof, hashes and blocked actions",
    ]

    for marker in required:
        assert marker in TEXT
