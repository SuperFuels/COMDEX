from pathlib import Path

APP = Path("desktop/mac/src/app.js").read_text()


def _function_block(name: str) -> str:
    marker = f"function {name}"
    start = APP.index(marker)

    # Find the real function body brace, not "{}" inside default parameters.
    paren = APP.index("(", start)
    depth_paren = 0
    body_start_search = None
    for i in range(paren, len(APP)):
        if APP[i] == "(":
            depth_paren += 1
        elif APP[i] == ")":
            depth_paren -= 1
            if depth_paren == 0:
                body_start_search = i
                break

    assert body_start_search is not None
    brace = APP.index("{", body_start_search)

    depth = 0
    in_str = None
    esc = False

    for i in range(brace, len(APP)):
        ch = APP[i]

        if in_str:
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == in_str:
                in_str = None
            continue

        if ch in ("'", '"', "`"):
            in_str = ch
            continue

        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return APP[start:i + 1]

    raise AssertionError(f"could not read function {name}")


def test_phase21y_cockpit_panel_has_no_unreachable_dead_ui_after_return():
    block = _function_block("renderAionPilotCockpitPanel")

    assert "return renderAionPilotSimpleTaskStream(snapshot);" in block
    assert "const planRows" not in block
    assert "Mission composer" not in block
    assert "aion-pilot-cockpit" not in block


def test_phase21y_lrm_card_is_compact_and_hides_technical_detail():
    block = _function_block("renderAionLrmPilotContextReadonlyCard")

    assert "data-aion-phase21y-lrm-compact-card" in block
    assert "Technical LRM proof anchors and replay log" in block
    assert "<details" in block
    assert "No booking, payment, escrow" in block


def test_phase21y_lrm_fetch_does_not_dump_replay_events_into_main_stream():
    block = _function_block("applyAionLrmPilotContextPreviewPayload")

    assert "pilotState.lrm_visible_events = mappedEvents" in block
    assert "...mappedEvents" not in block
    assert "lrm_pilot_context_preview" in block


def test_phase21y_pilot_event_log_is_deduped_and_capped():
    block = _function_block("appendAionPilotStreamEvent")

    assert "dedupe" in block
    assert "maxEvents" in block
    assert ".slice(-maxEvents)" in block


def test_phase21y_approval_does_not_rerun_completed_safe_work_forever():
    block = _function_block("approveAionPilotMissionContract")

    assert "contract_approval_already_completed" in block
    assert "Safe preview already completed" in block
    assert "return;" in block


def test_phase21y_process_log_is_hidden_inside_advanced_drawer():
    block = _function_block("renderAionPilotSimpleTaskStream")

    assert "data-aion-phase21y-process-log-drawer" in block
    assert "data-aion-pilot-process-log-card" in block
    assert "Process log, proof, hashes, paths, lanes and blocked actions" in block
    assert "renderAionPilotAdvancedTechnicalDetails(snapshot)" in block


def test_phase21y_bottom_bar_is_not_debug_labelled():
    assert "[ Bottom Terminal Bar" not in APP
    assert 'content: "Ask Pilot";' in APP
