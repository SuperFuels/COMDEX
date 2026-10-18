from __future__ import annotations

from backend.modules.aion_business.api.work_schedule_api import (
    RewriteDescriptionRequest,
    rewrite_quote_description,
    rewrite_quote_email_template,
)


def test_quote_description_rewrite_uses_selected_local_model_and_stays_unsaved(monkeypatch) -> None:
    from backend.services.aion_mission_mode import pilot_local_model_runtime

    monkeypatch.setattr(
        pilot_local_model_runtime,
        "selected_local_runtime_profile_for_workspace",
        lambda _workspace_id: {"max_output_tokens": 320},
    )
    captured: dict = {}

    def run(**kwargs):
        captured.update(kwargs)
        return {"content": "We will prepare and re-render the wall.\n\n• Protect the surrounding area.\n• Apply the new render finish."}

    monkeypatch.setattr(pilot_local_model_runtime, "run_selected_local_chat", run)

    result = rewrite_quote_description(
        "home-fixed",
        RewriteDescriptionRequest(text="rerendr wall and make good"),
    )

    assert result["provider"] == "local_model"
    assert result["editable"] is True
    assert result["saved"] is False
    assert "re-render" in result["description"]
    assert "do not invent" in captured["prompt"].lower()
    assert "Return only the editable rewritten text" in captured["system_prompt"]


def test_quote_email_rewrite_preserves_placeholders_and_stays_unsaved(monkeypatch) -> None:
    from backend.services.aion_mission_mode import pilot_local_model_runtime

    monkeypatch.setattr(
        pilot_local_model_runtime,
        "selected_local_runtime_profile_for_workspace",
        lambda _workspace_id: {"max_output_tokens": 320},
    )
    monkeypatch.setattr(
        pilot_local_model_runtime,
        "run_selected_local_chat",
        lambda **_kwargs: {
            "content": (
                "**Hi {customer_name},\n\nPlease find your quotation {quote_number} attached for review.\n\n"
                "Kind regards,\n{business_name}**"
            )
        },
    )

    result = rewrite_quote_email_template(
        "home-fixed",
        RewriteDescriptionRequest(
            text="hi {customer_name} quote {quote_number} attached thanks {business_name}",
        ),
    )

    assert result["provider"] == "local_model"
    assert result["editable"] is True
    assert result["saved"] is False
    assert "{customer_name}" in result["email_body"]
    assert "{quote_number}" in result["email_body"]
    assert "{business_name}" in result["email_body"]
    assert not result["email_body"].startswith("**")
