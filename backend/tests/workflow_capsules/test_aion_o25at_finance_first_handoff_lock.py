import json
import re
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]

APP = ROOT / "desktop/mac/src/app.js"

CONTROLLER = (
    ROOT
    / "desktop/mac/src/"
    / "aion_business_foundation_voice_controller.js"
)


def read_app() -> str:
    return APP.read_text(encoding="utf-8")


def read_controller() -> str:
    return CONTROLLER.read_text(encoding="utf-8")


def schema_block(
    text: str,
    field: str,
) -> str:
    marker = f'field: "{field}"'
    start = text.index(marker)
    left = text.rfind("{", 0, start)
    right = text.index("\n  },", start)
    return text[left:right]


def test_o25at_removes_redundant_guided_questions():
    text = read_controller()

    for field in (
        "desired_outcome",
        "success_measure",
        "department_priorities",
    ):
        block = schema_block(text, field)

        assert re.search(
            r"required:\s*false",
            block,
        )

        assert re.search(
            r"guided:\s*false",
            block,
        )


def test_o25at_completion_is_finance_handoff():
    text = read_controller()

    assert 'reason: "finance_handoff_ready"' in text

    assert (
        'action: "route_finance_live_agent"'
        in text
    )

    assert 'next_department: "finance"' in text
    assert 'next_pilot: "finance_pilot"' in text

    assert (
        "Do you want to review, correct, or "
        "continue deeper discovery?"
    ) not in text


def test_o25at_startup_entry_mode_is_preserved():
    text = read_controller()

    assert (
        "seed.foundation_draft?.entry_mode ||"
        in text
    )

    assert "seed.entry_mode ||" in text


def test_o25at_whole_recording_is_one_answer():
    text = read_app()

    assert "state.session_audio_chunks = [];" in text

    assert (
        "state.session_audio_chunks.push("
        in text
    )

    assert (
        "const completeAnswerBlob = new Blob"
        in text
    )

    assert "recorder.start();" in text
    assert "recorder.start(2500);" not in text


def test_o25at_reuses_existing_finance_route():
    text = read_app()

    assert (
        "function routeFoundationToFinanceO25AJ"
        in text
    )

    assert (
        "routeAionBusinessTwinToFinanceOnceV2()"
        in text
    )

    assert 'setActiveTab("live_agents")' in text


def test_o25at_controller_finishes_with_finance():
    script = f"""
const c = require({json.dumps(str(CONTROLLER))});

const draft = {{}};

for (const field of c.AION_FOUNDATION_SCHEMA) {{
  if (!field.required && !field.guided) continue;

  draft[field.field] =
    field.field === "entry_mode"
      ? "existing_business"
      : "completed test value";
}}

const packet =
  c.buildAionO25BBusinessFoundationDiscoveryPacket({{
    entry_mode: "existing_business",
    foundation_draft: draft,
    business_map: {{
      department_discovery_gaps: [
        "marketing",
        "sales",
        "finance",
        "operations",
        "support"
      ]
    }}
  }});

console.log(JSON.stringify({{
  status: packet.status,
  reason: packet.next_question.reason,
  action: packet.next_question.action,
  next_department:
    packet.next_question.next_department,
  next_pilot:
    packet.next_question.next_pilot,
  entry_mode:
    packet.foundation_draft.entry_mode
}}));
"""

    output = subprocess.check_output(
        ["node", "-e", script],
        text=True,
    )

    payload = json.loads(output)

    assert (
        payload["status"]
        == "foundation_ready_for_finance_handoff"
    )

    assert (
        payload["reason"]
        == "finance_handoff_ready"
    )

    assert (
        payload["action"]
        == "route_finance_live_agent"
    )

    assert payload["next_department"] == "finance"
    assert payload["next_pilot"] == "finance_pilot"

    assert (
        payload["entry_mode"]
        == "existing_business"
    )
