import os, json, subprocess, sys
from pathlib import Path

def test_turn_log_schema_v1(tmp_path: Path):
    env = os.environ.copy()
    env["DATA_ROOT"] = str(tmp_path / "data")
    env["PYTHONPATH"] = str(Path.cwd())
    env["AION_COMMENTARY"] = "1"
    env["AION_VERBOSITY"] = "terse"

    # run 1 exercise to produce a turn log line
    subprocess.check_call(
        [sys.executable, "backend/modules/aion_cognition/cee_exercise_playback.py", "--feed", "self_train", "--n", "1"],
        env=env,
    )

    p = tmp_path / "data" / "telemetry" / "turn_log.jsonl"
    assert p.exists()
    line = p.read_text(encoding="utf-8").splitlines()[-1]
    rec = json.loads(line)

    assert rec.get("schema") == "AION.TurnLog.v1"
    for k in (
        "ts","session","mode","type","prompt","intent","coherence","correct",
        "allow_learn","deny_reason","adr_active","cooldown_s","S","H","Phi","response_time_ms"
    ):
        assert k in rec