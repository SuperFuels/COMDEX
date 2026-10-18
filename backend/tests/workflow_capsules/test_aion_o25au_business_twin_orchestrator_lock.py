import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]

APP = ROOT / "desktop/mac/src/app.js"

INDEX = ROOT / "desktop/mac/src/index.html"

ORCHESTRATOR = (
    ROOT
    / "desktop/mac/src/"
    / "aion_business_twin_orchestrator.js"
)


def read_app() -> str:
    return APP.read_text(encoding="utf-8")


def read_index() -> str:
    return INDEX.read_text(encoding="utf-8")


def read_orchestrator() -> str:
    return ORCHESTRATOR.read_text(
        encoding="utf-8"
    )


def test_o25au_orchestrator_is_loaded_before_app():
    text = read_index()

    controller = text.index(
        "./aion_business_foundation_voice_controller.js"
    )

    orchestrator = text.index(
        "./aion_business_twin_orchestrator.js"
    )

    app = text.index("./app.js")

    assert controller < orchestrator < app


def test_o25au_module_has_business_twin_contract():
    text = read_orchestrator()

    assert (
        "AionBusinessTwinOrchestrator"
        in text
    )

    assert "createProgressionManifest" in text
    assert "prepareFinanceHandoff" in text
    assert "activateFinancePilot" in text
    assert "handleFoundationPacket" in text
    assert "getProgressionManifest" in text


def test_o25au_department_sequence_is_finance_first():
    text = read_orchestrator()

    finance = text.index('"finance"')
    operations = text.index(
        '"operations"',
        finance,
    )
    sales = text.index('"sales"', operations)
    marketing = text.index(
        '"marketing"',
        sales,
    )

    assert finance < operations < sales < marketing


def test_o25au_app_uses_thin_orchestrator_adapter():
    text = read_app()

    start = text.index(
        "function routeFoundationToFinanceO25AJ"
    )

    end = text.index(
        "async function speakNextQuestionFromPacketO25AJ",
        start,
    )

    block = text[start:end]

    assert (
        "window.AionBusinessTwinOrchestrator"
        in block
    )

    assert (
        "orchestrator.handleFoundationPacket"
        in block
    )

    assert (
        "activateFinancePilot:"
        in block
    )

    assert (
        "routeAionBusinessTwinToFinanceOnceV2()"
        in block
    )


def test_o25au_node_execution_builds_manifest_and_routes():
    script = f"""
const orchestrator =
  require({json.dumps(str(ORCHESTRATOR))});

let routeCalls = 0;

const packet = {{
  status:
    "foundation_ready_for_finance_handoff",

  schema_version:
    "aion.business_foundation.test.v1",

  readiness: {{
    readiness_score: 100
  }},

  foundation_draft: {{
    entry_mode: "existing_business",
    business_name: "Test Business"
  }},

  transcript_count: 12,

  next_question: {{
    reason: "finance_handoff_ready",
    action: "route_finance_live_agent",
    next_department: "finance",
    next_pilot: "finance_pilot"
  }}
}};

const routed =
  orchestrator.handleFoundationPacket(
    packet,
    {{
      activateFinancePilot(context) {{
        routeCalls += 1;

        return (
          context.target_department ===
            "finance" &&
          context.target_pilot ===
            "finance_pilot"
        );
      }}
    }}
  );

const manifest =
  orchestrator.getProgressionManifest();

console.log(JSON.stringify({{
  routed,
  routeCalls,
  status: manifest.status,
  currentDepartment:
    manifest.progression.current_department,
  financeStatus:
    manifest.departments.finance.status,
  strategy:
    manifest.progression.strategy,
  previewOnly:
    manifest.governance.preview_only,
  liveAutomation:
    manifest.governance
      .live_automation_enabled
}}));
"""

    output = subprocess.check_output(
        ["node", "-e", script],
        text=True,
    )

    payload = json.loads(output)

    assert payload["routed"] is True
    assert payload["routeCalls"] == 1

    assert (
        payload["status"]
        == "finance_pilot_active"
    )

    assert (
        payload["currentDepartment"]
        == "finance"
    )

    assert payload["financeStatus"] == "active"
    assert payload["strategy"] == "finance_first"
    assert payload["previewOnly"] is True
    assert payload["liveAutomation"] is False


def test_o25au_rejects_incomplete_foundation_packet():
    script = f"""
const orchestrator =
  require({json.dumps(str(ORCHESTRATOR))});

let routeCalls = 0;

const result =
  orchestrator.handleFoundationPacket(
    {{
      status:
        "foundation_discovery_in_progress",

      next_question: {{
        reason:
          "required_foundation_field_missing"
      }}
    }},
    {{
      activateFinancePilot() {{
        routeCalls += 1;
        return true;
      }}
    }}
  );

console.log(JSON.stringify({{
  result,
  routeCalls
}}));
"""

    output = subprocess.check_output(
        ["node", "-e", script],
        text=True,
    )

    payload = json.loads(output)

    assert payload["result"] is False
    assert payload["routeCalls"] == 0
