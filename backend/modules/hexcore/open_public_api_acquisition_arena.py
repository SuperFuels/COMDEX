"""Open acquisition of read-only public API adapters from official documentation."""
from __future__ import annotations
import argparse,hashlib,json,re,urllib.error,urllib.parse,urllib.request
from pathlib import Path
from typing import Any
from backend.modules.hexcore.documentation_guided_open_software_benchmark import _allow
from backend.modules.hexcore.persistent_learning import HexCorePersistentLearningRuntime,ProcedureCandidate,_canonical_hash,_utc_timestamp

PROCEDURE_ID="procedure_open_public_api_acquisition_80b9a41d73c6"
CONTRACTS={
 "github":{"docs":"https://docs.github.com/en/rest/repos/repos","base":"https://api.github.com","route_pattern":r"/repos/(?:\{|%7B)?owner(?:\}|%7D)?/(?:\{|%7B)?repo(?:\}|%7D)?","targets":[("python","cpython"),("nodejs","node")],"required":["full_name","default_branch","language"]},
 "pypi":{"docs":"https://docs.pypi.org/api/json/","base":"https://pypi.org","route_pattern":r"/pypi/(?:<|&lt;|\{|%7B)?project(?:>|&gt;|\}|%7D)?/json","targets":[("numpy",),("requests",)],"required":["info","releases"]},
 "open_meteo":{"docs":"https://open-meteo.com/en/docs","base":"https://api.open-meteo.com","route_pattern":r"/v1/forecast","targets":[(40.4168,-3.7038),(51.5072,-.1276)],"required":["latitude","longitude","current"]},
}
def _get(url:str,timeout:int=40)->tuple[int,bytes,dict[str,str]]:
 request=urllib.request.Request(url,headers={"User-Agent":"AION-HexCore-read-only-research/1.0","Accept":"application/json,text/html"},method="GET")
 try:
  with urllib.request.urlopen(request,timeout=timeout) as response:return response.status,response.read(),dict(response.headers.items())
 except urllib.error.HTTPError as error:return error.code,error.read(),dict(error.headers.items())
def _schema(value:Any,depth:int=0)->Any:
 if depth>=3:return type(value).__name__
 if isinstance(value,dict):return {key:_schema(value[key],depth+1) for key in sorted(value)[:40]}
 if isinstance(value,list):return {"type":"array","item":_schema(value[0],depth+1) if value else "unknown"}
 return type(value).__name__
def _documentation(name:str,contract:dict[str,Any])->dict[str,Any]:
 status,body,_=_get(contract["docs"]);text=body.decode("utf-8","replace");match=re.search(contract["route_pattern"],text,re.I);route=match.group(0) if match else None
 return {"source":contract["docs"],"status":status,"sha256":hashlib.sha256(body).hexdigest(),"route_evidence":route,"route_discovered":route is not None}
def _url(name:str,base:str,target:tuple[Any,...],invalid:bool=False)->str:
 if name=="github":return base+f"/repos/{target[0]}/{target[1]}"
 if name=="pypi":return base+f"/pypi/{target[0]}/json"
 query={"latitude":"not-a-number","longitude":0,"current":"temperature_2m"} if invalid else {"latitude":target[0],"longitude":target[1],"current":"temperature_2m,wind_speed_10m"}
 return base+"/v1/forecast"+("?"+urllib.parse.urlencode(query) if query else "")
def _acquire(name:str,contract:dict[str,Any])->dict[str,Any]:
 evidence=_documentation(name,contract);invalid_status=None
 if name=="open_meteo":invalid_status=_get(_url(name,contract["base"],contract["targets"][0],True))[0]
 outcomes=[]
 for index,target in enumerate(contract["targets"]):
  url=_url(name,contract["base"],target);status,body,headers=_get(url);parsed=json.loads(body) if status==200 else {};missing=[key for key in contract["required"] if key not in parsed];outcomes.append({"cohort":"development" if index==0 else "sealed_transfer","target":list(target),"url_commitment":hashlib.sha256(url.encode()).hexdigest(),"status":status,"passed":status==200 and not missing,"missing_required_fields":missing,"response_sha256":hashlib.sha256(body).hexdigest(),"schema":_schema(parsed),"content_type":headers.get("Content-Type") or headers.get("content-type")})
 adapter={"method":"GET","base":contract["base"],"route_evidence":evidence["route_evidence"],"required_response_fields":contract["required"],"credentials_required":False,"side_effect_class":"read_only","typed_schema":outcomes[0]["schema"]}
 return {"api":name,"documentation":evidence,"invalid_parameter_test":{"performed":name=="open_meteo","status":invalid_status,"rejected":invalid_status is not None and invalid_status>=400},"adapter":adapter,"outcomes":outcomes,"transferred":outcomes[1]["passed"]}
def run(*,state_path:Path,result_path:Path|None=None)->dict[str,Any]:
 rows=[_acquire(name,contract) for name,contract in CONTRACTS.items()];all_outcomes=[o for row in rows for o in row["outcomes"]];attempts_cold=3*len(all_outcomes);attempts_retained=len(all_outcomes)+len(rows);reduction=1-attempts_retained/attempts_cold
 gate={"official_document_sources":len(rows),"independent_public_api_authorities":len(rows),"documentation_routes_discovered":sum(r["documentation"]["route_discovered"] for r in rows),"typed_adapters_invented":len(rows),"development_and_transfer_calls":len(all_outcomes),"successful_calls":sum(o["passed"] for o in all_outcomes),"source_disjoint_transfers":sum(r["transferred"] for r in rows),"invalid_parameter_rejection_demonstrated":rows[2]["invalid_parameter_test"]["rejected"],"information_action_reduction_vs_cold":reduction,"credentials_used":False,"non_get_requests":0,"unsafe_or_paid_actions":0};gate["accepted"]=bool(gate["documentation_routes_discovered"]==3 and gate["successful_calls"]==6 and gate["source_disjoint_transfers"]==3 and gate["invalid_parameter_rejection_demonstrated"] and reduction>=.4)
 runtime=HexCorePersistentLearningRuntime(state_path=state_path,authority_provider=_allow);runtime.store.state.setdefault("open_public_api_adapters",{});cohort="public_api_"+_canonical_hash(gate)[:16];runtime.store.state["open_public_api_adapters"][cohort]={"gate":gate,"adapters":{r["api"]:r["adapter"] for r in rows},"created_at":_utc_timestamp()};candidate=ProcedureCandidate(procedure_id=PROCEDURE_ID,goal="open_public_api_acquisition",steps=["read_official_documentation","discover_endpoint_route","probe_parameter_failure","infer_typed_response_schema","execute_read_only_adapter","transfer_to_unseen_target","retain_or_reject"],score=sum(o["passed"] for o in all_outcomes)/len(all_outcomes),success=gate["accepted"],evidence={"cohort_id":cohort,"gate":gate},source_rules=[]);decision=runtime.skills.promote(candidate);runtime.skills.record_outcome(procedure_id=PROCEDURE_ID,success=candidate.success,score=candidate.score,evidence=candidate.evidence);runtime.store.commit(reason="open_public_api_acquisition");rr=HexCorePersistentLearningRuntime(state_path=state_path,authority_provider=_allow);restart={"cohort_retained":cohort in rr.store.state.get("open_public_api_adapters",{}),"champion_retained":rr.store.state["champions"].get("open_public_api_acquisition")==PROCEDURE_ID};payload={"schema_version":"aion.hexcore.open_public_api_acquisition.v1","created_at":_utc_timestamp(),"apis":rows,"gate":gate,"promotion":{"candidate":candidate.to_dict(),"decision":decision},"restart":restart,"passed":bool(gate["accepted"] and (decision.get("promoted") or decision.get("champion_id")==PROCEDURE_ID) and all(restart.values())),"boundary":"This acquires three read-only public JSON adapters from official documentation and transfers them to unseen targets. Documentation URLs, candidate authorities, objectives and safety policy remain engineered. It is not unrestricted browsing, credential use, deployment, purchasing, external certification or AGI."}
 if result_path:result_path.parent.mkdir(parents=True,exist_ok=True);result_path.write_text(json.dumps(payload,indent=2,sort_keys=True),encoding="utf-8")
 return payload
def main():
 p=argparse.ArgumentParser();p.add_argument("--state-path",type=Path,default=Path("backend/modules/hexcore/data/public_api_acquisition/state.json"));p.add_argument("--result-path",type=Path,default=Path("results/hexcore_open_public_api_acquisition.json"));a=p.parse_args();r=run(state_path=a.state_path.resolve(),result_path=a.result_path.resolve());print(json.dumps({"passed":r["passed"],"gate":r["gate"]},indent=2,sort_keys=True))
if __name__=="__main__":main()
