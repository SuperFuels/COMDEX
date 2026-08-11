"""Build a provenance-only corpus manifest from HexCore outcome artifacts."""
from __future__ import annotations
import argparse,hashlib,json,re
from pathlib import Path
from typing import Any

def _sha(path:Path)->str:return hashlib.sha256(path.read_bytes()).hexdigest()
def _family(name:str)->str:
 for family,terms in {"physical":("physical","acoustic","pixel","visual"),"software":("repair","software","repository","adapter","rust","polyglot"),"knowledge":("semantic","relation","document","evidence"),"causal":("causal","world","operator","multivariate"),"project":("project","continual","curriculum"),"tool":("photon","tool","api","program")}.items():
  if any(term in name for term in terms):return family
 return "general"
def _procedure(payload:dict[str,Any])->str|None:
 promotion=payload.get("promotion",{});candidate=promotion.get("candidate",{}) if isinstance(promotion,dict) else {};return candidate.get("procedure_id") or payload.get("procedure_id")
def _classification(payload:dict[str,Any])->str:
 if "protocol" in str(payload.get("schema_version","")).lower() or "AWAITING" in json.dumps(payload.get("gate",{})):return "protocol_only"
 promotion=payload.get("promotion",{});decision=promotion.get("decision",{}) if isinstance(promotion,dict) else {}
 if payload.get("passed") is True and (decision.get("promoted") is True or decision.get("champion_id")):return "verified_positive"
 if payload.get("passed") is False or decision.get("reason") in {"CANDIDATE_FAILED","REGRESSION_OR_NO_IMPROVEMENT"}:return "verified_negative"
 return "unresolved"
def build(*,repo_root:Path,output_path:Path)->dict[str,Any]:
 rows=[]
 for path in sorted((repo_root/"results").glob("hexcore*.json")):
  try:payload=json.loads(path.read_text(encoding="utf-8"))
  except (json.JSONDecodeError,UnicodeDecodeError):continue
  if not isinstance(payload,dict):continue
  classification=_classification(payload);name=path.stem.lower();digest=_sha(path);rows.append({"artifact":str(path.relative_to(repo_root)),"sha256":digest,"family":_family(name),"classification":classification,"procedure_id":_procedure(payload),"schema_version":payload.get("schema_version"),"created_at":payload.get("created_at"),"split_bucket":int(digest[:8],16)%10})
 # Artifacts, not individual episodes, own the split. No artifact or procedure
 # may occur in more than one split.
 for row in rows:row["split"]="train" if row["split_bucket"]<7 else ("development" if row["split_bucket"]<9 else "sealed")
 procedures={};leakage=[]
 for row in rows:
  if row["procedure_id"]:procedures.setdefault(row["procedure_id"],set()).add(row["split"])
 for procedure,splits in procedures.items():
  if len(splits)>1:leakage.append({"procedure_id":procedure,"splits":sorted(splits)})
 # Resolve duplicate-procedure leakage by assigning every copy to the most
 # conservative split already selected for that procedure.
 rank={"train":0,"development":1,"sealed":2}
 for collision in leakage:
  target=max(collision["splits"],key=rank.get)
  for row in rows:
   if row["procedure_id"]==collision["procedure_id"]:row["split"]=target
 final_leakage=[]
 for procedure in procedures:
  splits={row["split"] for row in rows if row["procedure_id"]==procedure}
  if len(splits)>1:final_leakage.append(procedure)
 counts={classification:sum(r["classification"]==classification for r in rows) for classification in ("verified_positive","verified_negative","protocol_only","unresolved")};families=sorted({r["family"] for r in rows});splits={split:sum(r["split"]==split for r in rows) for split in ("train","development","sealed")}
 manifest={"schema_version":"aion.verified_trajectory_manifest.v1","artifacts":rows,"summary":{"artifact_count":len(rows),"families":families,"family_count":len(families),"classifications":counts,"splits":splits,"procedure_split_leakage":final_leakage,"positive_training_authority":"CAU-promoted provenance-bearing outcomes only","negative_usage":"criticism, abstention and calibration targets only","protocol_usage":"evaluation infrastructure only; never capability training truth"},"gate":{"all_artifacts_sha256_committed":all(re.fullmatch(r"[0-9a-f]{64}",r["sha256"]) for r in rows),"verified_positives_present":counts["verified_positive"]>0,"verified_negatives_preserved":counts["verified_negative"]>0,"protocols_separated":counts["protocol_only"]>0,"procedure_split_leakage_zero":not final_leakage}}
 output_path.parent.mkdir(parents=True,exist_ok=True);output_path.write_text(json.dumps(manifest,indent=2,sort_keys=True),encoding="utf-8");return manifest
def main():
 p=argparse.ArgumentParser();p.add_argument("--repo-root",type=Path,default=Path("."));p.add_argument("--output",type=Path,default=Path("results/aion_verified_trajectory_corpus_manifest.json"));a=p.parse_args();r=build(repo_root=a.repo_root.resolve(),output_path=a.output.resolve());print(json.dumps({"summary":r["summary"],"gate":r["gate"]},indent=2,sort_keys=True))
if __name__=="__main__":main()
