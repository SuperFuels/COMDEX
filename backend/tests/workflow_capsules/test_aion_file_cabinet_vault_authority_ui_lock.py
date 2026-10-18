from pathlib import Path


APP_JS = Path("desktop/mac/src/app.js").read_text(encoding="utf-8")


def _function_block(name: str, next_name: str) -> str:
    start = APP_JS.index(f"function {name}")
    end = APP_JS.index(f"function {next_name}", start)
    return APP_JS[start:end]


def test_file_cabinet_tree_is_not_persisted_in_browser_storage():
    block = _function_block("saveAionFileCabinetTree", "getAionFileCabinetTree")
    assert "localStorage" not in block
    assert "__aionFileCabinetMemoryTree" in block


def test_legacy_browser_copy_is_one_time_import_then_purged():
    load_block = _function_block("getAionFileCabinetTree", "findAionCabinetNode")
    assert "__aionFileCabinetLegacyImportPending" in load_block
    assert "purgeAionFileCabinetLegacyBrowserStorage" in load_block
    assert "backend-authoritative" in APP_JS

