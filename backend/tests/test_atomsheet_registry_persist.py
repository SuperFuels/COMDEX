import os
import json
import tempfile
from backend.modules.atomsheets.registry import AtomSheetRegistry

def test_atomsheet_registry_persist_roundtrip(tmp_path):
    # temp registry file
    reg_path = tmp_path / "atomsheet_registry.json"
    reg = AtomSheetRegistry(path=str(reg_path), autoload=False)

    # make two fake sheet files
    s1 = tmp_path / "a.sqs.json"
    s2 = tmp_path / "b.sqs.json"
    s1.write_text(json.dumps({"id": "A", "title": "A", "cells": []}))
    s2.write_text(json.dumps({"id": "B", "title": "B", "cells": []}))

    sid1 = reg.register(str(s1), qfc_id="QFC_A")
    sid2 = reg.register(str(s2))
    assert sid1 in reg.list_sheets()
    assert sid2 in reg.list_sheets()
    assert reg.get_qfc_sheet("QFC_A") == os.path.abspath(str(s1))

    # new instance auto-loads
    reg2 = AtomSheetRegistry(path=str(reg_path), autoload=True)
    assert sid1 in reg2.list_sheets()
    assert reg2.get_qfc_sheet("QFC_A") == os.path.abspath(str(s1))

    # forget and unlink behaviors
    assert reg2.unlink("QFC_A") is True
    assert reg2.get_qfc_sheet("QFC_A") is None
    assert reg2.forget(sid1) is True
    assert sid1 not in reg2.list_sheets()

    # clearing removes everything
    reg2.clear()
    assert len(reg2.list_sheets()) == 0
    assert len(reg2.list_links()) == 0