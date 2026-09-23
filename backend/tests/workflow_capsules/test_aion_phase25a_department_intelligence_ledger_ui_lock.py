from pathlib import Path

APP_JS = Path("desktop/mac/src/app.js")


def read_app():
    return APP_JS.read_text(encoding="utf-8")


def phase25a_block():
    text = read_app()
    start = text.index("/* PHASE 25A LOCK: Department Intelligence Ledger + Boardroom sync */")
    end = text.index("/* END PHASE 25A LOCK: Department Intelligence Ledger + Boardroom sync */")
    return text[start:end]


def test_phase25a_department_intelligence_helpers_exist():
    text = read_app()

    assert "AION_DEPARTMENT_INTELLIGENCE_STORAGE_KEY" in text
    assert '"aion.departmentIntelligence"' in text
    assert "function getAionDepartmentIntelligence(" in text
    assert "function saveAionDepartmentIntelligence(" in text
    assert "function updateAionDepartmentIntelligence(" in text
    assert "function seedAionDepartmentIntelligenceFromBusinessFoundation(" in text
    assert "function getAionBoardroomAssessmentCoverage(" in text


def test_phase25a_department_keys_are_locked():
    block = phase25a_block()

    for key in ["marketing", "sales", "finance", "operations", "support"]:
        assert f'"{key}"' in block

    assert "central" not in block.lower()
    assert "builder" not in block.lower()


def test_phase25a_business_foundation_seeds_department_ledger():
    text = read_app()

    assert "seedAionDepartmentIntelligenceFromBusinessFoundation(foundation)" in text
    assert "state.approvedSmallBusinessFoundation = foundation" in text
    assert "state.businessContextFoundation = foundation" in text
    assert "window.localStorage?.setItem(\"aion.businessContextFoundation\"" in text


def test_phase25a_boardroom_flat_view_reads_department_intelligence():
    text = read_app()

    assert "function renderBoardroomDepartmentIntelligencePanel()" in text
    assert "data-aion-department-intelligence-boardroom=\"true\"" in text
    assert "renderBoardroomDepartmentIntelligencePanel()" in text
    assert "renderAionBusinessContextMiniCard(\"boardroom\")" in text


def test_phase25a_spatial_boardroom_reads_department_intelligence():
    text = read_app()

    assert "function renderBoardroomSpatialDepartmentIntelligencePanel()" in text
    assert "data-aion-spatial-department-intelligence=\"true\"" in text
    assert "renderBoardroomSpatialDepartmentIntelligencePanel()" in text
    assert "renderBoardroomSpatialView(snapshot)" in text


def test_phase25a_exports_safe_debug_helpers():
    block = phase25a_block()

    assert "window.getAionDepartmentIntelligence" in block
    assert "window.saveAionDepartmentIntelligence" in block
    assert "window.updateAionDepartmentIntelligence" in block
    assert "window.getAionBoardroomAssessmentCoverage" in block


def test_phase25a_no_live_external_execution_added():
    block = phase25a_block().lower()

    forbidden = [
        "sendemail(",
        "send_email(",
        "publishad(",
        "chargecard(",
        "createbooking(",
        "live_send_enabled: true",
        "external_writes_enabled",
    ]

    for token in forbidden:
        assert token not in block
