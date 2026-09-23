from pathlib import Path


ROOT = Path(".")
SUITE = ROOT / "scripts/run_goal_engine_focused_lock_suite.sh"


PHASE12_MODULES = [
    "backend/modules/aion_gateway/public_intent_gateway.py",
    "backend/modules/aion_gateway/public_widget_request_mapping.py",
    "backend/modules/aion_gateway/public_embed_guard_envelope.py",
    "backend/modules/aion_gateway/public_embed_human_review_handoff.py",
]

PHASE12_FRONTEND_RENDERERS = [
    "renderAionPublicEmbedWidgetShellV0",
    "renderAionPublicEmbedWidgetMappingBridgeV0",
    "buildPublicWidgetMappingPreviewV0",
]

PHASE12_DOCS = [
    "docs/rfc/aion_public_intent_gateway_lock.tex",
    "docs/rfc/aion_public_embed_widget_shell_lock.tex",
    "docs/rfc/aion_public_widget_request_mapping_lock.tex",
    "docs/rfc/aion_public_embed_widget_mapping_bridge_lock.tex",
    "docs/rfc/aion_public_embed_guard_envelope_lock.tex",
    "docs/rfc/aion_public_embed_human_review_handoff_lock.tex",
]

PHASE12_TESTS = [
    "backend/tests/workflow_capsules/test_aion_public_intent_gateway_lock.py",
    "backend/tests/workflow_capsules/test_aion_public_intent_gateway_lock_doc.py",
    "backend/tests/workflow_capsules/test_aion_public_embed_widget_shell_ui_lock.py",
    "backend/tests/workflow_capsules/test_aion_public_embed_widget_shell_lock_doc.py",
    "backend/tests/workflow_capsules/test_aion_public_widget_request_mapping_lock.py",
    "backend/tests/workflow_capsules/test_aion_public_widget_request_mapping_lock_doc.py",
    "backend/tests/workflow_capsules/test_aion_public_embed_widget_mapping_bridge_ui_lock.py",
    "backend/tests/workflow_capsules/test_aion_public_embed_widget_mapping_bridge_lock_doc.py",
    "backend/tests/workflow_capsules/test_aion_public_embed_guard_envelope_lock.py",
    "backend/tests/workflow_capsules/test_aion_public_embed_guard_envelope_lock_doc.py",
    "backend/tests/workflow_capsules/test_aion_public_embed_human_review_handoff_lock.py",
    "backend/tests/workflow_capsules/test_aion_public_embed_human_review_handoff_lock_doc.py",
]


def _text(path: str) -> str:
    return Path(path).read_text(encoding="utf-8")


def test_phase13_public_gateway_modules_exist():
    for path in PHASE12_MODULES:
        assert Path(path).exists(), path


def test_phase13_public_gateway_frontend_renderers_exist():
    app = _text("desktop/mac/src/app.js")
    for renderer in PHASE12_FRONTEND_RENDERERS:
        assert renderer in app


def test_phase13_public_gateway_docs_exist():
    for path in PHASE12_DOCS:
        assert Path(path).exists(), path


def test_phase13_public_gateway_tests_are_in_focused_suite():
    suite = SUITE.read_text(encoding="utf-8")
    for path in PHASE12_TESTS:
        assert path in suite, path


def test_phase13_public_gateway_docs_lock_preview_only_boundary():
    required_terms = [
        "preview-only",
        "human review",
        "create a booking",
        "create a live job",
        "execute the Goal Engine",
        "move money",
        "create a payment",
        "create escrow",
        "release funds",
        "send external messages",
    ]

    combined = "\n".join(_text(path) for path in PHASE12_DOCS)

    for term in required_terms:
        assert term in combined


def test_phase13_public_gateway_does_not_claim_live_public_route():
    combined = "\n".join(_text(path) for path in PHASE12_DOCS)

    forbidden_claims = [
        "public route is mounted",
        "live public route is mounted",
        "unauthenticated public write route is exposed",
        "live job creation is enabled",
        "autonomous booking is enabled",
        "payment movement is enabled",
    ]

    for claim in forbidden_claims:
        assert claim not in combined


def test_phase13_public_gateway_lock_footer_present_in_all_docs():
    for path in PHASE12_DOCS:
        text = _text(path)
        assert "Maintainer: Tessaris AI" in text, path
        assert "Author: Kevin Robinson" in text, path


def test_phase13_public_gateway_dna_switch_index_not_in_focused_suite():
    suite = SUITE.read_text(encoding="utf-8")
    assert "backend/modules/dna_chain/dna_switch_index.json" not in suite
