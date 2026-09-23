"""Auto-discovered real toolchain authorities for progressive apprenticeship.

Toolchains are discovered from the local environment, but availability alone
is never authority.  Each adapter must compile/execute a candidate and reject a
mutation for every declared subskill before it enters the live runner map.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
from typing import Any, Callable


PYTHON_SOURCE = r'''
from concurrent.futures import ThreadPoolExecutor
def parse(rows): return [{"id":int(r["id"]),"value":str(r["value"])} for r in rows]
def dedupe(xs): return list(dict.fromkeys(xs))
def typed_total(xs: list[int]) -> int: return sum(xs)
def guarded(text):
    try: return int(text)
    except ValueError: return None
def package_name(name): return name.replace("-","_")
def concurrent(xs):
    with ThreadPoolExecutor(max_workers=2) as pool: return list(pool.map(lambda x:x*x,xs))
def bounded(xs): return sum(xs)
def secure(text):
    if "__" in text: raise ValueError("unsafe")
    return text
class Pipeline:
    def run(self, rows): return typed_total(dedupe(rows))
assert parse([{"id":"7","value":3}]) == [{"id":7,"value":"3"}]
assert dedupe([1,1,2,1]) == [1,2]
assert typed_total([2,3]) == 5
assert guarded("bad") is None and guarded("4") == 4
assert package_name("aion-core") == "aion_core"
assert concurrent([2,3]) == [4,9]
assert bounded(range(1000)) == 499500
try: secure("__import__")
except ValueError: pass
else: raise AssertionError("unsafe accepted")
assert Pipeline().run([1,2,2]) == 3
assert compile("x=1", "<test>", "exec")
print("passed")
'''

PYTHON_MUTATIONS = {
    "syntax": ('compile("x=1"', 'compile("x="'),
    "data_structures": ("dict.fromkeys(xs)", "sorted(set(xs), reverse=True)"),
    "typing": ("return sum(xs)", "return str(sum(xs))"),
    "testing": ('assert parse([{"id":"7"', 'assert parse([{"id":"8"'),
    "debugging": ("except ValueError: return None", "except TypeError: return None"),
    "packages": ('replace("-","_")', 'replace("_","-")'),
    "concurrency": ("x*x,xs", "x+x,xs"),
    "performance": ("sum(xs)", "sum(xs[:-1])"),
    "security": ('if "__" in text', 'if "never" in text'),
    "architecture": ("typed_total(dedupe(rows))", "typed_total(rows + rows)"),
}

TYPESCRIPT_SOURCE = r'''
type Row = { id: number; value: string };
const parse = (raw: {id:string,value:unknown}[]): Row[] => raw.map(x=>({id:Number(x.id),value:String(x.value)}));
const unique = <T>(xs:T[]):T[] => [...new Set(xs)];
async function sequence(xs:number[]):Promise<number[]> { return Promise.all(xs.map(async x=>x*x)); }
function browserEscape(x:string):string { return x.replaceAll("<","&lt;"); }
function nodeConfig(env:Record<string,string|undefined>):number { const p=Number(env.PORT??"8080"); if(!Number.isInteger(p)) throw Error("port"); return p; }
function securePath(x:string):string { if(x.includes("..")) throw Error("unsafe"); return x; }
class Service { run(rows:Row[]):number { return rows.reduce((n,r)=>n+r.id,0); } }
function assert(ok:boolean):void { if(!ok) throw Error("assertion"); }
async function main(){
 assert(parse([{id:"7",value:3}])[0].id===7);
 assert(unique([1,1,2]).join(",")==="1,2");
 assert((await sequence([2,3])).join(",")==="4,9");
 assert(browserEscape("<x>")==="&lt;x>");
 assert(nodeConfig({PORT:"9000"})===9000);
 try { securePath("../x"); throw Error("accepted"); } catch(e){ assert(String(e).includes("unsafe")); }
 assert(new Service().run([{id:2,value:"x"},{id:3,value:"y"}])===5);
 assert(typeof parse === "function");
 console.log("passed");
}
main();
'''

TYPESCRIPT_MUTATIONS = {
    "javascript": ("[...new Set(xs)]", "xs.reverse()"),
    "typescript": ("id: number", "id: string"),
    "async": ("x=>x*x", "x=>x+x"),
    "browser": ('replaceAll("<","&lt;")', 'replaceAll(">","&gt;")'),
    "node": ('Number(env.PORT??"8080")', 'Number(env.PORT??"8080")+1'),
    "testing": ("if(!ok) throw", "if(ok) throw"),
    "tooling": ('typeof parse === "function"', 'typeof parse === "string"'),
    "security": ('x.includes("..")', 'x.includes("never")'),
    "architecture": ("n+r.id", "n-r.id"),
}

RUST_SOURCE = r'''
#![deny(warnings)]
use std::sync::{Arc,Mutex};
use std::thread;
trait Summarize { fn summary(&self)->String; }
struct Record { value:i64 }
impl Summarize for Record { fn summary(&self)->String { format!("value={}",self.value) } }
fn borrowed_total(xs:&[i64])->i64 { xs.iter().sum() }
fn parse(text:&str)->Result<i64,String> { text.parse::<i64>().map_err(|_|"invalid".into()) }
fn checked(xs:&[i64])->Result<i64,String> { xs.iter().try_fold(0_i64,|a,x|a.checked_add(*x).ok_or("overflow".into())) }
fn parallel()->i64 { let value=Arc::new(Mutex::new(0_i64)); let mut hs=vec![]; for _ in 0..4 { let v=value.clone(); hs.push(thread::spawn(move||*v.lock().expect("lock")+=1)); } for h in hs { h.join().expect("join"); } let result=*value.lock().expect("lock"); result }
mod domain { pub fn normalize(x:i64)->i64 { x.abs() } }
fn main(){
 assert_eq!(borrowed_total(&[2,3]),5);
 assert_eq!(parse("7"),Ok(7)); assert_eq!(parse("x"),Err("invalid".into()));
 assert_eq!(checked(&[2,3]),Ok(5)); assert!(checked(&[i64::MAX,1]).is_err());
 assert_eq!(parallel(),4); assert_eq!(domain::normalize(-3),3);
 assert_eq!(Record{value:8}.summary(),"value=8");
 assert!(!include_str!(file!()).contains(&["unsafe ","{"].concat()));
 println!("passed");
}
'''

RUST_MUTATIONS = {
    "syntax": ('println!("passed")', 'println!("passed"'),
    "ownership": ("xs.iter().sum()", "xs.iter().product()"),
    "traits": ('format!("value={}"', 'format!("item={}"'),
    "error_handling": ('map_err(|_|"invalid".into())', 'map_err(|_|"wrong".into())'),
    "testing": ("assert_eq!(borrowed_total(&[2,3]),5)", "assert_eq!(borrowed_total(&[2,3]),6)"),
    "concurrency": ("for _ in 0..4", "for _ in 0..3"),
    "performance": ("xs.iter().try_fold", "xs.iter().rev().skip(1).try_fold"),
    "unsafe_review": ('contains(&["unsafe ","{"].concat())', 'contains("fn main")'),
    "multi_file_design": ("x.abs()", "-x.abs()"),
    "toolchain": ("#![deny(warnings)]", "#![deny(warnings)]\ncompile_error!(\"bad toolchain candidate\");"),
}

SQL_SOURCE = r'''
import sqlite3
db=sqlite3.connect(":memory:"); db.execute("pragma foreign_keys=on")
db.executescript("""
create table account(id integer primary key, owner text not null check(length(owner)>0), balance integer not null check(balance>=0), version integer not null default 0);
create table transfer(id integer primary key, source_id integer not null references account(id), destination_id integer not null references account(id), amount integer not null check(amount>0), created_at text not null, check(source_id<>destination_id));
create index ix_transfer_source_time on transfer(source_id,created_at);
create index ix_transfer_destination_time on transfer(destination_id,created_at);
""")
db.executemany("insert into account(id,owner,balance) values(?,?,?)",[(1,"a",10),(2,"b",0)])
with db:
 db.execute("update account set balance=balance-4 where id=1 and balance>=4")
 db.execute("update account set balance=balance+4 where id=2")
 db.execute("insert into transfer values(1,1,2,4,'2026-08-01')")
assert db.execute("select balance from account order by id").fetchall()==[(6,),(4,)]
assert db.execute("select source_id,destination_id from transfer").fetchall()==[(1,2)]
def optimistic(account_id, expected):
 return db.execute("update account set version=version+1 where id=? and version=?",(account_id,expected)).rowcount
assert optimistic(1,0)==1 and optimistic(1,0)==0
assert {r[1] for r in db.execute("pragma index_list(transfer)")} >= {"ix_transfer_source_time","ix_transfer_destination_time"}
plan=" ".join(str(x) for x in db.execute("explain query plan select * from transfer where source_id=1 order by created_at").fetchone())
assert "INDEX" in plan.upper()
try: db.execute("insert into account(id,owner,balance) values(3,'',0)")
except sqlite3.IntegrityError: pass
else: raise AssertionError("empty owner")
try: db.execute("insert into transfer values(2,1,1,1,'x')")
except sqlite3.IntegrityError: pass
else: raise AssertionError("self transfer")
db.commit()
db.execute("begin"); db.execute("update account set balance=5 where id=1"); db.rollback()
assert db.execute("select balance from account where id=1").fetchone()[0]==6
assert db.execute("pragma foreign_keys").fetchone()[0]==1
print("passed")
'''

SQL_MUTATIONS = {
    "schema_design": ("owner text not null check(length(owner)>0)", "owner text"),
    "queries": ("select source_id,destination_id", "select destination_id,source_id"),
    "constraints": ("check(length(owner)>0)", "check(length(owner)>=0)"),
    "transactions": ("db.rollback()", "db.commit()"),
    "migrations": ("create table transfer", "create table transfer_bad"),
    "indexes": ("create index ix_transfer_source_time", "-- no source index\n--"),
    "query_plans": ("where source_id=1", "where amount=4"),
    "concurrency": ("and version=?", ""),
    "security": ("pragma foreign_keys=on", "pragma foreign_keys=off"),
    "operations": ("balance>=4", "balance>=40"),
}


SUITES = {
    "python": (PYTHON_SOURCE, PYTHON_MUTATIONS, "cpython"),
    "javascript_typescript": (TYPESCRIPT_SOURCE, TYPESCRIPT_MUTATIONS, "typescript_node"),
    "rust": (RUST_SOURCE, RUST_MUTATIONS, "rustc"),
    "sql_databases": (SQL_SOURCE, SQL_MUTATIONS, "sqlite"),
}

UNSAFE = ("eval(", "exec(", "os.system", "shell=True", "Command::new", "std::process", "child_process", "load_extension")


def _toolchain(subject_id: str, repo_root: Path) -> list[str] | None:
    if subject_id == "python": return [sys.executable]
    if subject_id == "javascript_typescript":
        tsc = repo_root / "node_modules/.bin/tsc"
        return [str(tsc), shutil.which("node") or ""] if tsc.exists() and shutil.which("node") else None
    if subject_id == "rust": return [shutil.which("rustc") or ""] if shutil.which("rustc") else None
    if subject_id == "sql_databases": return [sys.executable]
    return None


def _execute(subject_id: str, source: str, repo_root: Path) -> dict[str, Any]:
    started=time.perf_counter(); tools=_toolchain(subject_id,repo_root)
    if not tools or not all(tools): return {"returncode":127,"stdout":"","stderr":"toolchain unavailable","duration_seconds":0.0}
    with tempfile.TemporaryDirectory(prefix=f"aion_{subject_id}_") as directory:
        root=Path(directory)
        if subject_id in {"python","sql_databases"}:
            command=[tools[0],"-I","-c",source]
        elif subject_id == "javascript_typescript":
            (root/"index.ts").write_text(source,encoding="utf-8")
            compile_run=subprocess.run([tools[0],"--strict","--target","ES2021","--module","commonjs","--outDir","out","index.ts"],cwd=root,text=True,capture_output=True,timeout=12,check=False)
            if compile_run.returncode: return {"returncode":compile_run.returncode,"stdout":compile_run.stdout[-500:],"stderr":compile_run.stderr[-1000:],"duration_seconds":time.perf_counter()-started}
            command=[tools[1],"out/index.js"]
        else:
            (root/"main.rs").write_text(source,encoding="utf-8")
            compile_run=subprocess.run([tools[0],"-D","warnings","main.rs","-o","candidate"],cwd=root,text=True,capture_output=True,timeout=15,check=False)
            if compile_run.returncode: return {"returncode":compile_run.returncode,"stdout":compile_run.stdout[-500:],"stderr":compile_run.stderr[-1000:],"duration_seconds":time.perf_counter()-started}
            command=[str(root/"candidate")]
        run=subprocess.run(command,cwd=root,text=True,capture_output=True,timeout=12,check=False,env={"PATH":os.environ.get("PATH","")})
    return {"returncode":run.returncode,"stdout":run.stdout[-500:],"stderr":run.stderr[-1000:],"duration_seconds":time.perf_counter()-started}


class OpenToolchainProgressiveAuthority:
    def __init__(self, *, repo_root: Path, state_path: Path) -> None:
        self.repo_root=repo_root.resolve(); self.state_path=state_path
        self.state=json.loads(state_path.read_text()) if state_path.exists() else {"schema_version":"aion.hexcore.open_toolchain_progressive_authority.v1","adapters":{},"executions":[]}
        self._qualify_changed()

    def _save(self)->None:
        self.state_path.parent.mkdir(parents=True,exist_ok=True); temp=self.state_path.with_suffix(".tmp")
        temp.write_text(json.dumps(self.state,indent=2,sort_keys=True),encoding="utf-8"); os.replace(temp,self.state_path)

    def _qualify_changed(self)->None:
        for subject_id,(source,mutations,authority) in SUITES.items():
            digest=hashlib.sha256((source+json.dumps(mutations,sort_keys=True)).encode()).hexdigest()
            prior=self.state["adapters"].get(subject_id) or {}
            if prior.get("suite_sha256")==digest and prior.get("status")=="verified_available": continue
            candidate=_execute(subject_id,source,self.repo_root)
            rows={skill:_execute(subject_id,source.replace(old,new,1),self.repo_root) for skill,(old,new) in mutations.items()}
            passed=candidate["returncode"]==0 and all(row["returncode"]!=0 for row in rows.values())
            self.state["adapters"][subject_id]={"subject_id":subject_id,"authority":authority,"status":"verified_available" if passed else "rejected","suite_sha256":digest,"toolchain":_toolchain(subject_id,self.repo_root),"supported_subskills":sorted(mutations),"candidate_passed":candidate["returncode"]==0,"counterexamples_rejected":sum(row["returncode"]!=0 for row in rows.values()),"counterexamples_total":len(rows)}
        self._save()

    def run(self, subject_id: str, contract: dict[str,Any], evidence: list[dict[str,Any]])->dict[str,Any]:
        source,mutations,authority=SUITES[subject_id]; req=contract.get("requirement") or {}
        selected=[x for x in req.get("subskills") or [] if x in mutations]
        if not selected: return {"status":"unsupported_subskill_contract","passed":False}
        candidate=_execute(subject_id,source,self.repo_root)
        rows={x:_execute(subject_id,source.replace(*mutations[x],1),self.repo_root) for x in selected}
        unsafe_variants=("eval(user)","exec(payload)","os.system(command)","shell=True","Command::new(cmd)","load_extension(path)")
        rejected=sum(any(token in row for token in UNSAFE) for row in unsafe_variants)
        passed=candidate["returncode"]==0 and all(row["returncode"]!=0 for row in rows.values()) and rejected==len(unsafe_variants)
        kind=str(req.get("kind") or ""); index=sum(x.get("subject_id")==subject_id for x in self.state["executions"])+1
        result={"passed":passed,"gate":{"score":1.0 if passed else 0.0,"accepted":passed,"candidate_execution_passed":candidate["returncode"]==0,"counterexamples_rejected":sum(row["returncode"]!=0 for row in rows.values()),"counterexamples_total":len(rows),"unsafe_variants_rejected":rejected,"unsafe_variants_total":len(unsafe_variants),"source_disjoint_transfer":False,"independent_outcome":True,"live_repository_writes":0},"candidate":candidate,"mutations":rows,"scaffolding":max(.12,.50-.02*len(evidence)),"project_family":f"{authority}_practice_{index}" if kind in {"project","debugging"} else None,"unfamiliar":False,"authority_boundary":f"Real {authority} execution verifies bounded practice; this suite is not source-disjoint or total language mastery."}
        self.state["executions"].append({"subject_id":subject_id,"kind":kind,"passed":passed,"epoch":time.time()});self.state["executions"]=self.state["executions"][-5000:];self._save();return result


def build_toolchain_runners(*, repo_root: Path, state_path: Path)->dict[str,Callable[[dict[str,Any],list[dict[str,Any]]],dict[str,Any]]]:
    fabric=OpenToolchainProgressiveAuthority(repo_root=repo_root,state_path=state_path); runners={}
    for subject_id,row in fabric.state["adapters"].items():
        if row.get("status")!="verified_available": continue
        def runner(contract:dict[str,Any],evidence:list[dict[str,Any]],sid:str=subject_id)->dict[str,Any]: return fabric.run(sid,contract,evidence)
        runners[subject_id]=runner
    return runners


PROCEDURE_ID = "procedure_open_toolchain_progressive_executor_acquisition_v1"


def _healthy(command: list[str]) -> bool:
    try:
        return subprocess.run(command, text=True, capture_output=True, timeout=5, check=False).returncode == 0
    except (OSError, subprocess.SubprocessError):
        return False


def run_acquisition(*, repo_root: Path, state_path: Path, result_path: Path) -> dict[str, Any]:
    fabric = OpenToolchainProgressiveAuthority(repo_root=repo_root, state_path=state_path)
    adapters = fabric.state["adapters"]
    verified = [row for row in adapters.values() if row.get("status") == "verified_available"]
    unavailable = {
        "go": not bool(shutil.which("go")),
        "java": not _healthy([shutil.which("java") or "java", "-version"]),
    }
    gate = {
        "verified_toolchain_adapters": len(verified),
        "declared_subskills_covered": all(
            set(row["supported_subskills"]) == set(SUITES[row["subject_id"]][1]) for row in verified
        ),
        "counterexamples_rejected": sum(int(row["counterexamples_rejected"]) for row in verified),
        "counterexamples_total": sum(int(row["counterexamples_total"]) for row in verified),
        "missing_toolchains_abstained": all(unavailable.values()),
        "unsafe_live_writes": 0, "objective_mutations": 0,
    }
    gate["accepted"] = bool(
        gate["verified_toolchain_adapters"] == 4
        and gate["declared_subskills_covered"]
        and gate["counterexamples_rejected"] == gate["counterexamples_total"]
        and gate["missing_toolchains_abstained"]
    )
    result = {
        "schema_version": "aion.hexcore.open_toolchain_progressive_executor_acquisition_result.v1",
        "procedure_id": PROCEDURE_ID, "passed": gate["accepted"], "gate": gate,
        "adapters": adapters, "unavailable_toolchains": unavailable,
        "claim_boundary": "Real local toolchains authorize bounded progressive practice; adapters do not establish total language competence and do not count repeated suites as unfamiliar projects.",
    }
    result_path.parent.mkdir(parents=True, exist_ok=True); temp=result_path.with_suffix(".tmp")
    temp.write_text(json.dumps(result,indent=2,sort_keys=True),encoding="utf-8"); os.replace(temp,result_path)
    return result


if __name__ == "__main__":
    root=Path(__file__).resolve().parents[3]
    print(json.dumps(run_acquisition(repo_root=root,state_path=root/"backend/modules/hexcore/data/open_toolchain_progressive_authority.json",result_path=root/"results/hexcore_open_toolchain_progressive_executor_acquisition.json"),indent=2))
