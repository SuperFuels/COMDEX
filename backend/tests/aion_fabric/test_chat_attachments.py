from pathlib import Path

from backend.modules.aion_fabric.chat_attachments import (
    MAX_FOLDER_ITEMS,
    attachment_context_for_model,
    prepare_chat_attachments,
)


def test_text_attachment_is_bounded_and_path_is_not_sent_to_model(tmp_path: Path) -> None:
    source = tmp_path / "brief.txt"
    source.write_text("useful content " * 2000, encoding="utf-8")
    prepared = prepare_chat_attachments([{"path": str(source), "id": "one"}])
    assert prepared[0]["preview"].startswith("useful content")
    assert len(prepared[0]["preview"]) <= 12_000
    model_context = attachment_context_for_model(prepared)
    assert "useful content" in model_context
    assert str(tmp_path) not in model_context


def test_pages_package_is_a_file_and_folder_manifest_is_bounded(tmp_path: Path) -> None:
    pages = tmp_path / "Report.pages"
    pages.mkdir()
    folder = tmp_path / "project"
    folder.mkdir()
    for index in range(MAX_FOLDER_ITEMS + 20):
        (folder / f"item-{index}.txt").write_text(str(index), encoding="utf-8")
    prepared = prepare_chat_attachments([{"path": str(pages)}, {"path": str(folder)}])
    assert prepared[0]["kind"] == "file"
    assert prepared[0]["extension"] == ".pages"
    assert prepared[1]["kind"] == "folder"
    assert len(prepared[1]["manifest"]) == MAX_FOLDER_ITEMS
