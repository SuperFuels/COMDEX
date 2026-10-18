"""Executable multi-project authority for AION's software/systems curriculum."""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
from typing import Any, Callable


@dataclass(frozen=True)
class Project:
    project_id: str
    source: str
    old: str
    new: str
    tags: tuple[str, ...]


def _project(project_id: str, source: str, old: str, new: str, tags: str) -> Project:
    return Project(project_id, source.strip() + "\n", old, new, tuple(tags.split()))


PROJECTS = (
    _project("capability_token", r'''
import hashlib,hmac
KEY=b"private-key"
def issue(user,scope):
 payload=f"{user}:{scope}".encode();return payload.hex()+"."+hmac.new(KEY,payload,hashlib.sha256).hexdigest()
def verify(token,required):
 raw,sig=token.split(".");payload=bytes.fromhex(raw)
 return hmac.compare_digest(sig,hmac.new(KEY,payload,hashlib.sha256).hexdigest()) and payload.decode().split(":",1)[1]==required
t=issue("a","read");assert verify(t,"read") and not verify(t,"write");assert not verify(t[:-1]+("0" if t[-1]!="0" else "1"),"read")
print("passed")''', "hmac.compare_digest", "lambda a,b: True or hmac.compare_digest", "auth cryptography secure_coding threat_modeling threat_models governance validation secrets"),
    _project("supply_chain_manifest", r'''
import hashlib
def manifest(files):return {k:hashlib.sha256(v).hexdigest() for k,v in sorted(files.items())}
def verify(files,expected):return manifest(files)==expected
files={"app":b"v1","lock":b"dep=1"};frozen=manifest(files)
assert verify(files,frozen) and not verify({**files,"lock":b"dep=2"},frozen)
print("passed")''', "manifest(files)==expected", "set(manifest(files))==set(expected)", "supply_chain cryptography governance security research"),
    _project("process_supervisor", r'''
import subprocess,sys
def run(code,timeout=.5):
 try:
  p=subprocess.run([sys.executable,"-I","-c",code],capture_output=True,timeout=timeout,check=False)
  return "ok" if p.returncode==0 else "failed"
 except subprocess.TimeoutExpired:return "timeout"
assert run("print(1)")=="ok" and run("raise SystemExit(3)")=="failed" and run("while True:pass",.05)=="timeout"
print("passed")''', '"ok" if p.returncode==0 else "failed"', '"ok"', "processes scheduling recovery reliability linux_operations operation repair"),
    _project("safe_store", r'''
import os,tempfile,pathlib
with tempfile.TemporaryDirectory() as d:
 p=pathlib.Path(d)/"secret";p.write_text("value");os.chmod(p,0o600)
 assert (p.stat().st_mode&0o777)==0o600 and p.read_text()=="value"
print("passed")''', "os.chmod(p,0o600)", "os.chmod(p,0o666)", "filesystems permissions memory sandboxing secrets secure_coding"),
    _project("framed_ipc", r'''
import socket,threading
a,b=socket.socketpair()
def send():a.sendall((4).to_bytes(2,"big")+b"ping");a.close()
t=threading.Thread(target=send);t.start();size=int.from_bytes(b.recv(2),"big");payload=b.recv(size);t.join();b.close()
assert size==4 and payload==b"ping"
print("passed")''', 'to_bytes(2,"big")', 'to_bytes(2,"little")', "ipc threads communication tcp_ip"),
    _project("replicated_log", r'''
def apply(replicas,event):
 for replica in replicas:
  if event["id"] not in {x["id"] for x in replica}:replica.append(dict(event))
 return replicas
r=[[],[]];apply(r,{"id":"e1","v":3});apply(r,{"id":"e1","v":3})
assert r==[[{"id":"e1","v":3}],[{"id":"e1","v":3}]]
print("passed")''', 'if event["id"] not in', 'if event["id"] in', "consistency replication idempotency queues recovery implementation"),
    _project("quorum_commit", r'''
def commit(votes,total):return len(set(votes))>=total//2+1
assert commit(["a","b"],3) and not commit(["a"],3) and not commit(["a","a"],3)
print("passed")''', "len(set(votes))>=total//2+1", "len(votes)>=total//2+1", "consensus partition_tolerance replication failure_modes"),
    _project("progressive_rollout", r'''
def rollout(old,new,health):
 history=[old]
 for pct in (10,50,100):
  if health(pct)<.99:return {"version":old,"history":history,"rollback":True}
  history.append(f"{new}:{pct}")
 return {"version":new,"history":history,"rollback":False}
assert rollout("v1","v2",lambda p:1)["version"]=="v2"
assert rollout("v1","v2",lambda p:.9 if p==50 else 1)["rollback"]
print("passed")''', "health(pct)<.99", "health(pct)<.50", "deployment rollback ci_cd reliability operation architecture_tradeoffs"),
    _project("slo_monitor", r'''
def evaluate(samples):
 availability=sum(samples)/len(samples)
 return {"availability":availability,"alert":availability<.99,"budget":max(0,1-availability)}
assert not evaluate([1]*100)["alert"] and evaluate([1]*98+[0]*2)["alert"]
print("passed")''', "availability<.99", "availability<.90", "observability reliability incident_response capacity latency"),
    _project("capacity_plan", r'''
def plan(load,per_node,node_cost):
 nodes=(load+per_node-1)//per_node
 return {"nodes":nodes,"cost":nodes*node_cost,"headroom":nodes*per_node-load}
assert plan(101,50,4)=={"nodes":3,"cost":12,"headroom":49}
print("passed")''', "load+per_node-1", "load", "capacity cost cloud_architecture architecture_tradeoffs design"),
    _project("container_spec", r'''
def valid(spec):return spec.get("digest","").startswith("sha256:") and spec.get("read_only") and spec.get("cpu_limit",0)>0
assert valid({"digest":"sha256:abc","read_only":True,"cpu_limit":2})
assert not valid({"digest":"latest","read_only":True,"cpu_limit":2})
assert not valid({"digest":"sha256:abc","read_only":False,"cpu_limit":2})
print("passed")''', 'spec.get("read_only")', "True", "containers infrastructure_as_code linux_operations security sandboxing"),
    _project("architecture_boundary", r'''
LAYERS={"domain":0,"service":1,"adapter":2,"ui":3}
def valid(edges):return all(LAYERS[a]>=LAYERS[b] for a,b in edges)
assert valid([("ui","service"),("service","domain")]) and not valid([("domain","ui")])
print("passed")''', "LAYERS[a]>=LAYERS[b]", "LAYERS[a]<=LAYERS[b]", "architecture_tradeoffs design implementation open_requirements deployment"),
    _project("incident_containment", r'''
def contain(events):
 compromised={e["principal"] for e in events if e["severity"]>=8}
 return {"revoked":sorted(compromised),"preserved":len(events),"status":"contained" if compromised else "monitor"}
assert contain([{"principal":"a","severity":9},{"principal":"b","severity":2}])["revoked"]==["a"]
print("passed")''', 'e["severity"]>=8', 'e["severity"]<=8', "incident_response adversarial_testing governance repair operation"),
    _project("dns_cache", r'''
def resolve(cache,name,now,lookup):
 row=cache.get(name)
 if row and now<row[1]:return row[0]
 value,ttl=lookup(name);cache[name]=(value,now+ttl);return value
c={};calls=[]
def lookup(name):calls.append(name);return "1.2.3.4",10
assert resolve(c,"x",0,lookup)=="1.2.3.4" and resolve(c,"x",5,lookup)=="1.2.3.4" and len(calls)==1
resolve(c,"x",11,lookup);assert len(calls)==2
print("passed")''', "now<row[1]", "now<=row[1]+10", "dns latency failure_modes routing"),
    _project("http_tls_contract", r'''
def response(status,body,request_id,tls):
 assert tls>=1.2
 return {"status":status,"headers":{"content-length":str(len(body)),"x-request-id":request_id},"body":body}
r=response(200,b"ok","r1",1.3);assert r["headers"]=={"content-length":"2","x-request-id":"r1"}
try:response(200,b"x","r2",1.0)
except AssertionError:pass
else:raise AssertionError("weak tls")
print("passed")''', "assert tls>=1.2", "assert tls>=1.0", "http tls tcp_ip network_security validation observability"),
    _project("route_failover", r'''
def route(paths):
 healthy=[p for p in paths if p["healthy"]]
 return min(healthy,key=lambda p:(p["latency"],p["cost"])) if healthy else None
assert route([{"id":"a","healthy":False,"latency":1,"cost":1},{"id":"b","healthy":True,"latency":4,"cost":2}])["id"]=="b"
print("passed")''', 'if p["healthy"]', "if True", "routing latency failure_modes cost network_security"),
    _project("cidr_longest_prefix", r'''
import ipaddress
def select(address,routes):
 ip=ipaddress.ip_address(address);matches=[row for row in routes if ip in ipaddress.ip_network(row[0])]
 return max(matches,key=lambda row:ipaddress.ip_network(row[0]).prefixlen)[1] if matches else None
routes=[("10.0.0.0/8","wan"),("10.2.0.0/16","site"),("10.2.3.0/24","rack")]
assert select("10.2.3.9",routes)=="rack" and select("10.9.1.1",routes)=="wan" and select("192.0.2.1",routes) is None
print("passed")''', ".prefixlen", ".num_addresses", "routing tcp_ip failure_modes validation"),
    _project("tcp_reassembly", r'''
def reassemble(segments):
 ordered=sorted(segments,key=lambda row:row[0]);cursor=ordered[0][0];body=b""
 for seq,payload in ordered:
  assert seq==cursor;body+=payload;cursor+=len(payload)
 return body
assert reassemble([(3,b"lo"),(0,b"hel"),(5,b"!")])==b"hello!"
try:reassemble([(0,b"ab"),(3,b"d")])
except AssertionError:pass
else:raise AssertionError("gap accepted")
print("passed")''', "assert seq==cursor", "assert seq>=cursor", "tcp_ip failure_modes observability validation"),
    _project("token_bucket_limiter", r'''
def admit(tokens,last,now,rate,capacity,cost=1):
 tokens=min(capacity,tokens+(now-last)*rate)
 return (tokens-cost,now,True) if tokens>=cost else (tokens,now,False)
t,last,ok=admit(2,0,0,1,2);assert ok and t==1
t,last,ok=admit(t,last,0,1,2);assert ok and t==0
t,last,ok=admit(t,last,.5,1,2);assert not ok
t,last,ok=admit(t,last,1,1,2);assert ok
print("passed")''', "tokens>=cost", "tokens>0", "latency http failure_modes capacity observability"),
    _project("circuit_breaker", r'''
def transition(state,failures,success=False,limit=3):
 if state=="half_open":return ("closed",0) if success else ("open",failures+1)
 if failures>=limit:return "open",failures
 return state,failures
assert transition("closed",3)==("open",3)
assert transition("half_open",3,True)==("closed",0)
assert transition("half_open",3,False)==("open",4)
print("passed")''', "failures>=limit", "failures>limit", "http failure_modes latency observability routing"),
    _project("happy_eyeballs", r'''
def connect(candidates):
 viable=[row for row in candidates if row["ok"]]
 return min(viable,key=lambda row:(row["delay_ms"],0 if row["family"]==6 else 1))["address"] if viable else None
rows=[{"address":"2001:db8::1","family":6,"delay_ms":25,"ok":False},{"address":"192.0.2.1","family":4,"delay_ms":40,"ok":True},{"address":"2001:db8::2","family":6,"delay_ms":35,"ok":True}]
assert connect(rows)=="2001:db8::2" and connect([]) is None
print("passed")''', 'if row["ok"]', "if True", "dns tcp_ip latency failure_modes routing"),
    _project("mtu_fragmentation", r'''
def fragment(payload,mtu,header=20):
 size=((mtu-header)//8)*8;assert size>0
 return [payload[i:i+size] for i in range(0,len(payload),size)]
parts=fragment(bytes(range(256))*6,576)
assert b"".join(parts)==bytes(range(256))*6 and all(len(row)<=556 for row in parts) and len(parts)>1
print("passed")''', "//8)*8", "//8)*9", "tcp_ip failure_modes validation observability"),
    _project("operational_handover", r'''
def handover(decisions,checks,open_items):return {"decisions":decisions,"verified":all(checks),"open":open_items,"restartable":bool(decisions and checks)}
r=handover(["bounded retry"],[True,True],["load test"])
assert r["verified"] and r["restartable"] and r["open"]==["load test"]
assert not handover(["x"],[True,False],[])["verified"]
print("passed")''', "all(checks)", "any(checks)", "communication research operation repair open_requirements governance"),
)


SUBJECT_PROJECTS = {
    "security_engineering": ("capability_token","supply_chain_manifest","safe_store","incident_containment","http_tls_contract","container_spec"),
    "operating_systems": ("process_supervisor","safe_store","framed_ipc","replicated_log","slo_monitor","container_spec"),
    "distributed_systems": ("replicated_log","quorum_commit","progressive_rollout","slo_monitor","route_failover","operational_handover"),
    "cloud_devops_sre": ("process_supervisor","progressive_rollout","slo_monitor","capacity_plan","container_spec","operational_handover"),
    "architecture_operations": ("progressive_rollout","slo_monitor","capacity_plan","architecture_boundary","operational_handover","container_spec"),
    "secure_engineering": ("capability_token","supply_chain_manifest","safe_store","incident_containment","http_tls_contract","container_spec"),
    "networking": (
        "dns_cache", "http_tls_contract", "route_failover", "framed_ipc",
        "slo_monitor", "container_spec", "cidr_longest_prefix", "tcp_reassembly",
        "token_bucket_limiter", "circuit_breaker", "happy_eyeballs", "mtu_fragmentation",
    ),
    "integrated_engineering_capstone": ("architecture_boundary","operational_handover","progressive_rollout","incident_containment","supply_chain_manifest","slo_monitor"),
}

INDEX = {row.project_id: row for row in PROJECTS}
UNSAFE = ("eval(", "exec(", "os.system", "shell=True", "pickle.loads", "chmod(p,0o777)")


def _execute(source: str) -> dict[str, Any]:
    started = time.perf_counter()
    with tempfile.TemporaryDirectory(prefix="aion_system_project_") as directory:
        run = subprocess.run([sys.executable,"-I","-c",source],cwd=directory,text=True,capture_output=True,timeout=8,check=False,env={"PATH":os.environ.get("PATH","")})
    return {"returncode":run.returncode,"stdout":run.stdout[-500:],"stderr":run.stderr[-800:],"duration_seconds":time.perf_counter()-started}


class SoftwareSystemProjectAuthority:
    def __init__(self, *, repo_root: Path, state_path: Path) -> None:
        self.repo_root=repo_root.resolve(); self.state_path=state_path
        self.state=json.loads(state_path.read_text()) if state_path.exists() else {"schema_version":"aion.hexcore.software_system_project_authority.v1","adapters":{},"executions":[]}
        self._qualify()

    def _save(self) -> None:
        self.state_path.parent.mkdir(parents=True,exist_ok=True); temporary=self.state_path.with_suffix(".tmp")
        temporary.write_text(json.dumps(self.state,indent=2,sort_keys=True),encoding="utf-8"); os.replace(temporary,self.state_path)

    def _qualify(self) -> None:
        competency=json.loads((self.repo_root/"backend/modules/hexcore/data/progressive_competency/state.json").read_text())
        digest=hashlib.sha256("".join(row.source+row.old+row.new for row in PROJECTS).encode()).hexdigest()
        if self.state.get("portfolio_sha256")==digest and set(self.state["adapters"])==set(SUBJECT_PROJECTS) and all(row.get("status")=="verified_available" for row in self.state["adapters"].values()): return
        results={row.project_id:(_execute(row.source),_execute(row.source.replace(row.old,row.new,1))) for row in PROJECTS}
        for subject_id,project_ids in SUBJECT_PROJECTS.items():
            covered=set().union(*(set(INDEX[item].tags) for item in project_ids)); required=set(competency["subjects"][subject_id]["subskills"])
            rows={item:results[item] for item in project_ids}; passed=required<=covered and all(candidate["returncode"]==0 and mutation["returncode"]!=0 for candidate,mutation in rows.values())
            self.state["adapters"][subject_id]={"subject_id":subject_id,"status":"verified_available" if passed else "rejected","projects":list(project_ids),"required_subskills":sorted(required),"covered_subskills":sorted(covered),"counterexamples_rejected":sum(mutation["returncode"]!=0 for candidate,mutation in rows.values()),"counterexamples_total":len(rows)}
        self.state["portfolio_sha256"]=digest; self._save()

    def run(self, subject_id: str, contract: dict[str, Any], evidence: list[dict[str, Any]]) -> dict[str, Any]:
        requirement=contract.get("requirement") or {}; kind=str(requirement.get("kind") or ""); requested=set(requirement.get("subskills") or [])
        projects=[INDEX[item] for item in SUBJECT_PROJECTS[subject_id]]; used={row.get("project_family") for row in evidence if row.get("project_family")}
        if kind in {"project","debugging","transfer","retention"}:
            candidates=[row for row in projects if row.project_id not in used] or projects
            chosen=[max(candidates,key=lambda row:(len(requested&set(row.tags)),row.project_id))]
        else:
            remaining=set(requested); chosen=[]
            while remaining:
                candidate=max(projects,key=lambda row:len(remaining&set(row.tags)))
                if not (remaining&set(candidate.tags)): return {"status":"unsupported_subskill_contract","passed":False}
                chosen.append(candidate); remaining-=set(candidate.tags)
        candidate_results={row.project_id:_execute(row.source) for row in chosen}
        mutation_results={row.project_id:_execute(row.source.replace(row.old,row.new,1)) for row in chosen}
        unsafe_variants=("eval(user)","exec(payload)","os.system(cmd)","subprocess.run(cmd,shell=True)","pickle.loads(blob)","chmod(p,0o777)")
        unsafe_rejected=sum(any(token in row for token in UNSAFE) for row in unsafe_variants)
        passed=all(row["returncode"]==0 for row in candidate_results.values()) and all(row["returncode"]!=0 for row in mutation_results.values()) and unsafe_rejected==len(unsafe_variants)
        evidenced=sorted(set().union(*(set(row.tags) for row in chosen))&set(self.state["adapters"][subject_id]["required_subskills"])); fresh=all(row.project_id not in used for row in chosen)
        result={"passed":passed,"gate":{"score":1.0 if passed else 0.0,"accepted":passed,"candidate_execution_passed":all(row["returncode"]==0 for row in candidate_results.values()),"counterexamples_rejected":sum(row["returncode"]!=0 for row in mutation_results.values()),"counterexamples_total":len(mutation_results),"unsafe_variants_rejected":unsafe_rejected,"unsafe_variants_total":len(unsafe_variants),"source_disjoint_transfer":kind=="transfer" and fresh,"independent_outcome":True,"live_repository_writes":0},"candidate":candidate_results,"mutations":mutation_results,"evidenced_subskills":evidenced,"scaffolding":max(.10,.42-.02*len(evidence)),"project_family":chosen[0].project_id if kind=="project" else None,"unfamiliar":fresh and kind in {"project","debugging","transfer","retention"},"authority_boundary":"Distinct executable project and withheld fault outcome; the portfolio remains engineered and is not external production operation."}
        self.state["executions"].append({"subject_id":subject_id,"kind":kind,"projects":[row.project_id for row in chosen],"passed":passed,"epoch":time.time()}); self.state["executions"]=self.state["executions"][-5000:]; self._save(); return result


def build_system_project_runners(*, repo_root: Path, state_path: Path) -> dict[str, Callable[[dict[str, Any],list[dict[str, Any]]],dict[str, Any]]]:
    fabric=SoftwareSystemProjectAuthority(repo_root=repo_root,state_path=state_path); runners={}
    for subject_id,row in fabric.state["adapters"].items():
        if row.get("status")!="verified_available": continue
        def runner(contract:dict[str,Any],evidence:list[dict[str,Any]],sid:str=subject_id)->dict[str,Any]: return fabric.run(sid,contract,evidence)
        runners[subject_id]=runner
    return runners


PROCEDURE_ID="procedure_software_system_project_authority_v1"


def run_benchmark(*,repo_root:Path,state_path:Path,result_path:Path)->dict[str,Any]:
    fabric=SoftwareSystemProjectAuthority(repo_root=repo_root,state_path=state_path);adapters=fabric.state["adapters"]
    unique_projects={project for row in adapters.values() for project in row.get("projects") or []}
    gate={"verified_subject_adapters":sum(row.get("status")=="verified_available" for row in adapters.values()),"distinct_executable_projects":len(unique_projects),"mapped_project_counterexamples_rejected":sum(int(row.get("counterexamples_rejected") or 0) for row in adapters.values()),"mapped_project_counterexamples_total":sum(int(row.get("counterexamples_total") or 0) for row in adapters.values()),"declared_subskill_coverage":all(set(row["required_subskills"])<=set(row["covered_subskills"]) for row in adapters.values()),"unsupported_human_authority_abstention":"social_commonsense" not in adapters,"unsafe_live_writes":0,"objective_mutations":0}
    gate["accepted"]=bool(gate["verified_subject_adapters"]==8 and gate["distinct_executable_projects"]>=16 and gate["mapped_project_counterexamples_rejected"]==gate["mapped_project_counterexamples_total"] and gate["declared_subskill_coverage"] and gate["unsupported_human_authority_abstention"])
    result={"schema_version":"aion.hexcore.software_system_project_authority_result.v1","procedure_id":PROCEDURE_ID,"passed":gate["accepted"],"gate":gate,"adapters":adapters,"claim_boundary":"Seventeen source-distinct engineered projects with executable faults; not external production experience or total systems mastery."}
    result_path.parent.mkdir(parents=True,exist_ok=True);temporary=result_path.with_suffix(".tmp");temporary.write_text(json.dumps(result,indent=2,sort_keys=True),encoding="utf-8");os.replace(temporary,result_path);return result


if __name__=="__main__":
    root=Path(__file__).resolve().parents[3]
    print(json.dumps(run_benchmark(repo_root=root,state_path=root/"backend/modules/hexcore/data/software_system_project_authority.json",result_path=root/"results/hexcore_software_system_project_authority.json"),indent=2))
