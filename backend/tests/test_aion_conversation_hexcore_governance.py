from __future__ import annotations

from types import SimpleNamespace

import backend.modules.aion_conversation.conversation_orchestrator as orchestrator_module
from backend.modules.aion_conversation.conversation_orchestrator import ConversationOrchestrator


class _FakeGovernedRuntime:
    def __init__(self):
        self.begin_calls = []
        self.complete_calls = []

    def begin_turn(self, **kwargs):
        self.begin_calls.append(kwargs)
        return SimpleNamespace(
            governance_id="gov-test-1",
            authority={"allow_learn": False, "deny_reason": "TEST_DENY"},
            recalled_knowledge=[
                {
                    "source": "cee_lex_memory",
                    "answer": "remembered fact",
                    "confidence": 0.9,
                }
            ],
            pattern_results=[],
            tessaris_rules=[],
            goals=list(kwargs["request_metadata"].get("goals") or []),
            memories=list(kwargs["request_metadata"].get("memories") or []),
            reasoning_providers=["test_provider"],
            cognitive_foundation={"role": "replaceable_representation_provider"},
        )

    def complete_turn(self, **kwargs):
        self.complete_calls.append(kwargs)
        return {
            "schema_version": "aion.hexcore.governance_result.v1",
            "governance_id": "gov-test-1",
            "authority": {"allow_learn": False, "deny_reason": "TEST_DENY"},
            "learning_committed": False,
            "learning_reason": "TEST_DENY",
        }


def test_active_conversation_route_passes_through_hexcore_governance(monkeypatch):
    monkeypatch.setenv("AION_DIALOGUE_STATE_PERSIST", "0")
    governed = _FakeGovernedRuntime()
    orch = ConversationOrchestrator(governed_runtime=governed)

    out = orch.handle_turn(
        session_id="hexcore-integration-test",
        user_text="show forex curriculum",
        include_metadata=True,
        include_debug=True,
        request_metadata={"reasoning_providers": ["local_gemma"]},
    )

    assert out["ok"] is True
    assert len(governed.begin_calls) == 1
    assert len(governed.complete_calls) == 1
    assert governed.complete_calls[0]["response_text"] == out["response"]
    hexcore = out["metadata"]["orchestrator"]["hexcore"]
    assert hexcore["governance_id"] == "gov-test-1"
    assert hexcore["learning_committed"] is False


def test_governed_route_disables_legacy_composer_teaching(monkeypatch):
    monkeypatch.setenv("AION_DIALOGUE_STATE_PERSIST", "0")
    captured = {}

    def fake_composer(request):
        captured["apply_teaching"] = request.apply_teaching
        return {
            "ok": True,
            "origin": "test_composer",
            "response": "candidate answer",
            "confidence": 0.5,
            "metadata": {},
        }

    monkeypatch.setattr(orchestrator_module, "_run_composer_response", fake_composer)
    governed = _FakeGovernedRuntime()
    orch = ConversationOrchestrator(governed_runtime=governed)
    out = orch.handle_turn(
        session_id="hexcore-teaching-test",
        user_text="Explain a novel technical concept.",
        apply_teaching=True,
        include_metadata=True,
        request_metadata={
            "learning_outcome": {
                "verified": True,
                "verifier": "test",
                "verification_method": "executable",
                "answer": "verified answer",
            }
        },
    )

    assert captured["apply_teaching"] is False
    assert out["metadata"]["hexcore_governed_teaching_requested"] is True
    assert governed.complete_calls[0]["apply_teaching"] is True
