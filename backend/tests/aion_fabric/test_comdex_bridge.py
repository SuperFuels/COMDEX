from backend.modules.aion_fabric.comdex_bridge import ReadOnlyComdexBridge


def test_comdex_bridge_projects_metadata_without_boardroom_content(tmp_path):
    meetings = tmp_path / ".runtime" / "local_node" / "boardroom_meetings"
    meetings.mkdir(parents=True)
    (meetings / "business-one.json").write_text('{"secret":"must not escape"}', encoding="utf-8")
    module = tmp_path / "backend" / "AION" / "agent.py"
    module.parent.mkdir(parents=True)
    module.write_text("# intelligence", encoding="utf-8")

    snapshot = ReadOnlyComdexBridge(tmp_path).snapshot()
    assert snapshot["boardroom_sessions"] == 1
    assert snapshot["boardroom_ids"] == ["business-one"]
    assert snapshot["intelligence_modules_present"] == 1
    assert "secret" not in str(snapshot)
    assert snapshot["content_exposed_to_tv"] is False
