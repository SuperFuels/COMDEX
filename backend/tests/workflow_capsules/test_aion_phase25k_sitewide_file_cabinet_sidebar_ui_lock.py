from pathlib import Path

TEXT = Path("desktop/mac/src/app.js").read_text(encoding="utf-8")


def test_phase25k_sitewide_sidebar_has_file_cabinet_button():
    assert 'data-aion-sitewide-file-cabinet-tab="true"' in TEXT
    assert 'data-tab="file_cabinet"' in TEXT
    assert 'data-aion-sidebar-label="Files"' in TEXT
    assert 'file_cabinet: "≡"' in TEXT


def test_phase25k_sitewide_sidebar_mounts_file_cabinet_drawer_outside_canvas():
    assert 'data-aion-sitewide-file-cabinet-mount="true"' in TEXT
    assert "renderAionWorkflowFileCabinetDrawer()" in TEXT
    assert 'state.activeTab === "operations_flow"' in TEXT


def test_phase25k_sitewide_file_cabinet_reuses_existing_workflow_cabinet_contract():
    assert "AION_FILE_CABINET_STORAGE_KEY" in TEXT
    assert "aion.workflow_file_cabinet.v1" in TEXT
    assert "aion:workflow-file-cabinet:force-save" in TEXT
    assert "business_container" in TEXT


def test_phase25k_folder_delete_button_no_longer_renders_broken_x_angle():
    assert 'data-aion-cabinet-delete-name="${escapeHtml(node.name)}">×<`' not in TEXT
    assert 'data-aion-cabinet-delete-name="${escapeHtml(node.name)}">×</button>`' in TEXT
