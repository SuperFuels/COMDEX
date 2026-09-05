from backend.modules.local_node.pilot_authority_policy import PilotAuthorityPolicyStore


def test_authority_defaults_to_asking_for_every_real_action(tmp_path):
    store = PilotAuthorityPolicyStore(str(tmp_path))
    policy = store.get("home-fixed")

    assert policy["rules"]["email_send"]["mode"] == "ask_each_time"
    assert store.evaluate("home-fixed", "email_send")["decision"] == "exact_approval_required"


def test_nonfinancial_standing_authority_can_be_granted_and_revoked(tmp_path):
    store = PilotAuthorityPolicyStore(str(tmp_path))
    store.update("home-fixed", {"email_send": {"mode": "full_access"}}, "owner")
    assert store.evaluate("home-fixed", "email_send")["authorized"] is True

    store.update("home-fixed", {"email_send": {"mode": "blocked", "ask_again": False}}, "owner")
    blocked = store.evaluate("home-fixed", "email_send")
    assert blocked["authorized"] is False
    assert blocked["decision"] == "blocked_by_owner"
    assert blocked["ask_user"] is False


def test_financial_authority_is_always_bounded(tmp_path):
    store = PilotAuthorityPolicyStore(str(tmp_path))
    try:
        store.update("home-fixed", {"payment": {"mode": "full_access"}}, "owner")
        assert False, "financial standing authority must require a limit"
    except ValueError as exc:
        assert str(exc) == "financial_limit_required:payment"

    store.update(
        "home-fixed",
        {"payment": {"mode": "auto_within_limits", "max_amount": 50, "currency": "GBP"}},
        "owner",
    )
    assert store.evaluate("home-fixed", "payment", amount=40, currency="GBP")["authorized"] is True
    assert store.evaluate("home-fixed", "payment", amount=51, currency="GBP")["decision"] == "amount_exceeds_authority"
