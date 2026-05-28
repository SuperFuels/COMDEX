from pathlib import Path


PUBLIC_ROUTE_FILES = [
    "backend/modules/aion_gateway/public_intent_gateway.py",
    "backend/modules/aion_gateway/public_widget_request_mapping.py",
    "backend/modules/aion_gateway/public_embed_guard_envelope.py",
    "backend/modules/aion_gateway/public_embed_human_review_handoff.py",
]

API_ENTRY_FILES = [
    "backend/main.py",
    "backend/modules/aion_gateway/a2a_api.py",
]


def _text(path: str) -> str:
    return Path(path).read_text(encoding="utf-8")


def test_phase13_no_public_route_regression_files_exist():
    for path in PUBLIC_ROUTE_FILES:
        assert Path(path).exists(), path


def test_phase13_public_gateway_modules_are_preview_builders_not_routes():
    for path in PUBLIC_ROUTE_FILES:
        text = _text(path).lower()

        for forbidden in [
            "@app.post",
            "@app.put",
            "@app.patch",
            "@router.post",
            "@router.put",
            "@router.patch",
            "fastapi(",
            "apirouter(",
            "flask(",
            "django.urls",
            "add_api_route",
            "route(",
        ]:
            assert forbidden not in text, f"{forbidden} found in {path}"

        assert "preview" in text


def test_phase13_no_public_write_endpoint_for_aion_gateway_intent_is_mounted():
    existing = [path for path in API_ENTRY_FILES if Path(path).exists()]
    combined = "\n".join(_text(path).lower() for path in existing)

    forbidden_routes = [
        "/api/aion-gateway/intent",
        "/api/aion_gateway/intent",
        "/aion-gateway/intent",
        "/aion_gateway/intent",
        "/api/public/aion-gateway",
        "/api/public/aion_gateway",
        "/api/embed/aion",
        "/api/widget/aion",
    ]

    for route in forbidden_routes:
        assert route not in combined


def test_phase13_public_embed_guard_states_no_public_route_mounted():
    text = _text("backend/modules/aion_gateway/public_embed_guard_envelope.py")

    for term in [
        '"public_route_mounted": False',
        '"unauthenticated_public_write_route_exposed": False',
        '"preview_only": True',
        '"human_review_required": True',
    ]:
        assert term in text


def test_phase13_public_handoff_states_no_public_write_route():
    text = _text("backend/modules/aion_gateway/public_embed_human_review_handoff.py")

    for term in [
        '"unauthenticated_public_write_route_exposed": False',
        '"preview_only": True',
        '"human_review_required": True',
    ]:
        assert term in text


def test_phase13_public_intent_gateway_is_preview_only():
    text = _text("backend/modules/aion_gateway/public_intent_gateway.py")

    for term in [
        "preview",
        "human_review_required",
        "would_create_booking",
        "would_create_live_job",
        "would_execute_goal_engine",
    ]:
        assert term in text

    # This module may contain preview/safety flags such as
    # "would_send_external_message": false. The route regression only blocks
    # live route mounting and live side-effect execution calls.
    for forbidden in [
        "@router.post",
        "@app.post",
        "send_external(",
        "send_external_message(",
        "create_live_job(",
        "execute_goal_engine(",
    ]:
        assert forbidden not in text.lower()


def test_phase13_no_public_route_regression_is_focused_suite_member():
    suite = _text("scripts/run_goal_engine_focused_lock_suite.sh")

    assert "backend/tests/workflow_capsules/test_aion_phase13_no_public_route_regression_lock.py" in suite
    assert "backend/tests/workflow_capsules/test_aion_phase13_no_public_route_regression_lock_doc.py" in suite
