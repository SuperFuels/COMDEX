import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
INDEX = ROOT / "desktop/mac/src/index.html"
CLIENT = ROOT / "desktop/mac/src/aion_department_pilot_backend.js"
APP = ROOT / "desktop/mac/src/app.js"


def test_backend_bridge_is_modular_and_loaded_before_legacy_app():
    index = INDEX.read_text(encoding="utf-8")
    assert index.index("./aion_department_pilot_runtime.js") < index.index(
        "./aion_department_pilot_backend.js"
    ) < index.index("./app.js")
    assert "aion_department_pilot_backend" not in APP.read_text(encoding="utf-8")
    bridge = CLIENT.read_text(encoding="utf-8")
    assert "approved Boardroom queue" in bridge
    assert "approved work monitor" in bridge
    assert "data-aion-canonical-pilot-queue" in bridge
    assert "data-aion-department-design-gate" in bridge
    assert "Its purpose, workflows, capabilities and permissions will be agreed" in bridge
    assert "data-aion-finance-run-task" in bridge
    assert "Run read-only Finance analysis" in bridge
    assert "Result ready for Boardroom" in bridge
    assert "/execute-read-only" in bridge
    assert "data-aion-finance-conversation" in bridge
    assert "grounded conversation" in bridge
    assert "/finance/conversation/session" in bridge
    assert "/finance/conversation/turn" in bridge
    assert "handleFinanceConversationSubmit" in bridge
    assert "stopImmediatePropagation" in bridge


def test_backend_bridge_rejects_preview_and_uses_one_step_boardroom_handoff():
    script = f"""
const calls = [];
const listeners = {{}};
global.window = {{
  fetch: async (url, options) => {{
    calls.push({{ url, body: JSON.parse(options.body) }});
    return {{ ok: true, json: async () => ({{ ok: true }}) }};
  }},
  addEventListener: (name, handler) => {{ listeners[name] = handler; }},
  dispatchEvent: () => {{}},
}};
global.CustomEvent = class CustomEvent {{ constructor(name, options) {{ this.type = name; this.detail = options.detail; }} }};
require({json.dumps(str(CLIENT))});
const canonical = {{
  schema_version: 'aion.department_pilot.boardroom_assignment_package.v1',
  package_id: 'finance-1', workspace_id: 'home-fixed', business_id: 'home-fixed',
  department_id: 'finance', status: 'draft'
}};
(async () => {{
  await window.AionDepartmentPilotBackend.approveAndRoute(canonical, {{
    approval_id: 'approval-1', approved_by: 'kevin', approved_at: '2026-07-16T22:31:00Z'
  }});
  let previewRejected = false;
  try {{ await window.AionDepartmentPilotBackend.routeApprovedPackage({{ ...canonical, preview_only: true }}); }}
  catch (error) {{ previewRejected = error.message === 'preview_boardroom_package_cannot_be_routed'; }}
  await window.AionDepartmentPilotBackend.approveBoardroomAction({{
    workspace_id: 'home-fixed', business_id: 'home-fixed', department_id: 'finance',
    actions: [{{ action_id: 'cash', department_id: 'finance' }}]
  }});
  console.log(JSON.stringify({{
    calls,
    previewRejected,
    listenerInstalled: Boolean(listeners['aion:canonical-boardroom-package-approved']),
    actionListenerInstalled: Boolean(listeners['aion:canonical-boardroom-action-approved'])
  }}));
}})();
"""
    payload = json.loads(subprocess.check_output(["node", "-e", script], text=True))
    assert payload["previewRejected"] is True
    assert payload["listenerInstalled"] is True
    assert payload["actionListenerInstalled"] is True
    assert payload["calls"][0]["url"].endswith(
        "/api/aion/business/department-pilots/approve-and-route"
    )
    assert payload["calls"][0]["body"]["routed_by"] == "central_pilot"
    assert payload["calls"][1]["url"].endswith(
        "/api/aion/business/department-pilots/approve-boardroom-action"
    )
