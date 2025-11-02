# backend/tests/test_no_top_level_photonlang.py
import subprocess, sys
def test_no_top_level_photonlang():
    cmd = ["git","--no-pager","grep","-nE",r'(^|[^.])\b(import|from)\s+photonlang\b',"--",".",":(exclude)backend/modules/photonlang/**"]
    out = subprocess.run(cmd, capture_output=True, text=True).stdout.strip()
    assert out == "", f"Stray 'photonlang' imports found:\n{out}"