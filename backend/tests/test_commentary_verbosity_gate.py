import os
import subprocess
import sys

def run(env):
    e = os.environ.copy()
    e.update(env)
    p = subprocess.run(
        [
            sys.executable,
            "backend/modules/aion_cognition/cee_exercise_playback.py",
            "--feed", "self_train",
            "--n", "1",
        ],
        env=e,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    return p.stdout

def test_commentary_suppressed_when_verbosity_off(tmp_path):
    out = run({
        "PYTHONPATH": str(tmp_path.parent),
        "AION_COMMENTARY": "1",
        "AION_VERBOSITY": "off",
    })
    assert "[AION]" not in out

def test_commentary_emitted_when_terse(tmp_path):
    out = run({
        "PYTHONPATH": str(tmp_path.parent),
        "AION_COMMENTARY": "1",
        "AION_VERBOSITY": "terse",
    })
    assert "[AION]" in out