import re
from pathlib import Path
import json
import subprocess


APP = Path("desktop/mac/src/app.js")
CONTROLLER = Path(
    "desktop/mac/src/aion_business_foundation_voice_controller.js"
)


def read_app() -> str:
    return APP.read_text(encoding="utf-8")


def read_controller() -> str:
    return CONTROLLER.read_text(encoding="utf-8")


def test_o25as_aion_introduces_itself_and_explains_the_purpose():
    text = read_app()

    assert "Hi, I’m AION, your AI business partner." in text
    assert "sales, marketing, finance, operations and customer support" in text
    assert "identify what could be automated" in text
    assert "your AI Boardroom" in text
    assert "you can edit the answer" in text


def test_o25as_business_structure_is_the_second_question():
    text = read_controller()

    contact = text.index('id: "contact_name"')
    structure = text.index('id: "business_structure"')
    role = text.index('id: "owner_role"')

    assert contact < structure < role
    assert "just you, you with occasional help" in text


def test_o25as_entry_mode_is_not_asked_during_guided_flow():
    text = read_controller()

    entry_start = text.index('field: "entry_mode"')
    entry_block = text[entry_start:entry_start + 420]

    assert "guided: false" in entry_block
    assert "selectedEntryMode" in read_app()
    assert "existing_business" in read_app()
    assert "new_business_idea" in read_app()


def test_o25as_adds_business_maturity_and_measurement_fields():
    text = read_controller()

    required_fields = [
        "business_stage",
        "revenue_status",
        "annual_turnover_band",
        "current_challenges",
        "near_term_priorities",
        "success_measure",
        "team_structure",
    ]

    for field in required_fields:
        assert f'field: "{field}"' in text


def test_o25as_optional_questions_can_be_deferred():
    text = read_controller()

    assert "userDeferredCurrentQuestion" in text
    assert "deferred_by_user" in text
    assert "user_deferred_optional_question" in text
    assert "optional_guided_foundation_field_unanswered" in text


def test_o25as_department_priority_is_not_user_selected():
    text = read_controller()

    marker = 'field: "department_priorities"'
    marker_index = text.index(marker)
    block_start = text.rfind("{", 0, marker_index)
    block_end = text.index("\n  },", marker_index)
    block = text[block_start:block_end]

    assert re.search(
        r"required:\s*false",
        block,
    )

    assert re.search(
        r"guided:\s*false",
        block,
    )

    assert (
        "Which area should AION understand in more detail first"
        not in text
    )

    assert (
        "Which function should AION explore next"
        not in text
    )

    assert 'reason: "finance_handoff_ready"' in text
    assert 'next_department: "finance"' in text
    assert 'next_pilot: "finance_pilot"' in text


def test_o25as_runtime_sequence_skips_seeded_entry_mode():
    script = r'''
const controller = require(
  "./desktop/mac/src/aion_business_foundation_voice_controller.js"
);

let state = controller.createAionBusinessFoundationVoiceDiscoveryState({
  entry_mode: "existing_business",
  foundation_draft: {
    entry_mode: "existing_business"
  }
});

let packet =
  controller.buildAionO25BBusinessFoundationDiscoveryPacket(state);

const sequence = [];

sequence.push(packet.next_question.target_field);

state = controller.applyAionO25BVoiceTurnToFoundationDraft(
  state,
  {
    speaker: "user",
    text: "Kevin",
    target_field: packet.next_question.target_field,
    source: "test"
  }
);

packet =
  controller.buildAionO25BBusinessFoundationDiscoveryPacket(state);

sequence.push(packet.next_question.target_field);

console.log(JSON.stringify({
  sequence,
  entry_mode: packet.foundation_draft.entry_mode
}));
'''

    result = subprocess.run(
        ["node", "-e", script],
        check=True,
        capture_output=True,
        text=True,
    )

    payload = json.loads(result.stdout.strip())

    assert payload["entry_mode"] == "existing_business"
    assert payload["sequence"] == [
        "contact_name",
        "business_structure",
    ]
