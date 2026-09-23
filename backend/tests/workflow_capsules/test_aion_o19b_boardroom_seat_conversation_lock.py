from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
CONVERSATION = (ROOT / "desktop/mac/src/lib/boardroom-seat-conversation.js").read_text()
RENDERER = (ROOT / "desktop/mac/src/lib/desktop-boardroom-renderer.js").read_text()
APP = (ROOT / "desktop/mac/src/app.js").read_text()
INDEX = (ROOT / "desktop/mac/src/index.html").read_text()


def test_boardroom_seats_have_real_click_targets_and_launch_conversation():
    assert "aion_executive_conversation_target_" in RENDERER
    assert "aion_board_conversation_target_" in RENDERER
    assert "teamMode: \"executive\"" in RENDERER
    assert "teamMode: \"board\"" in RENDERER
    assert "AionBoardroomSeatConversation?.open?." in APP


def test_conversation_component_is_loaded_before_app_runtime():
    assert './lib/boardroom-seat-conversation.js' in INDEX
    assert INDEX.index('./lib/boardroom-seat-conversation.js') < INDEX.index('./app.js')


def test_executive_agents_are_department_specific_and_voice_enabled():
    for department in ("marketing", "sales", "finance", "operations", "support", "hr"):
        assert f"{department}: {{" in CONVERSATION
    assert "playLocalVoice" in CONVERSATION
    assert "playSystemVoice" in CONVERSATION
    assert "seatVoices" in CONVERSATION
    assert "requestMicrophonePermission" in CONVERSATION
    assert "/api/aion/voice/stt" in CONVERSATION


def test_board_members_use_selected_live_provider_without_simulation():
    assert "/api/boardroom/providers/status" in CONVERSATION
    assert "/api/boardroom/ask" in CONVERSATION
    assert "requested_providers: [candidate]" in CONVERSATION
    assert "The selected intelligence provider did not return an answer" in CONVERSATION
    assert "AION reasoning route" in CONVERSATION


def test_executive_agents_fail_over_on_rate_limits_but_direct_board_seats_do_not():
    assert "chooseProviderCandidates" in CONVERSATION
    assert "temporarily rate-limited" in CONVERSATION
    assert "return connected.includes(key) ? [key] : []" in CONVERSATION


def test_external_actions_remain_approval_gated():
    assert "Prepare or advise only" in CONVERSATION
    assert "do not claim it happened" in CONVERSATION
    assert "external actions still require" in CONVERSATION
