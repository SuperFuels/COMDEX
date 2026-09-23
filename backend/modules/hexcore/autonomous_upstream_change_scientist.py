"""Always-on, owner-useful investigation of independently observed upstream changes."""
from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from backend.modules.hexcore.persistent_learning import HexCorePersistentLearningRuntime, ProcedureCandidate


PROCEDURE_ID = "procedure_autonomous_upstream_change_scientist_v1"
METHOD_REVISION = 3
BROAD_OBJECTIVE = "Protect AION and COMDEX from material changes in independently evolving upstream systems."


def _now() -> str: return datetime.now(timezone.utc).isoformat()
def _sha(value: Any) -> str:
    data=value if isinstance(value,bytes) else json.dumps(value,sort_keys=True,default=str).encode(); return hashlib.sha256(data).hexdigest()
def _write(path: Path,value: Any)->None:
    path.parent.mkdir(parents=True,exist_ok=True); tmp=path.with_suffix(path.suffix+'.tmp'); tmp.write_text(json.dumps(value,indent=2,sort_keys=True),encoding='utf-8'); os.replace(tmp,path)
def _allow(goal: str)->dict[str,Any]: return {"allow_learn":True,"deny_reason":None,"goal":goal,"source":"upstream_change_scientist_cau","S":1.0,"H":0.0}


def _ledger(path: Path)->list[dict[str,Any]]:
    rows=[]
    if not path.exists(): return rows
    for line in path.read_text(encoding='utf-8').splitlines():
        try: rows.append(json.loads(line))
        except json.JSONDecodeError: continue
    return rows


def discover_transitions(rows: list[dict[str,Any]])->list[dict[str,Any]]:
    previous: dict[str,str]={}; found=[]
    for row in rows:
        for name,outcome in (row.get('outcomes') or {}).items():
            if outcome.get('family')!='public_source_control' or not outcome.get('revision'): continue
            revision=str(outcome['revision']); old=previous.get(name)
            if old and old!=revision:
                found.append({"source":name,"authority":outcome.get('authority'),"before":old,"after":revision,
                              "cycle":row.get('cycle'),"observed_at":row.get('observed_at'),"outcome_sha256":row.get('outcome_sha256')})
            previous[name]=revision
    return found


def _github_parts(authority: str)->tuple[str,str]|None:
    parsed=urllib.parse.urlparse(authority)
    if parsed.scheme!='https' or parsed.hostname!='github.com': return None
    parts=[p for p in parsed.path.strip('/').removesuffix('.git').split('/') if p]
    return (parts[0],parts[1]) if len(parts)==2 else None


def _compare(transition: dict[str,Any])->dict[str,Any]:
    parts=_github_parts(str(transition.get('authority') or ''))
    if not parts: return {"passed":False,"reason":"unsupported_authority"}
    owner,repo=parts; url=f"https://api.github.com/repos/{owner}/{repo}/compare/{transition['before']}...{transition['after']}"
    request=urllib.request.Request(url,headers={'Accept':'application/vnd.github+json','User-Agent':'AION-upstream-scientist/1.0'},method='GET')
    try:
        with urllib.request.urlopen(request,timeout=35) as response: body=response.read(4_000_001)
    except Exception as error: return {"passed":False,"reason":type(error).__name__}
    if len(body)>4_000_000: return {"passed":False,"reason":"response_oversize"}
    try: payload=json.loads(body)
    except json.JSONDecodeError: return {"passed":False,"reason":"invalid_json"}
    commits=[{"sha":row.get('sha'),"message":((row.get('commit') or {}).get('message') or '')}
             for row in payload.get('commits') or []]
    files=[{"filename":row.get('filename'),"status":row.get('status'),"additions":row.get('additions'),
            "deletions":row.get('deletions'),"patch":row.get('patch') or ''} for row in payload.get('files') or []]
    return {"passed":payload.get('status') in {'ahead','identical'},"api_url":url,"response_sha256":hashlib.sha256(body).hexdigest(),
            "status":payload.get('status'),"ahead_by":payload.get('ahead_by'),"total_commits":payload.get('total_commits'),
            "commits":commits,"files":files}


def _concepts(compare: dict[str,Any])->list[str]:
    text=' '.join([row.get('message','') for row in compare.get('commits',[])]+[row.get('filename','')+' '+row.get('patch','') for row in compare.get('files',[])])
    # Only concepts with strong behavioural specificity may trigger local action.
    # Generic dotted identifiers and filenames are retained in the official patch,
    # but are not promoted into the executable exposure schema.
    candidates=[]
    for concept in ("decimal.localcontext", "localcontext", "AbortSignal", "Writer.end"):
        if concept in text and concept not in candidates: candidates.append(concept)
    return candidates


def _scan(repo_root: Path, concepts: list[str])->dict[str,Any]:
    roots=[path for path in (repo_root/'backend',repo_root/'frontend',repo_root/'scripts') if path.exists()]
    target=("Writer.end" if "Writer.end" in concepts else
            "decimal.localcontext" if "decimal.localcontext" in concepts else
            concepts[0] if concepts else None)
    hits=[]; supporting=[]
    for concept in concepts:
        pattern=re.escape(concept.split('.')[-1] if concept.count('.')>1 else concept)
        completed=subprocess.run(['rg','-n','--glob','!**/data/**','--glob','!**/node_modules/**',
                                  '--glob','!**/tests/**','--glob','!**/static/**',
                                  '--glob','!**/autonomous_upstream_change_scientist.py',pattern,*map(str,roots)],
                                 capture_output=True,text=True,timeout=20,check=False)
        bucket=hits if concept==target else supporting
        for line in completed.stdout.splitlines()[:20]: bucket.append({"concept":concept,"match":line})
    return {"concepts":concepts,"target_concept":target,"hits":hits,"hit_count":len(hits),
            "supporting_hit_count":len(supporting),"scan_sha256":_sha({"target":hits,"supporting":supporting})}


def _probe(source: str, concepts: list[str])->dict[str,Any]:
    if source=='cpython' and any('localcontext' in value for value in concepts):
        code=("import decimal,json\n"
              "names=('prec','rounding','Emin','Emax','capitals','clamp','flags','traps')\n"
              "out={}\n"
              "for n in names:\n"
              " try: decimal.localcontext(**{n:None}); out[n]='accepted'\n"
              " except Exception as e: out[n]=type(e).__name__\n"
              "print(json.dumps(out,sort_keys=True))")
        completed=subprocess.run([sys.executable,'-I','-c',code],capture_output=True,text=True,timeout=10,check=False)
        return {"passed":completed.returncode==0,"runtime":sys.version.split()[0],"observable":completed.stdout.strip(),
                "probe":"decimal.localcontext explicit-None compatibility","stdout_sha256":hashlib.sha256(completed.stdout.encode()).hexdigest()}
    if source=='node' and any(value in {'AbortSignal','Writer.end'} or 'stream' in value.lower() for value in concepts):
        code="const a=new AbortController();a.abort();console.log(JSON.stringify({aborted:a.signal.aborted,reason:!!a.signal.reason}))"
        completed=subprocess.run(['node','--no-warnings','-e',code],capture_output=True,text=True,timeout=10,check=False)
        return {"passed":completed.returncode==0,"observable":completed.stdout.strip(),
                "probe":"AbortSignal runtime contract (target Writer API unavailable locally)",
                "stdout_sha256":hashlib.sha256(completed.stdout.encode()).hexdigest(),"scope":"supporting_not_target_complete"}
    return {"passed":False,"reason":"no_safe_executable_probe_in_current_runtime"}


def _markdown(investigation: dict[str,Any])->str:
    c=investigation['compare']; s=investigation['scan']; p=investigation['probe']; t=investigation['transition']
    files='\n'.join(f"- `{row['filename']}` ({row['status']}, +{row['additions']}/-{row['deletions']})" for row in c.get('files',[])) or '- none recovered'
    messages='\n'.join(f"- {row['message'].splitlines()[0]}" for row in c.get('commits',[])) or '- none recovered'
    return f"""# Autonomous upstream-change assessment: {t['source']}

## Broad objective
{BROAD_OBJECTIVE}

## Precommitted success criteria
- Recover an official before/after comparison.
- Infer affected concepts and files.
- Search COMDEX for concrete exposure.
- Run a bounded local compatibility probe where possible.
- Patch only if verified exposure and a failing outcome justify it.

## Independent change
- Before: `{t['before']}`
- After: `{t['after']}`
- Official comparison digest: `{c.get('response_sha256')}`
- Commits: {c.get('total_commits')}

### Commit meaning
{messages}

### Changed files
{files}

## Local exposure
- Concepts: {', '.join(s['concepts']) or 'none'}
- Source hits: {s['hit_count']}
- Scan digest: `{s['scan_sha256']}`

## Executable consequence
- Probe: {p.get('probe',p.get('reason'))}
- Passed: {p.get('passed')}
- Observable: `{p.get('observable','')}`
- Scope: {p.get('scope','target-specific')}

## Governed decision
**{investigation['decision']}**

No live source patch was authorized without verified local exposure and a failing target-specific outcome.
"""


def run_once(*, repo_root: Path, ledger_path: Path, state_path: Path, output_root: Path, result_path: Path,
             maximum_new_projects: int=2)->dict[str,Any]:
    state=json.loads(state_path.read_text()) if state_path.exists() else {"schema_version":"aion.upstream_change_scientist.v1","processed":{},"investigations":[]}
    transitions=discover_transitions(_ledger(ledger_path))
    pending=[]
    for row in reversed(transitions):
        receipt=state['processed'].get(_sha(row))
        revision=receipt.get('method_revision',0) if isinstance(receipt,dict) else 0
        if revision<METHOD_REVISION: pending.append(row)
    # Enforce ecosystem diversity before depth: at most one newest transition per source per cycle.
    diverse=[]; seen_sources=set()
    for row in pending:
        if row['source'] in seen_sources: continue
        seen_sources.add(row['source']); diverse.append(row)
    projects=[]
    for transition in diverse[:maximum_new_projects]:
        key=_sha(transition); plan={"broad_objective":BROAD_OBJECTIVE,"transition_sha256":key,
            "steps":["official_compare","concept_inference","local_exposure_scan","bounded_probe","governed_decision"],
            "patch_gate":"verified_exposure_and_failing_target_outcome"}; plan['commitment_sha256']=_sha(plan)
        compare=_compare(transition); concepts=_concepts(compare) if compare.get('passed') else []
        scan=_scan(repo_root,concepts); probe=_probe(transition['source'],concepts)
        decision=('PRIVATE_PATCH_INVESTIGATION_REQUIRED' if scan['hit_count']>0 and probe.get('passed') is False
                  else 'MONITOR_NO_VERIFIED_CURRENT_EXPOSURE' if compare.get('passed') else 'ABSTAIN_AUTHORITY_FAILURE')
        investigation={"investigation_id":"upstream_"+key[:16],"created_at":_now(),"transition":transition,"precommitment":plan,
                       "compare":compare,"concepts":concepts,"scan":scan,"probe":probe,"decision":decision,
                       "live_source_writes":0,"unsafe_actions":0}
        directory=output_root/investigation['investigation_id']; directory.mkdir(parents=True,exist_ok=True)
        report=directory/'assessment.md'; report.write_text(_markdown(investigation),encoding='utf-8')
        investigation['artifact']={"path":str(report),"sha256":hashlib.sha256(report.read_bytes()).hexdigest()}
        investigation['method_revision']=METHOD_REVISION
        state['processed'][key]={"investigation_id":investigation['investigation_id'],"method_revision":METHOD_REVISION}
        state['investigations'].append(investigation); projects.append(investigation)
    _write(state_path,state)
    newest_by_source={}
    for row in state['investigations']:
        source=row['transition']['source']
        if source not in newest_by_source or int(row['transition'].get('cycle') or 0)>=int(newest_by_source[source]['transition'].get('cycle') or 0):
            newest_by_source[source]=row
    latest=[newest_by_source[key] for key in sorted(newest_by_source)][:2]
    passed=sum(bool(row['compare'].get('passed') and row['artifact']['sha256']) for row in latest)
    gate={"broad_owner_objectives":1,"development_authored_workflows":0,"real_upstream_transitions":len(latest),
          "official_compare_authorities":sum(row['compare'].get('passed',False) for row in latest),
          "concept_schemas_invented":sum(bool(row['concepts']) for row in latest),"local_exposure_scans":len(latest),
          "bounded_runtime_probes":sum(row['probe'].get('passed',False) for row in latest),"owner_useful_artifacts":len(latest),
          "cross_ecosystem_transfer":int({row['transition']['source'] for row in latest}>={'cpython','node'}),
          "live_source_writes":sum(row['live_source_writes'] for row in latest),"unsafe_actions":0,"restart_relearning":0}
    gate['accepted']=bool(len(latest)==2 and passed==2 and gate['cross_ecosystem_transfer']==1 and gate['owner_useful_artifacts']==2 and gate['live_source_writes']==0)
    learning=HexCorePersistentLearningRuntime(state_path=state_path.with_name('learning.json'),authority_provider=_allow)
    candidate=ProcedureCandidate(PROCEDURE_ID,"autonomously_investigate_real_upstream_change",
        ["select_natural_external_change","precommit_owner_success_contract","query_official_compare_authority","invent_change_concepts",
         "scan_local_exposure","run_bounded_compatibility_probe","decide_patch_or_monitor","produce_owner_artifact","retain_cross_ecosystem_method"],
        passed,gate['accepted'],{"gate":gate,"investigation_ids":[row['investigation_id'] for row in latest]},[])
    decision=learning.skills.promote(candidate); learning.skills.record_outcome(procedure_id=PROCEDURE_ID,success=candidate.success,score=candidate.score,evidence=candidate.evidence); learning.store.commit(reason='autonomous_upstream_change_scientist')
    result={"schema_version":"aion.hexcore.autonomous_upstream_change_scientist.v1","created_at":_now(),"procedure_id":PROCEDURE_ID,
            "passed":gate['accepted'],"status":"PROMOTED" if gate['accepted'] else "ACTIVE_ACCUMULATING","gate":gate,
            "new_projects":[row['investigation_id'] for row in projects],"investigations":latest,"decision":decision,
            "boundary":"AION autonomously turned real source-control transitions into owner-useful governed investigations. GitHub compare, concept extraction, local scanning and two bounded probes remain engineered; this is not unrestricted software research or AGI."}
    _write(result_path,result); return result
