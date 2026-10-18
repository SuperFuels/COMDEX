from pathlib import Path
import ast
import re


GATEWAY_MODULES = [
    "backend/modules/aion_gateway/public_intent_gateway.py",
    "backend/modules/aion_gateway/public_widget_request_mapping.py",
    "backend/modules/aion_gateway/public_embed_guard_envelope.py",
    "backend/modules/aion_gateway/public_embed_human_review_handoff.py",
    "backend/modules/aion_gateway/fulfilment_job.py",
    "backend/modules/aion_gateway/fulfilment_job_core.py",
    "backend/modules/aion_gateway/machine_cart.py",
    "backend/modules/aion_gateway/a2a_job_trace.py",
    "backend/modules/aion_gateway/a2a_job_evidence_settlement.py",
    "backend/modules/aion_gateway/a2a_handshake_preview.py",
    "backend/modules/aion_gateway/agent_channels.py",
    "backend/modules/aion_gateway/exceptions.py",
    "backend/modules/aion_gateway/home_fixed_vertical.py",
]


FORBIDDEN_LIVE_BOOKING_TERMS = [
    "create_booking(",
    "create_live_booking(",
    "book_job(",
    "confirm_booking(",
    "dispatch_job(",
    "execute_live_job(",
    "start_live_job(",
    "run_goal_engine(",
    "execute_goal_engine(",
]


REQUIRED_FALSE_FLAGS = [
    "would_create_booking",
    "would_create_live_job",
    "would_execute_goal_engine",
    "human_review_required",
]


def _text(path: str) -> str:
    return Path(path).read_text(encoding="utf-8")


def test_phase13_no_booking_gateway_modules_exist():
    missing = [path for path in GATEWAY_MODULES if not Path(path).exists()]
    assert missing == []


def test_phase13_no_booking_modules_do_not_call_live_booking_functions():
    for path in GATEWAY_MODULES:
        text = _text(path).lower()
        for term in FORBIDDEN_LIVE_BOOKING_TERMS:
            assert term not in text, f"{term} found in {path}"


def test_phase13_no_booking_modules_keep_booking_flags_false_or_preview_only():
    combined = "\n".join(_text(path) for path in GATEWAY_MODULES)

    for term in REQUIRED_FALSE_FLAGS:
        assert term in combined

    required_false_pairs = [
        "would_create_booking\": False",
        "would_create_live_job\": False",
        "would_execute_goal_engine\": False",
        "human_review_required\": True",
    ]

    assert any(pair in combined for pair in [
        "would_create_booking\": False",
        "'would_create_booking': False",
        "\"would_create_booking\": false",
    ])

    assert any(pair in combined for pair in [
        "would_create_live_job\": False",
        "'would_create_live_job': False",
        "\"would_create_live_job\": false",
    ])

    assert any(pair in combined for pair in [
        "would_execute_goal_engine\": False",
        "'would_execute_goal_engine': False",
        "\"would_execute_goal_engine\": false",
    ])


def test_phase13_no_booking_public_embed_handoff_blocks_approval_execution():
    text = _text("backend/modules/aion_gateway/public_embed_human_review_handoff.py")

    for term in [
        "approval_can_create_live_job",
        "approval_can_execute_goal_engine",
        "approval_can_move_money",
        "approval_can_send_external_messages",
        "next_step",
        "future_guarded_approval_path",
    ]:
        assert term in text

    for term in [
        "\"approval_can_create_live_job\": False",
        "\"approval_can_execute_goal_engine\": False",
        "\"approval_can_move_money\": False",
        "\"approval_can_send_external_messages\": False",
    ]:
        assert term in text


def test_phase13_no_booking_public_gateway_regression_files_remain_in_focused_suite():
    suite = Path("scripts/run_goal_engine_focused_lock_suite.sh").read_text(encoding="utf-8")

    for path in [
        "backend/tests/workflow_capsules/test_aion_public_intent_gateway_lock.py",
        "backend/tests/workflow_capsules/test_aion_public_widget_request_mapping_lock.py",
        "backend/tests/workflow_capsules/test_aion_public_embed_guard_envelope_lock.py",
        "backend/tests/workflow_capsules/test_aion_public_embed_human_review_handoff_lock.py",
    ]:
        assert path in suite


def test_phase13_no_booking_regression_test_contains_only_existing_modules():
    this_file = Path(__file__)
    text = this_file.read_text(encoding="utf-8")
    match = re.search(r"GATEWAY_MODULES\s*=\s*(\[[\s\S]*?\])", text)
    assert match

    modules = ast.literal_eval(match.group(1))
    missing = [module for module in modules if not Path(module).exists()]
    assert missing == []
