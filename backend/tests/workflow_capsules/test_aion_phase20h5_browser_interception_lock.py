import pytest

from backend.services.aion_mission_mode.browser_interception_rules import (
    create_interception_policy,
    evaluate_dom_mutation,
    evaluate_download,
    evaluate_iframe_or_script,
    evaluate_navigation,
    evaluate_network_request,
    evaluate_popup,
    summarize_interceptions,
)


def _policy(**kwargs):
    base = dict(
        mission_id="mission_001",
        mission_run_id="run_001",
        business_id="business_001",
        provider="vercel",
        browser_worker_id="browser_001",
        browser_session_hash="sha256:session",
        allowed_domains=["https://vercel.com"],
        allowed_iframe_domains=["https://vercel.com"],
        allowed_script_domains=["https://vercel.com"],
    )
    base.update(kwargs)
    return create_interception_policy(**base)


def test_phase20h5_policy_hash_is_deterministic() -> None:
    assert _policy()["policy_hash"] == _policy()["policy_hash"]


def test_phase20h5_safe_get_request_allowed() -> None:
    result = evaluate_network_request(
        policy=_policy(),
        request_url="https://vercel.com/dashboard",
        method="GET",
    )
    assert result["allowed"] is True


def test_phase20h5_off_domain_network_request_blocked() -> None:
    result = evaluate_network_request(
        policy=_policy(),
        request_url="https://evil.example.com",
        method="GET",
    )
    assert result["allowed"] is False
    assert "network_request_outside_allowed_domains" in result["reasons"]


def test_phase20h5_mutating_post_blocked_without_policy_and_approval() -> None:
    result = evaluate_network_request(
        policy=_policy(),
        request_url="https://vercel.com/api/deploy",
        method="POST",
        request_payload_hash="sha256:payload",
    )
    assert result["allowed"] is False
    assert "mutating_http_method_blocked" in result["reasons"]
    assert "missing_approval_hash_for_mutating_request" in result["reasons"]


def test_phase20h5_mutating_post_allowed_with_policy_and_approval() -> None:
    result = evaluate_network_request(
        policy=_policy(allow_mutating_methods=True),
        request_url="https://vercel.com/api/deploy",
        method="POST",
        request_payload_hash="sha256:payload",
        approval_hash="sha256:approval",
    )
    assert result["allowed"] is True


def test_phase20h5_unknown_http_method_blocked() -> None:
    result = evaluate_network_request(
        policy=_policy(),
        request_url="https://vercel.com/api",
        method="TRACE",
    )
    assert result["allowed"] is False
    assert "unknown_http_method_blocked" in result["reasons"]


def test_phase20h5_navigation_allowed_inside_domain() -> None:
    result = evaluate_navigation(
        policy=_policy(),
        target_url="https://vercel.com/projects",
    )
    assert result["allowed"] is True


def test_phase20h5_navigation_redirect_chain_off_domain_blocked() -> None:
    result = evaluate_navigation(
        policy=_policy(),
        target_url="https://vercel.com/projects",
        redirect_chain=["https://vercel.com/a", "https://evil.example.com/b"],
    )
    assert result["allowed"] is False
    assert "redirect_chain_outside_allowed_domains" in result["reasons"]


def test_phase20h5_safe_dom_mutation_allowed() -> None:
    result = evaluate_dom_mutation(
        policy=_policy(),
        mutation_type="fill_input_staged",
        selector="#project-name",
        staged_payload_hash="sha256:payload",
    )
    assert result["allowed"] is True


def test_phase20h5_dangerous_dom_mutation_blocked_even_with_approval_in_h5() -> None:
    result = evaluate_dom_mutation(
        policy=_policy(),
        mutation_type="click_submit",
        selector="button[type=submit]",
        staged_payload_hash="sha256:payload",
        approval_hash="sha256:approval",
    )
    assert result["allowed"] is False
    assert "dangerous_dom_mutation_blocked" in result["reasons"]


def test_phase20h5_unknown_dom_mutation_blocked() -> None:
    result = evaluate_dom_mutation(
        policy=_policy(),
        mutation_type="unknown_dom_write",
        selector="#x",
    )
    assert result["allowed"] is False
    assert "unknown_dom_mutation_blocked" in result["reasons"]


def test_phase20h5_popup_blocked_by_default() -> None:
    result = evaluate_popup(
        policy=_policy(),
        popup_url="https://vercel.com/oauth",
    )
    assert result["allowed"] is False
    assert "popup_blocked_by_policy" in result["reasons"]


def test_phase20h5_popup_allowed_when_policy_allows_and_domain_matches() -> None:
    result = evaluate_popup(
        policy=_policy(allow_popups=True),
        popup_url="https://vercel.com/oauth",
    )
    assert result["allowed"] is True


def test_phase20h5_download_blocked_by_default() -> None:
    result = evaluate_download(
        policy=_policy(),
        download_url="https://vercel.com/report.pdf",
        file_name="report.pdf",
    )
    assert result["allowed"] is False
    assert "download_blocked_by_policy" in result["reasons"]


def test_phase20h5_download_allowed_when_policy_allows_and_domain_matches() -> None:
    result = evaluate_download(
        policy=_policy(allow_downloads=True),
        download_url="https://vercel.com/report.pdf",
        file_name="report.pdf",
    )
    assert result["allowed"] is True


def test_phase20h5_iframe_allowed_only_when_whitelisted() -> None:
    allowed = evaluate_iframe_or_script(
        policy=_policy(),
        event_type="iframe",
        resource_url="https://vercel.com/embed",
    )
    blocked = evaluate_iframe_or_script(
        policy=_policy(),
        event_type="iframe",
        resource_url="https://evil.example.com/embed",
    )
    assert allowed["allowed"] is True
    assert blocked["allowed"] is False
    assert "iframe_resource_outside_allowed_domains" in blocked["reasons"]


def test_phase20h5_script_allowed_only_when_whitelisted() -> None:
    allowed = evaluate_iframe_or_script(
        policy=_policy(),
        event_type="script",
        resource_url="https://vercel.com/app.js",
    )
    blocked = evaluate_iframe_or_script(
        policy=_policy(),
        event_type="script",
        resource_url="https://evil.example.com/app.js",
    )
    assert allowed["allowed"] is True
    assert blocked["allowed"] is False
    assert "script_resource_outside_allowed_domains" in blocked["reasons"]


def test_phase20h5_unsupported_resource_event_rejected() -> None:
    with pytest.raises(ValueError):
        evaluate_iframe_or_script(
            policy=_policy(),
            event_type="video",
            resource_url="https://vercel.com/video",
        )


def test_phase20h5_interception_hash_is_deterministic() -> None:
    first = evaluate_network_request(
        policy=_policy(),
        request_url="https://vercel.com/dashboard",
        method="GET",
    )
    second = evaluate_network_request(
        policy=_policy(),
        request_url="https://vercel.com/dashboard",
        method="GET",
    )
    assert first["interception_hash"] == second["interception_hash"]


def test_phase20h5_summary_marks_blocked_for_safety_when_any_blocked() -> None:
    ok = evaluate_network_request(
        policy=_policy(),
        request_url="https://vercel.com/dashboard",
        method="GET",
    )
    bad = evaluate_network_request(
        policy=_policy(),
        request_url="https://evil.example.com",
        method="GET",
    )
    summary = summarize_interceptions(
        mission_id="mission_001",
        mission_run_id="run_001",
        browser_worker_id="browser_001",
        interceptions=[ok, bad],
    )
    assert summary["allowed_count"] == 1
    assert summary["blocked_count"] == 1
    assert summary["runtime_state"] == "blocked_for_safety"
    assert "network_request_outside_allowed_domains" in summary["blocked_reasons"]


def test_phase20h5_summary_hash_is_deterministic() -> None:
    item = evaluate_network_request(
        policy=_policy(),
        request_url="https://vercel.com/dashboard",
        method="GET",
    )
    first = summarize_interceptions(
        mission_id="mission_001",
        mission_run_id="run_001",
        browser_worker_id="browser_001",
        interceptions=[item],
    )
    second = summarize_interceptions(
        mission_id="mission_001",
        mission_run_id="run_001",
        browser_worker_id="browser_001",
        interceptions=[item],
    )
    assert first["summary_hash"] == second["summary_hash"]
