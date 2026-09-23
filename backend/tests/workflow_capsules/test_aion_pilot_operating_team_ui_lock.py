from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
INDEX = (ROOT / "desktop/mac/src/index.html").read_text(encoding="utf-8")
UI = (ROOT / "desktop/mac/src/pilot_operating_team_ui.js").read_text(encoding="utf-8")
APP = (ROOT / "desktop/mac/src/app.js").read_text(encoding="utf-8")
MAIN = (ROOT / "desktop/mac/electron/main.js").read_text(encoding="utf-8")
PRELOAD = (ROOT / "desktop/mac/electron/preload.js").read_text(encoding="utf-8")
BROWSER = (ROOT / "desktop/mac/electron/isolated-browser.html").read_text(encoding="utf-8")
CSS = (ROOT / "desktop/mac/src/pilot_operating_team.css").read_text(encoding="utf-8")


def test_operating_team_assets_are_loaded_after_the_existing_pilot_surfaces():
    assert '<link rel="stylesheet" href="./pilot_operating_team.css" />' in INDEX
    assert '<script src="./pilot_operating_team_ui.js"></script>' in INDEX
    assert INDEX.index("aion_department_pilot_runtime.js") < INDEX.index("pilot_operating_team_ui.js")


def test_train_agent_exposes_native_team_teaching_and_mission_controls():
    assert "data-aion-pilot-operating-team" in UI
    assert "pilot-team-overlay" in UI
    assert "data-pilot-team-header-toggle" in UI
    assert "data-pilot-team-header-toggle-host" in APP
    assert "document.body.append(next)" in UI
    assert "data-pilot-teach-toggle" in UI
    assert "data-pilot-validate-skill" in UI
    assert "data-pilot-create-mission" in UI
    assert "data-pilot-mission-command" in UI
    assert "pause" in UI
    assert "redirect" in UI
    assert "stop" in UI
    assert "resume" in UI
    assert 'data-aion-pilot-teaching="${escapeHtml(departmentId)}"' in UI
    assert "data-pilot-teach-department" not in UI
    assert "missions/launch" in UI
    assert "Plan and launch mission" in UI
    assert "data-pilot-add-skill-node" in UI
    assert "Taught process library" in UI
    assert "data-pilot-edit-skill" in UI
    assert "data-pilot-save-skill-edit" in UI
    assert "data-pilot-delete-skill" in UI
    assert "Delete “${skill.name}” from the taught-process library?" in UI
    assert "__aionPilotWorkflowSkillModules" in UI
    assert 'group: "Taught Processes"' in APP
    assert 'action_id: "pilot.demonstrated_skill.execute"' in UI
    assert "grid-template-columns: repeat(4, minmax(0, 1fr))" in CSS


def test_department_pages_expose_live_view_and_control_transfer():
    assert "[data-aion-shared-department-pilot]" in UI
    assert "data-pilot-open-computer" in UI
    assert "data-pilot-control" in UI
    assert "Return control to Pilot" in UI
    for department in ("finance", "sales", "marketing", "operations", "support", "people", "products_services"):
        assert f'data-aion-shared-department="{department}"' in APP


def test_operating_team_uses_the_canonical_business_workspace_and_live_api_base():
    assert "window.AionBusinessContainerClient?.resolveBusinessId?.()" in UI
    assert "desktopState.workspaceId" in UI
    assert "runtime.loadedWorkspaceId === requestedWorkspaceId" in UI
    assert "desktopState.apiBase" in UI
    assert "Pilot runtime did not respond. Restart Tessaris and try again." in UI


def test_department_computers_use_separate_persistent_browser_partitions():
    assert "isolatedBrowserProfileId" in MAIN
    assert "browser_profile_id" in MAIN
    assert 'webview.setAttribute("partition", "persist:" + browserProfileId)' in BROWSER
    assert "profileChanged" in MAIN
    assert "missionChanged" in MAIN
    assert "No mission assigned. Watch computer shows this isolated workspace; it does not start work." in BROWSER


def test_semantic_replay_is_validation_only_and_live_work_uses_backend_gateway():
    assert 'ipcMain.handle("aion-replay-browser-skill"' in MAIN
    assert "replayBrowserSkill" in PRELOAD
    assert "replaySemanticSteps" in BROWSER
    assert "exact_approval_required" in BROWSER
    assert "live_execution_requires_backend_gateway" in MAIN
    assert 'mode: "dry_run"' in MAIN


def test_train_agent_exposes_governed_routines_and_completion_packs():
    assert "data-aion-pilot-routines" in UI
    assert "data-pilot-create-routine" in UI
    assert "Scheduled and event-driven routines" in UI
    assert "data-pilot-create-workflow-routine" in UI
    assert "data-pilot-workflow-routine-id" in UI
    assert '"minute", "hour", "day", "week"' in UI
    assert "data-pilot-routine-interval-value" in UI
    assert "data-pilot-routine-interval-unit" in UI
    assert "data-pilot-routine-output" in UI
    assert "data-pilot-routine-output-instructions" in UI
    assert "data-pilot-routine-output-destination" in UI
    assert "vault_grants_only" in UI
    assert "Authorised input source" not in UI
    assert "Expected evidence-backed result" not in UI
    assert "Every X minutes" not in UI
    assert "replacePanelWithoutLosingPlace" in UI
    assert 'active.matches("input, textarea, select")' in UI
    assert "next.scrollTop = scrollTop" in UI
    assert 'event.target.setAttribute("value", event.target.value)' in UI
    assert "updateVisibleIntervalUnitLabels" in UI
    assert "data-pilot-test-routine" in UI
    assert "data-pilot-toggle-routine" in UI
    assert "Evidence and completion packs" in UI
    assert "data-aion-pilot-workers" in UI
    assert "data-pilot-register-worker" in UI
    assert "data-pilot-save-template" in UI
    assert "data-pilot-use-template" in UI


def test_model_selection_remains_vault_owned():
    assert "The selected Vault model plans the work" in UI
    assert "OpenBot" not in UI
    assert "grok" not in UI.lower()
