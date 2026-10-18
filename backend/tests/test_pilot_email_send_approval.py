from types import SimpleNamespace

from backend.modules.local_node.local_node_runtime import LocalNodeRuntime
from backend.modules.local_node.pilot_authority_policy import PilotAuthorityPolicyStore


class MemoryApprovalStore:
    def __init__(self):
        self.items = {}

    def save_approval(self, workspace_id, approval_id, item):
        saved = dict(item)
        self.items[(workspace_id, approval_id)] = saved
        return saved

    def get_approval(self, workspace_id, approval_id):
        item = self.items.get((workspace_id, approval_id))
        return dict(item) if item else None


def build_runtime(tmp_path):
    runtime = LocalNodeRuntime.__new__(LocalNodeRuntime)
    runtime.config = SimpleNamespace(workspace_id="home-fixed")
    runtime.train_task_approval_store = MemoryApprovalStore()
    runtime.pilot_authority_policy = PilotAuthorityPolicyStore(str(tmp_path))
    runtime._append_audit = lambda **kwargs: None
    runtime.get_gmail_connector_health = lambda: {"auth_status": "connected"}
    sent = []

    def fake_send(**message):
        sent.append(message)
        return {"sent": True, "message_id": "gmail-message-1", "thread_id": "gmail-thread-1"}

    runtime._send_gmail_message = fake_send
    return runtime, sent


def test_pilot_email_requires_exact_payload_approval_and_sends_once(tmp_path):
    runtime, sent = build_runtime(tmp_path)
    prepared = runtime.prepare_pilot_email_send(
        to="client@example.com",
        subject="CarbonCore benefits",
        body="A complete retained email draft.",
    )

    assert prepared["ok"] is True
    assert prepared["sent"] is False
    assert sent == []

    rejected = runtime.execute_pilot_email_send(
        approval_id=prepared["approval_id"],
        payload_hash="sha256:wrong",
    )
    assert rejected == {
        "ok": False,
        "reason": "payload_hash_mismatch",
        "sent": False,
        "at": rejected["at"],
    }
    assert sent == []

    completed = runtime.execute_pilot_email_send(
        approval_id=prepared["approval_id"],
        payload_hash=prepared["payload_hash"],
        approval_granted=True,
    )
    assert completed["ok"] is True
    assert completed["sent"] is True
    assert completed["result"]["message_id"] == "gmail-message-1"
    assert len(sent) == 1

    duplicate = runtime.execute_pilot_email_send(
        approval_id=prepared["approval_id"],
        payload_hash=prepared["payload_hash"],
    )
    assert duplicate["ok"] is False
    assert duplicate["reason"] == "already_sent"
    assert len(sent) == 1


def test_pilot_email_stops_when_gmail_is_not_connected(tmp_path):
    runtime, sent = build_runtime(tmp_path)
    prepared = runtime.prepare_pilot_email_send(
        to="client@example.com",
        subject="CarbonCore benefits",
        body="A complete retained email draft.",
    )
    runtime.get_gmail_connector_health = lambda: {"auth_status": "not_connected"}

    result = runtime.execute_pilot_email_send(
        approval_id=prepared["approval_id"],
        payload_hash=prepared["payload_hash"],
        approval_granted=True,
    )

    assert result["ok"] is False
    assert result["reason"] == "gmail_not_connected"
    assert result["sent"] is False
    assert sent == []


def test_pilot_email_never_allow_suppresses_approval_prompt(tmp_path):
    runtime, sent = build_runtime(tmp_path)
    runtime.pilot_authority_policy.update(
        "home-fixed",
        {"email_send": {"mode": "blocked"}},
        "owner",
    )

    prepared = runtime.prepare_pilot_email_send(
        to="client@example.com",
        subject="CarbonCore benefits",
        body="A complete retained email draft.",
    )

    assert prepared["ok"] is False
    assert prepared["reason"] == "blocked_by_owner"
    assert prepared["authority"]["ask_user"] is False
    assert runtime.train_task_approval_store.items == {}
    assert sent == []
