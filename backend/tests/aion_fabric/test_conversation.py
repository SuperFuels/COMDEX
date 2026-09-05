from __future__ import annotations

from backend.modules.aion_fabric.conversation import ConversationMemory
from backend.modules.aion_fabric.voice import VoiceControlService


def test_conversation_persists_objective_and_natural_corrections(tmp_path):
    memory = ConversationMemory(tmp_path)
    first = memory.prepare_request("Plan a weekend in Granada for us")
    assert first["is_refinement"] is False
    second = memory.prepare_request("Make it cheaper")
    assert second["is_refinement"] is True
    assert second["objective"] == "Plan a weekend in Granada for us"
    assert "Make it cheaper" in second["composed_request"]
    restarted = ConversationMemory(tmp_path).snapshot()
    assert restarted["active_objective"] == "Plan a weekend in Granada for us"
    assert restarted["constraints"] == ["Make it cheaper"]


def test_new_objective_interrupts_but_does_not_merge_old_task(tmp_path):
    memory = ConversationMemory(tmp_path)
    memory.prepare_request("Find extendable ladders near Albox")
    next_request = memory.prepare_request("Plan a weekend in Granada")
    assert next_request["composed_request"] == "Plan a weekend in Granada"
    assert memory.snapshot()["interrupted_task_count"] == 1


def test_pause_and_resume_restore_objective_and_constraints(tmp_path):
    memory = ConversationMemory(tmp_path)
    memory.prepare_request("Plan a weekend in Granada")
    memory.prepare_request("Make it cheaper")
    assert memory.pause_active()["objective"] == "Plan a weekend in Granada"
    assert memory.snapshot()["active_objective"] is None
    resumed = memory.resume_previous()
    assert resumed["objective"] == "Plan a weekend in Granada"
    assert "Make it cheaper" in resumed["composed_request"]


def test_cancel_removes_active_conversation_instead_of_only_acknowledging(tmp_path):
    memory = ConversationMemory(tmp_path)
    memory.prepare_request("Plan a weekend in Granada")
    memory.prepare_request("Make it cheaper")

    cancelled = memory.cancel_active()

    assert cancelled["objective"] == "Plan a weekend in Granada"
    assert memory.snapshot()["active_objective"] is None
    assert memory.snapshot()["constraints"] == []


def test_explicit_refinement_requires_an_existing_objective(tmp_path):
    memory = ConversationMemory(tmp_path)
    result = memory.prepare_request("under 500 euros", explicit_refinement=True)
    assert result["is_refinement"] is False


def test_private_phone_turns_are_hidden_from_shared_tv(tmp_path):
    memory = ConversationMemory(tmp_path)
    memory.record_turn("user", "My private calendar request", channel="private_phone")
    memory.record_turn("user", "Show the device mesh", channel="shared_tv")
    shared = memory.snapshot(channel="shared_tv")
    private = memory.snapshot(channel="private_phone")
    assert [turn["text"] for turn in shared["recent_turns"]] == ["Show the device mesh"]
    assert any(turn["text"] == "My private calendar request" for turn in private["recent_turns"])
    assert shared["private_turns_hidden"] is True


def test_agent_follow_up_rejects_background_tv_dialogue():
    assert VoiceControlService._plausible_agent_follow_up("mid range and near the centre") is True
    assert VoiceControlService._plausible_agent_follow_up("wait a second i will get ready there is loads of stuff to do") is False
    assert VoiceControlService._plausible_agent_follow_up("welcome to the channel thanks for watching") is False
    assert VoiceControlService._plausible_agent_follow_up("okay") is False
