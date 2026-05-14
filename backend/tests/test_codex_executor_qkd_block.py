import pytest
from backend.modules.codex.codex_executor import CodexExecutor
from backend.modules.glyphwave.qkd.qkd_policy_enforcer import QKDPolicyViolationError


def test_codex_executor_qkd_block(monkeypatch):
    executor = CodexExecutor()

    # Context requires QKD
    context = {
        "glyph": "∑",
        "source": "test",
        "qkd_policy": {
            "require_qkd": True
        },
        "sender_id": "agent.alice",
        "recipient_id": "agent.bob"
    }

    # Monkeypatch GKeyStore to return None (simulate missing GKey)
    from backend.modules.glyphwave.qkd_handshake import GKeyStore
    monkeypatch.setattr(GKeyStore, "get_key_pair", staticmethod(lambda s, r: None))
    monkeypatch.setattr(GKeyStore, "detect_tampering", staticmethod(lambda s, r: False))

    # Execute and expect QKD block
    with pytest.raises(QKDPolicyViolationError):
        executor.execute_instruction_tree({"op": "collapse"}, context=context)