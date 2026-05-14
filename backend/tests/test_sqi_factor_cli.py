import json
import subprocess
import sys
from pathlib import Path


def run_cli(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [
            sys.executable,
            "backend/modules/sqi/factor/sqi_factor_cli.py",
            *args,
        ],
        check=True,
        text=True,
        capture_output=True,
    )


def test_cli_factor_json_no_trace_no_dashboard():
    proc = run_cli(str(10007 * 10009), "--json", "--no-trace", "--no-dashboard")
    data = json.loads(proc.stdout)
    assert data["mode"] == "factor"
    assert data["factor"] in {10007, 10009}
    assert data["factor"] * data["cofactor"] == 10007 * 10009
    assert data["trace_path"] is None
    assert data["dashboard_path"] is None


def test_cli_benchmark_json():
    proc = run_cli(str(1000003 * 1009), "--benchmark", "--json")
    data = json.loads(proc.stdout)
    assert data["mode"] == "benchmark"
    assert data["result"]["sqi"]["factor"] in {1000003, 1009}


def test_cli_output_file(tmp_path):
    out = tmp_path / "factor.json"
    run_cli(str(8051), "--json", "--out", str(out), "--no-trace", "--no-dashboard")
    assert out.exists()
    data = json.loads(out.read_text())
    assert data["factor"] in {83, 97}
