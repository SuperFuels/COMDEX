from pathlib import Path

APP_JS = Path("desktop/mac/src/app.js").read_text(encoding="utf-8")


def block():
    assert "BEGIN AION O13H1 LINKED DEPARTMENT DOCUMENT BOX REROUTE" in APP_JS
    return APP_JS.split("BEGIN AION O13H1 LINKED DEPARTMENT DOCUMENT BOX REROUTE", 1)[1].split(
        "END AION O13H1 LINKED DEPARTMENT DOCUMENT BOX REROUTE", 1
    )[0]


def test_o13h1_installed():
    b = block()
    assert "Linked department document box reroute installed" in b
    assert "aionRerouteLinkedDepartmentDocumentBoxO13H1" in b
    assert "aionOpenLinkedDepartmentChooserFromDocumentBoxO13H1" in b


def test_o13h1_detects_old_white_box_content():
    b = block()
    assert "linked department sheets" in b
    assert "department goal sheets are linked records" in b
    assert "department_goal_links" in b
    assert "linked_department_sheets" in b


def test_o13h1_removes_old_document_boxes_only_for_linked_departments():
    b = block()
    assert "removeLinkedDepartmentDocumentBoxesO13H1" in b
    assert "isLinkedDepartmentTextO13H1(el.textContent)" in b
    assert "looksLikeRightDocumentBox" in b


def test_o13h1_routes_to_existing_department_chooser():
    b = block()
    assert "aionRenderLinkedDepartmentSheetChooserO13H" in b
    assert "aionRenderDepartmentChooserO13B" in b
    assert "routed_to: \"department_goal_sheet_chooser\"" in b


def test_o13h1_uses_limited_mutation_observer():
    b = block()
    assert "MutationObserver" in b
    assert "Limited observer only watches for the old Linked Department document box" in b
    assert "rerouteIfLinkedDepartmentDocumentBoxO13H1" in b
