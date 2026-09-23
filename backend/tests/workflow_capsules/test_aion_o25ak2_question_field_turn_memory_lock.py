import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
CONTROLLER = ROOT / "desktop/mac/src/aion_business_foundation_voice_controller.js"
APP = ROOT / "desktop/mac/src/app.js"


def test_first_question_is_short_and_not_generic_intro():
    text = APP.read_text(encoding="utf-8")
    assert 'const AION_O25AJ_OPENING = "Hi, I’m AION, your AI business partner.' in text
    assert "Before we start, what should I call you?" in text
    assert "you can edit the answer before your Business Foundation is finalised" in text
    assert "currentState?.next_question?.target_field" in text


def test_controller_maps_short_answers_to_current_question_then_advances():
    script = f"""
const c = require({json.dumps(str(CONTROLLER))});
let state = c.createAionBusinessFoundationVoiceDiscoveryState({{}});
let packet = c.buildAionO25BBusinessFoundationDiscoveryPacket(state);
state.next_question = packet.next_question;

state = c.applyAionO25BVoiceTurnToFoundationDraft(state, {{
  speaker: "user",
  text: "Kevin",
  source: "typed_test",
  target_field: state.next_question.target_field || state.next_question.field
}});
packet = c.buildAionO25BBusinessFoundationDiscoveryPacket(state);

state = c.applyAionO25BVoiceTurnToFoundationDraft(packet, {{
  speaker: "user",
  text: "Just me",
  source: "typed_test",
  target_field: packet.next_question.target_field || packet.next_question.field
}});
packet = c.buildAionO25BBusinessFoundationDiscoveryPacket(state);

state = c.applyAionO25BVoiceTurnToFoundationDraft(packet, {{
  speaker: "user",
  text: "Founder",
  source: "typed_test",
  target_field: packet.next_question.target_field || packet.next_question.field
}});
packet = c.buildAionO25BBusinessFoundationDiscoveryPacket(state);

console.log(JSON.stringify({{
  contact_name: packet.foundation_draft.contact_name,
  business_structure: packet.foundation_draft.business_structure,
  owner_role: packet.foundation_draft.owner_role,
  next_field: packet.next_question.target_field || packet.next_question.field,
  last_mapped: packet.last_turn.mapped_field,
  transcript_count: packet.transcript_count
}}));
"""
    out = subprocess.check_output(["node", "-e", script], text=True)
    payload = json.loads(out)
    assert payload["contact_name"] == "Kevin"
    assert payload["business_structure"] == "Just me"
    assert payload["owner_role"] == "Founder"
    assert payload["last_mapped"] == "owner_role"
    assert payload["next_field"] == "business_name"
    assert payload["transcript_count"] == 3
