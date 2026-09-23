from pathlib import Path

APP_JS = Path("desktop/mac/src/app.js").read_text(encoding="utf-8")


def function_block(name):
    start = APP_JS.index(f"function {name}")
    next_fn = APP_JS.find("\nfunction ", start + 1)
    if next_fn == -1:
        return APP_JS[start:]
    return APP_JS[start:next_fn]


def test_phase_l1_registered_business_resolver_reads_business_information_sources():
    block = function_block("getAionRegisteredBusinessIdentity")

    assert "state?.approvedSmallBusinessFoundation" in block
    assert "state?.businessContextFoundation" in block
    assert "state?.smallBusinessFoundationDraft" in block
    assert "desktopStore?.state?.approvedSmallBusinessFoundation" in block
    assert "desktopStore?.state?.businessContextFoundation" in block
    assert "desktopStore?.state?.smallBusinessFoundationDraft" in block
    assert '"aion.approvedSmallBusinessFoundation"' in block
    assert '"aion.businessContextFoundation"' in block
    assert '"aion.smallBusinessFoundationDraft"' in block
    assert '"aion.businessFoundation"' in block
    assert '"aion.businessProfile"' in block


def test_phase_l1_no_hard_coded_home_fixed_runtime_identity_fallback():
    resolver_block = function_block("getAionRegisteredBusinessIdentity")
    container_block = function_block("getAionWorkflowBusinessContainerId")
    header_block = function_block("getAionWorkflowCanvasHeaderBusinessLabel")

    combined = "\n".join([resolver_block, container_block, header_block])

    assert '"Home Fixed"' not in combined
    assert '"home_fixed"' not in combined
    assert "'Home Fixed'" not in combined
    assert "'home_fixed'" not in combined


def test_phase_l1_costa_only_allowed_as_stale_rejection_or_cleanup_needle():
    allowed_blocks = [
        function_block("isAionLegacyDemoBusinessIdentity"),
    ]

    allowed_text = "\n".join(allowed_blocks)

    costa_lines = []
    for i, line in enumerate(APP_JS.splitlines(), 1):
        lower = line.lower()
        if (
            "costa-conexion" in lower
            or "costa_conexion" in lower
            or "costaconexion" in lower
            or "costa connection" in lower
            or "costa conextion" in lower
        ):
            costa_lines.append((i, line))

    assert costa_lines, "Expected stale Costa rejection needles to exist."

    for _, line in costa_lines:
        if line in allowed_text:
            continue

        # Late stale cleanup list is allowed.
        if "staleNeedles" in APP_JS[max(0, APP_JS.find(line) - 300):APP_JS.find(line) + 300]:
            continue

        # Documentation comment explaining stale rejection is allowed.
        if "Stale demo graph identities" in line:
            continue

        if "staleBusinessEndpointPattern" in line:
            continue
        if "\\/api\\/aion\\/business" in line and "costa" in line.lower():
            continue
        if "AION BUSINESS ENDPOINT FETCH GUARD" in line:
            continue
        raise AssertionError(f"Unexpected runtime Costa reference: {line}")


def test_phase_l1_registered_business_neutral_fallback_only_when_missing():
    resolver_block = function_block("getAionRegisteredBusinessIdentity")
    container_block = function_block("getAionWorkflowBusinessContainerId")
    header_block = function_block("getAionWorkflowCanvasHeaderBusinessLabel")

    assert '"business_not_registered"' in resolver_block
    assert '"Business not registered"' in resolver_block
    assert '"business_not_registered"' in container_block
    assert '"Business not registered"' in header_block


def test_phase_l1_goal_loop_still_uses_existing_canvas_and_pilot():
    c1_block = APP_JS[
        APP_JS.index("/* AION GOAL LOOP CANVAS PHASE B1"):
        APP_JS.index("/* END AION GOAL LOOP CANVAS PHASE B1 */")
    ]

    assert "workflow_canvas_mount_hint" in c1_block
    assert "existing_workflow_canvas" in c1_block
    assert "window.__aionWorkflowGraph" in c1_block
    assert "window.__aionWorkflowMainGraph" in c1_block

    forbidden = c1_block.lower()
    assert "new aionpilot" not in forbidden
    assert "renderaiongoalloopcanvas(" not in forbidden
    assert "data-aion-goal-loop-canvas-root" not in forbidden
