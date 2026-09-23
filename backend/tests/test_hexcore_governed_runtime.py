from __future__ import annotations

import json

from backend.modules.hexcore.governed_runtime import (
    AppendOnlyOutcomeLedger,
    HexCoreGovernedRuntime,
)


def _runtime(tmp_path, *, allow_learn=True, recall=None, writes=None):
    writes = writes if writes is not None else []

    def authority(_goal):
        return {
            "allow_learn": allow_learn,
            "deny_reason": None if allow_learn else "LOW_STABILITY",
            "S": 0.9,
            "H": 0.1,
            "source": "test_cau",
        }

    def writer(prompt, answer, resonance, metadata):
        writes.append(
            {
                "prompt": prompt,
                "answer": answer,
                "resonance": dict(resonance),
                "metadata": dict(metadata),
            }
        )
        return True

    return HexCoreGovernedRuntime(
        authority_provider=authority,
        recall_provider=lambda _prompt: dict(recall or {}),
        memory_writer=writer,
        outcome_ledger=AppendOnlyOutcomeLedger(tmp_path / "governed_turns.jsonl"),
        foundation_root=tmp_path / "tpu",
        learning_state_path=tmp_path / "persistent_learning.json",
    )


def test_recall_is_exposed_but_provider_response_is_not_automatically_learned(tmp_path):
    writes = []
    runtime = _runtime(
        tmp_path,
        recall={
            "prompt": "capital",
            "answer": "Paris",
            "confidence": 0.91,
            "resonance": {"SQI": 0.8},
        },
        writes=writes,
    )
    context = runtime.begin_turn(
        turn_id="turn-1",
        session_id="session-1",
        user_text="What is the capital?",
    )

    assert context.recalled_knowledge[0]["answer"] == "Paris"
    result = runtime.complete_turn(
        context=context,
        response_text="Paris",
        confidence=0.9,
        mode="answer",
        apply_teaching=False,
    )

    assert result["learning_committed"] is False
    assert result["learning_reason"] == "TEACHING_NOT_REQUESTED"
    assert writes == []


def test_verified_outcome_and_positive_cau_can_commit_memory(tmp_path):
    writes = []
    runtime = _runtime(tmp_path, writes=writes)
    context = runtime.begin_turn(
        turn_id="turn-2",
        session_id="session-1",
        user_text="What is the verified value?",
    )
    result = runtime.complete_turn(
        context=context,
        response_text="The value is 42.",
        confidence=0.8,
        mode="answer",
        apply_teaching=True,
        request_metadata={
            "learning_outcome": {
                "verified": True,
                "verifier": "test_executor",
                "verification_method": "executable",
                "answer": "42",
                "resonance": {"SQI": 0.95},
            }
        },
    )

    assert result["learning_committed"] is True
    assert len(writes) == 1
    assert writes[0]["answer"] == "42"
    assert writes[0]["metadata"]["verified"] is True


def test_cau_denial_is_fail_closed_for_learning(tmp_path):
    writes = []
    runtime = _runtime(tmp_path, allow_learn=False, writes=writes)
    context = runtime.begin_turn(
        turn_id="turn-3",
        session_id="session-1",
        user_text="Remember this verified result",
    )
    result = runtime.complete_turn(
        context=context,
        response_text="Acknowledged.",
        confidence=0.8,
        mode="answer",
        apply_teaching=True,
        request_metadata={
            "learning_outcome": {
                "verified": True,
                "verifier": "human",
                "verification_method": "human_authority",
                "answer": "verified result",
            }
        },
    )

    assert result["learning_committed"] is False
    assert result["learning_reason"] == "LOW_STABILITY"
    assert writes == []


def test_missing_authority_contract_denies_learning(tmp_path):
    runtime = HexCoreGovernedRuntime(
        authority_provider=lambda _goal: {},
        recall_provider=lambda _prompt: {},
        memory_writer=lambda *_args: True,
        outcome_ledger=AppendOnlyOutcomeLedger(tmp_path / "outcomes.jsonl"),
        foundation_root=tmp_path / "tpu",
        learning_state_path=tmp_path / "persistent_learning.json",
    )
    context = runtime.begin_turn(
        turn_id="turn-4",
        session_id="session-1",
        user_text="test",
    )

    assert context.authority["allow_learn"] is False
    assert context.authority["deny_reason"] == "CAU_UNAVAILABLE"


def test_soul_laws_veto_action_and_outcome_ledger_is_hash_chained_record(tmp_path):
    runtime = _runtime(tmp_path)
    veto = runtime.evaluate_action("apply mutation to rewrite code")
    safe = runtime.evaluate_action("summarize the supplied evidence")

    assert veto["allowed"] is False
    assert veto["reason"] == "SOUL_LAW_VETO"
    assert safe["allowed"] is True

    context = runtime.begin_turn(
        turn_id="turn-5",
        session_id="session-1",
        user_text="summarize",
    )
    result = runtime.complete_turn(
        context=context,
        response_text="summary",
        confidence=0.7,
        mode="answer",
        apply_teaching=False,
    )
    row = json.loads((tmp_path / "governed_turns.jsonl").read_text().splitlines()[-1])
    assert row["schema_version"] == "aion.hexcore.governed_turn_outcome.v1"
    assert row["record_hash"] == result["outcome_record_hash"]
    assert "previous_record_hash" in row


def test_learning_is_not_written_when_audit_ledger_is_unavailable(tmp_path):
    writes = []

    class FailingLedger(AppendOnlyOutcomeLedger):
        def append(self, record):
            raise OSError("ledger unavailable")

    runtime = HexCoreGovernedRuntime(
        authority_provider=lambda _goal: {"allow_learn": True},
        recall_provider=lambda _prompt: {},
        memory_writer=lambda *args: writes.append(args) or True,
        outcome_ledger=FailingLedger(tmp_path / "unavailable.jsonl"),
        foundation_root=tmp_path / "tpu",
        learning_state_path=tmp_path / "persistent_learning.json",
    )
    context = runtime.begin_turn(
        turn_id="turn-6",
        session_id="session-1",
        user_text="remember verified result",
    )

    try:
        runtime.complete_turn(
            context=context,
            response_text="candidate",
            confidence=0.7,
            mode="answer",
            apply_teaching=True,
            request_metadata={
                "learning_outcome": {
                    "verified": True,
                    "verifier": "executor",
                    "verification_method": "executable",
                    "answer": "verified result",
                }
            },
        )
    except OSError:
        pass
    else:
        raise AssertionError("audit failure must fail the governed learning transaction")

    assert writes == []


def test_legacy_cee_learning_gates_now_fail_closed(monkeypatch):
    from backend.modules.aion_cognition import cee_exercise_playback as playback
    from backend.modules.aion_cognition import cee_lex_memory as lex_memory

    monkeypatch.setattr(playback, "_cau_state", None)
    assert playback._cau_status()["allow_learn"] is False

    monkeypatch.setattr(lex_memory, "_get_cau_state", lambda goal=None: {})
    allowed, _state = lex_memory._cau_allow()
    assert allowed is False
