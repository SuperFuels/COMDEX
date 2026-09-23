from pathlib import Path

TEXT = Path("desktop/mac/src/app.js").read_text(encoding="utf-8")


def test_phase25k_only_sitewide_file_cabinet_nav_button_remains():
    assert 'data-aion-sitewide-file-cabinet-tab="true"' in TEXT
    assert 'data-tab="file_cabinet"' in TEXT
    assert '["file_cabinet", "Files", "▤"]' not in TEXT


def test_phase25k_sitewide_file_cabinet_mounts_on_canvas_too():
    assert '<div data-aion-sitewide-file-cabinet-mount="true">${renderAionWorkflowFileCabinetDrawer()}</div>' in TEXT
    assert 'state.activeTab === "operations_flow"\n        ? ""\n        : `<div data-aion-sitewide-file-cabinet-mount="true">${renderAionWorkflowFileCabinetDrawer()}</div>`' not in TEXT


def test_phase25k_canvas_no_longer_mounts_second_file_cabinet_drawer():
    assert TEXT.count('${renderAionWorkflowFileCabinetDrawer()}') == 1


def test_phase25k_file_cabinet_still_reuses_business_container_pointer_contract():
    assert "AION_FILE_CABINET_STORAGE_KEY" in TEXT
    assert "aion.workflow_file_cabinet.v1" in TEXT
    assert 'type: "business_container_artifact"' in TEXT
    assert 'source_of_truth: "business_container"' in TEXT
