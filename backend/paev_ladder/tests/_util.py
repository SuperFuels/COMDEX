import json
import os
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[2]  # .../backend
RESULTS_DIR = ROOT / "paev_ladder" / "results"

def _strict() -> bool:
    return os.getenv("PAEV_STRICT", "0") == "1"

def load_result(name: str) -> dict:
    """
    Load a result json for a ladder test.

    Resolution order:
      1) env var PAEV_RESULT_<NAME_UPPER>
      2) backend/paev_ladder/results/<name>.json

    DEV mode (PAEV_STRICT!=1):
      - missing file or status=="MISSING_MEASUREMENT" => SKIP
    STRICT mode (PAEV_STRICT=1):
      - missing/incomplete => FAIL
    """
    env_key = f"PAEV_RESULT_{name.upper()}"
    p = os.getenv(env_key)
    if p:
        path = Path(p)
    else:
        path = RESULTS_DIR / f"{name}.json"

    if not path.exists():
        msg = (
            f"Missing results for {name}: expected {path} "
            f"(or set {env_key}=/path/to/{name}.json)"
        )
        if _strict():
            raise FileNotFoundError(msg)
        pytest.skip(msg)

    r = json.loads(path.read_text(encoding="utf-8"))

    if r.get("status") == "MISSING_MEASUREMENT":
        msg = f"{name}: status=MISSING_MEASUREMENT (provide real measurement JSON to run this rung)"
        if _strict():
            pytest.fail(msg)
        pytest.skip(msg)

    return r

def req_keys(r: dict, keys: list[str]) -> None:
    missing = [k for k in keys if k not in r]
    if missing:
        msg = f"Missing required keys: {missing}"
        if _strict():
            pytest.fail(msg)
        pytest.skip(msg)
