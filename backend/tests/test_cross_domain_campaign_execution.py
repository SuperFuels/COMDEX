from __future__ import annotations

import json
from pathlib import Path

from backend.modules.hexcore.cross_domain_campaign_execution import (
    FLASK_URL, PYTHON_DATA_MODEL_URL, USGS_URL, WORLD_BANK_URL, run,
)


ROOT=Path(__file__).resolve().parents[2]


def _fixtures(url:str)->bytes:
    if url==WORLD_BANK_URL:
        rows=[]; value=100.0
        for year in range(1960,2026):
            value*=1.02 if year<2000 else 1.05
            rows.append({"date":str(year),"value":value})
        return json.dumps([{},list(reversed(rows))]).encode()
    if url==USGS_URL:
        return json.dumps({"features":[{"properties":{"time":i,"mag":2+(i%5)*.1},"geometry":{"coordinates":[0,0,5+i%3]}} for i in range(100)]}).encode()
    if url==FLASK_URL:
        return json.dumps({"info":{"version":"3.1.3","requires_python":">=3.9"}}).encode()
    if url==PYTHON_DATA_MODEL_URL:
        return b"<p>Dictionaries preserve insertion order, meaning that keys will be produced in the same order.</p>"
    raise AssertionError(url)


def test_six_campaigns_execute_and_delay_retention(tmp_path:Path)->None:
    result=run(repo_root=ROOT,state_path=tmp_path/"state.json",result_path=tmp_path/"result.json",
               fetcher=_fixtures,delay_seconds=3600,now_epoch=1000,
               output_root=tmp_path/"projects",record_competency=False)
    assert result["passed"] is True
    assert result["gate"]["campaigns_passed"]==6
    assert result["gate"]["distinct_authorities"]>=5
    assert result["gate"]["source_disjoint_projects"]==6
    assert result["gate"]["retention_awarded_early"]==0
    assert result["gate"]["live_repository_writes"]==0


def test_delayed_reconstruction_uses_fresh_outcome_and_retained_capsule(tmp_path:Path)->None:
    state=tmp_path/"state.json"; result_path=tmp_path/"result.json"
    first=run(repo_root=ROOT,state_path=state,result_path=result_path,fetcher=_fixtures,delay_seconds=10,now_epoch=1000,
              output_root=tmp_path/"projects",record_competency=False)
    assert first["gate"]["delayed_reconstructions"]==0
    later=run(repo_root=ROOT,state_path=state,result_path=result_path,fetcher=_fixtures,delay_seconds=10,now_epoch=1011,
              output_root=tmp_path/"projects",record_competency=False)
    assert later["gate"]["delayed_reconstructions"]==6
    assert all(row["retention_credit"]==1 for row in json.loads(state.read_text())["later_reconstructions"])
