import json
from pathlib import Path
import backend.modules.hexcore.autonomous_upstream_change_scientist as s

def test_integrated_upstream_scientist_creates_two_useful_projects(tmp_path:Path,monkeypatch)->None:
    ledger=tmp_path/'ledger.jsonl'; rows=[]
    for cycle,(py,node) in enumerate((('a','x'),('b','y')),1):
        rows.append({'cycle':cycle,'observed_at':str(cycle),'outcome_sha256':str(cycle),'outcomes':{
            'cpython':{'family':'public_source_control','authority':'https://github.com/python/cpython.git','revision':py},
            'node':{'family':'public_source_control','authority':'https://github.com/nodejs/node.git','revision':node}}})
    ledger.write_text('\n'.join(json.dumps(r) for r in rows))
    monkeypatch.setattr(s,'_compare',lambda t:{'passed':True,'response_sha256':t['after'],'total_commits':1,'commits':[{'sha':t['after'],'message':'change AbortSignal localcontext'}],'files':[{'filename':'x.py','status':'modified','additions':1,'deletions':1,'patch':'localcontext AbortSignal'}]})
    monkeypatch.setattr(s,'_scan',lambda root,concepts:{'concepts':concepts,'hits':[],'hit_count':0,'scan_sha256':'scan'})
    monkeypatch.setattr(s,'_probe',lambda source,concepts:{'passed':True,'probe':source,'observable':'ok'})
    result=s.run_once(repo_root=tmp_path,ledger_path=ledger,state_path=tmp_path/'state.json',output_root=tmp_path/'out',result_path=tmp_path/'result.json')
    assert result['passed'] and result['gate']['cross_ecosystem_transfer']==1 and result['gate']['owner_useful_artifacts']==2
    again=s.run_once(repo_root=tmp_path,ledger_path=ledger,state_path=tmp_path/'state.json',output_root=tmp_path/'out',result_path=tmp_path/'result.json')
    assert again['new_projects']==[] and len(again['investigations'])==2
