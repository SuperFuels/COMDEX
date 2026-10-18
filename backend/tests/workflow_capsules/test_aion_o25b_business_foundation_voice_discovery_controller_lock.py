from pathlib import Path
import json
import subprocess

ROOT = Path(__file__).resolve().parents[3]
CONTROLLER = ROOT / "desktop/mac/src/aion_business_foundation_voice_controller.js"


def read_controller():
    return CONTROLLER.read_text(encoding="utf-8")


def test_o25b_controller_exists_and_is_clean_module():
    text = read_controller()

    assert "AION O25B" in text
    assert "AION_BUSINESS_FOUNDATION_VOICE_CONTROLLER_VERSION" in text
    assert "createAionBusinessFoundationVoiceDiscoveryState" in text
    assert "applyAionO25BVoiceTurnToFoundationDraft" in text
    assert "buildAionO25BBusinessFoundationDiscoveryPacket" in text
    assert "module.exports" in text

    # O25B must be a clean controller, not another late app.js patch.
    assert CONTROLLER.name == "aion_business_foundation_voice_controller.js"


def test_o25b_is_schema_driven_not_demo_business_hardcoded():
    text = read_controller().lower()

    forbidden = [
        "home" + " fixed",
        "home_" + "fixed",
        "costa" + "-conexion",
        "costa" + "_conexion",
        "per" + "gola",
        "car" + "port",
        "roof" + "ing",
        "plumb" + "er",
        "electric" + "ian",
        "trade" + "smen",
        "almer" + "ía",
        "mur" + "cia",
    ]

    for token in forbidden:
        assert token not in text

    assert "hardcoded_business_answers: false" in text
    assert "hardcoded_vertical: false" in text
    assert "hardcoded_demo_business: false" in text


def test_o25b_starting_questions_are_limited_and_generic():
    text = read_controller()

    assert "existing business" in text or "entry_mode" in text
    assert "Before we start, what should I call you?" in text
    assert "contact_name" in text
    assert "owner_role" in text
    assert (
        "AION can help with growth, sales, marketing, finance, operations"
        not in text
    )
    assert 'reason: "finance_handoff_ready"' in text
    assert 'next_department: "finance"' in text
    assert 'next_pilot: "finance_pilot"' in text
    assert (
        "Which area would be most useful to focus on first?"
        not in text
    )

    # Starting questions are allowed. Long fixed business questionnaire flows are not.
    assert "AION_FOUNDATION_DISCOVERY_STARTERS" in text
    assert "AION_FOUNDATION_SCHEMA" in text
    assert "schema_driven_questions: true" in text


def test_o25b_node_execution_proves_foundation_packet():
    script = f"""
const c = require({json.dumps(str(CONTROLLER))});
let state = c.createAionBusinessFoundationVoiceDiscoveryState();
state = c.applyAionO25BVoiceTurnToFoundationDraft(state, {{
  speaker: "user",
  text: "I have an existing business and I want to map the business, improve decisions and automate internal work."
}});
state = c.applyAionO25BVoiceTurnToFoundationDraft(state, {{
  speaker: "user",
  text: "The business mainly provides services and works with customers through appointments and projects."
}});
const packet = c.buildAionO25BBusinessFoundationDiscoveryPacket(state);
console.log(JSON.stringify({{
  version: c.AION_BUSINESS_FOUNDATION_VOICE_CONTROLLER_VERSION,
  entry_mode: state.foundation_draft.entry_mode,
  desired_outcome: state.foundation_draft.desired_outcome,
  business_model: state.foundation_draft.business_model,
  transcript_count: state.transcript.length,
  next_question: packet.next_question,
  safety: packet.safety,
  readiness: packet.readiness
}}, null, 2));
"""
    result = subprocess.run(
        ["node", "-e", script],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
    )
    payload = json.loads(result.stdout)

    assert payload["version"] == "aion.o25b.business_foundation_voice_discovery_controller.v0.1"
    assert payload["entry_mode"] == "existing_business"
    assert payload["desired_outcome"]
    assert payload["business_model"] == "service"
    assert payload["transcript_count"] == 2
    assert payload["next_question"]["schema_driven"] is True
    assert payload["safety"]["preview_only"] is True
    assert payload["safety"]["external_actions_allowed"] is False
    assert payload["safety"]["live_execution_allowed"] is False
    assert payload["readiness"]["readiness_score"] >= 20


def test_o25b_syntax_check_clean():
    subprocess.run(["node", "--check", str(CONTROLLER)], cwd=ROOT, check=True)
