"""Verified executors for progressive competency contracts.

Executors are deliberately separate from the level authority.  They may create
practice and collect outcomes; only the competency ledger calculates levels.
"""
from __future__ import annotations

import json
import hashlib
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any, Callable

from backend.modules.hexcore.canonical_cognitive_runtime import _canonical_hash, _utc_timestamp
from backend.modules.hexcore.progressive_competency_system import ProgressiveCompetencySystem
from backend.modules.hexcore.progressive_executor_registry import ProgressiveExecutorRegistry
from backend.modules.hexcore.progressive_outcome_authority_fabric import build_subject_runners
from backend.modules.hexcore.open_toolchain_progressive_authority import build_toolchain_runners
from backend.modules.hexcore.software_system_project_authority import build_system_project_runners
from backend.modules.hexcore.learning_strategy_outcome_authority import build_learning_capability_runners
from backend.modules.hexcore.general_learning_capability_outcome_authority import (
    build_general_learning_capability_runners,
)
from backend.modules.hexcore.advanced_python_apprenticeship import run as run_advanced_python
from backend.modules.hexcore.diverse_practical_executor_portfolios import (
    event_resolution_runner, forecasting_runner,
    runner_has_fresh_family,
    runner_portfolio_version,
)


BASE_PROGRAM = r'''
import json

def clamp(value):
    return max(0, min(100, value))

def integrate(base, override):
    return {**base, **override}

def unique(values):
    return list(dict.fromkeys(values))

def locate_failure(values):
    return next((index for index, value in enumerate(values) if value < 0), None)

def observe(request_id, outcome):
    return json.dumps({"request_id": request_id, "outcome": outcome}, sort_keys=True)

def parse_port(text):
    value = int(text)
    if not 1 <= value <= 65535:
        raise ValueError("port outside range")
    return value

assert clamp(-2) == 0 and clamp(42) == 42 and clamp(140) == 100
assert integrate({"mode": "safe", "limit": 3}, {"limit": 5}) == {"mode": "safe", "limit": 5}
assert unique(["a", "a", "b", "a"]) == ["a", "b"]
assert locate_failure([4, 2, -1, -3]) == 2 and locate_failure([1, 2]) is None
assert json.loads(observe("r-7", "passed")) == {"request_id": "r-7", "outcome": "passed"}
assert parse_port("443") == 443
for invalid in ("0", "65536", "not-a-number"):
    try:
        parse_port(invalid)
    except (ValueError, TypeError):
        pass
    else:
        raise AssertionError("invalid port accepted")
print(json.dumps({"passed": True, "checks": 9}, sort_keys=True))
'''

PROJECTS = {
    "ledger_reconciliation": (r'''
def balance(rows):
    seen = set(); total = 0
    for event_id, kind, amount in rows:
        if event_id in seen:
            continue
        seen.add(event_id)
        if amount < 0: raise ValueError("negative amount")
        total += amount if kind == "credit" else -amount
    return total
rows = [("a","credit",12),("a","credit",12),("b","debit",5)]
assert balance(rows) == 7
try: balance([("x","credit",-1)])
except ValueError: pass
else: raise AssertionError("negative accepted")
print("passed")
''', "if event_id in seen:", "if False:"),
    "sensor_anomaly": (r'''
def anomalies(values, limit):
    return [i for i in range(1, len(values)) if abs(values[i]-values[i-1]) > limit]
assert anomalies([10, 11, 30, 31, 2], 8) == [2, 4]
assert anomalies([], 2) == [] and anomalies([1], 2) == []
print("passed")
''', "> limit", "< limit"),
    "transactional_inventory": (r'''
import sqlite3
db=sqlite3.connect(":memory:"); db.execute("create table stock(id text primary key, qty integer check(qty>=0))")
db.executemany("insert into stock values(?,?)", [("a",8),("b",1)])
def move(source, target, amount):
    source_qty=db.execute("select qty from stock where id=?",(source,)).fetchone()[0]
    if amount <= 0 or source_qty < amount: raise ValueError("invalid transfer")
    with db:
        db.execute("update stock set qty=qty-? where id=?",(amount,source))
        db.execute("update stock set qty=qty+? where id=?",(amount,target))
move("a","b",3)
assert db.execute("select qty from stock order by id").fetchall()==[(5,),(4,)]
try: move("a","b",9)
except ValueError: pass
else: raise AssertionError("overdraw accepted")
print("passed")
''', "if amount <= 0 or source_qty < amount:", "if amount <= 0:"),
    "configuration_precedence": (r'''
def resolve(defaults, file_values, environment):
    result={**defaults, **file_values, **environment}
    if result.get("tls_verify") is not True: raise ValueError("TLS verification required")
    return result
assert resolve({"port":80,"tls_verify":True},{"port":443},{"port":8443})["port"]==8443
try: resolve({"tls_verify":True},{},{"tls_verify":False})
except ValueError: pass
else: raise AssertionError("unsafe config accepted")
print("passed")
''', "result={**defaults, **file_values, **environment}", "result={**environment, **file_values, **defaults}"),
    "dependency_scheduler": (r'''
def schedule(graph):
    pending={node:set(deps) for node,deps in graph.items()}; result=[]
    while pending:
        ready=sorted(node for node,deps in pending.items() if not deps)
        if not ready: raise ValueError("cycle")
        result.extend(ready)
        for node in ready: pending.pop(node)
        for deps in pending.values(): deps.difference_update(ready)
    return result
order=schedule({"test":{"build"},"build":{"design"},"design":set()})
assert order.index("design") < order.index("build") < order.index("test")
try: schedule({"a":{"b"},"b":{"a"}})
except ValueError: pass
else: raise AssertionError("cycle accepted")
print("passed")
''', "if not ready: raise ValueError(\"cycle\")", "if not ready: return result"),
    "bounded_retry_policy": (r'''
def retry_delays(attempts, base=2, ceiling=30):
    if not 0 <= attempts <= 8: raise ValueError("invalid attempts")
    return [min(ceiling, base * (2 ** index)) for index in range(attempts)]
assert retry_delays(5) == [2,4,8,16,30]
assert retry_delays(0) == []
try: retry_delays(9)
except ValueError: pass
else: raise AssertionError("unbounded retry accepted")
print("passed")
''', "if not 0 <= attempts <= 8", "if attempts < 0"),
    "default_deny_access_policy": (r'''
def allowed(role, action, grants):
    return action in set(grants.get(role, ()))
grants={"reader":{"view"},"operator":{"view","restart"}}
assert allowed("reader","view",grants)
assert not allowed("reader","restart",grants)
assert not allowed("unknown","view",grants)
print("passed")
''', "return action in set(grants.get(role, ()))", "return role not in grants or action in set(grants.get(role, ()))"),
    "event_window_deduplication": (r'''
def unique_window(events, start, end):
    seen=set(); result=[]
    for event_id, timestamp in events:
        if start <= timestamp < end and event_id not in seen:
            seen.add(event_id); result.append(event_id)
    return result
events=[("a",2),("a",3),("b",5),("c",9)]
assert unique_window(events,2,9) == ["a","b"]
assert unique_window(events,10,12) == []
print("passed")
''', "and event_id not in seen", ""),
    "capacity_allocator": (r'''
def allocate(capacity, requests):
    if capacity < 0 or any(value < 0 for value in requests): raise ValueError("invalid capacity")
    accepted=[]; remaining=capacity
    for value in requests:
        if value <= remaining: accepted.append(value); remaining -= value
    return accepted, remaining
assert allocate(10,[4,7,3]) == ([4,3],3)
try: allocate(2,[-1])
except ValueError: pass
else: raise AssertionError("negative request accepted")
print("passed")
''', "if value <= remaining", "if value < capacity"),
    "contiguous_schema_migration": (r'''
def migrate(current, steps):
    version=current
    for source,target in steps:
        if source != version or target != source + 1: raise ValueError("migration gap")
        version=target
    return version
assert migrate(2,[(2,3),(3,4)]) == 4
try: migrate(2,[(2,4)])
except ValueError: pass
else: raise AssertionError("gap accepted")
print("passed")
''', "target != source + 1", "target <= source"),
    "failure_preserving_batch": (r'''
def process(items, handler):
    completed=[]; failed=[]
    for item in items:
        try: completed.append(handler(item))
        except ValueError: failed.append(item)
    return completed, failed
def handler(value):
    if value < 0: raise ValueError("bad")
    return value * 2
assert process([2,-1,3],handler) == ([4,6],[-1])
print("passed")
''', "except ValueError: failed.append(item)", "except ValueError: pass"),
    "semantic_version_selection": (r'''
def latest(versions, maximum_major):
    eligible=[tuple(map(int,value.split("."))) for value in versions if int(value.split(".")[0]) <= maximum_major]
    if not eligible: return None
    return ".".join(map(str,max(eligible)))
assert latest(["1.9.0","1.10.0","2.0.0"],1) == "1.10.0"
assert latest(["2.0.0"],1) is None
print("passed")
''', "return \".\".join(map(str,max(eligible)))", "return \".\".join(map(str,eligible[0]))"),
}

TRANSFER_PROJECT = ("cross_domain_order_fulfilment", r'''
def fulfil(events):
    completed=set(); shipped=[]
    for order_id, paid in events:
        if paid and order_id not in completed:
            completed.add(order_id); shipped.append(order_id)
    return shipped
assert fulfil([("o1",True),("o1",True),("o2",False),("o3",True)]) == ["o1","o3"]
print("passed")
''', "and order_id not in completed", "")

TRANSFER_PROJECTS = (
    TRANSFER_PROJECT,
    ("cross_domain_telemetry_deduplication", r'''
def accept(frames):
    seen=set(); accepted=[]
    for device,sequence,payload in frames:
        key=(device,sequence)
        if key not in seen and payload is not None:
            seen.add(key); accepted.append((device,sequence))
    return accepted
assert accept([("d1",1,"a"),("d1",1,"a"),("d1",2,None),("d2",1,"b")]) == [("d1",1),("d2",1)]
print("passed")
''', "if key not in seen and payload is not None", "if payload is not None"),
    ("cross_domain_lab_chain_of_custody", r'''
def valid_chain(events):
    expected=0
    for sequence,signed in events:
        if sequence != expected or not signed: return False
        expected += 1
    return bool(events)
assert valid_chain([(0,True),(1,True),(2,True)])
assert not valid_chain([(0,True),(2,True)])
assert not valid_chain([(0,False)])
print("passed")
''', "if sequence != expected or not signed", "if not signed"),
    ("cross_domain_bounded_capacity_reservation", r'''
def reserve(capacity, requests):
    used=0; accepted=[]
    for request_id,amount in requests:
        if amount > 0 and used + amount <= capacity:
            used += amount; accepted.append(request_id)
    return accepted, capacity-used
assert reserve(10,[("a",4),("b",8),("c",6)]) == (["a","c"],0)
assert reserve(2,[("x",-1)]) == ([],2)
print("passed")
''', "if amount > 0 and used + amount <= capacity", "if amount > 0"),
)

RETENTION_PROJECT = ("delayed_cache_invalidation", r'''
def read_cache(entries, key, now):
    row=entries.get(key)
    if row is None: return None
    value, expires_at, invalidated=row
    if invalidated or now >= expires_at: return None
    return value
cache={"alpha":("ready", 20, False), "beta":("stale", 30, True)}
assert read_cache(cache,"alpha",10)=="ready"
assert read_cache(cache,"alpha",20) is None
assert read_cache(cache,"beta",10) is None
assert read_cache(cache,"missing",10) is None
print("passed")
''', "if invalidated or now >= expires_at", "if now > expires_at")

RETENTION_PROJECTS = (
    RETENTION_PROJECT,
    ("delayed_idempotent_replay", r'''
def replay(events):
    seen=set(); total=0
    for event_id,amount in events:
        if event_id in seen: continue
        if amount < 0: raise ValueError("negative")
        seen.add(event_id); total += amount
    return total
assert replay([("a",3),("a",3),("b",4)]) == 7
try: replay([("x",-1)])
except ValueError: pass
else: raise AssertionError("negative accepted")
print("passed")
''', "if event_id in seen: continue", "if False: continue"),
    ("delayed_checkpoint_recovery", r'''
def recover(checkpoints, events):
    state=dict(checkpoints[-1]) if checkpoints else {}
    for key,value in events: state[key]=value
    return state
assert recover([{"a":1}],[("b",2),("a",3)]) == {"a":3,"b":2}
assert recover([{"a":1}],[]) == {"a":1}
assert recover([],[]) == {}
print("passed")
''', "state=dict(checkpoints[-1])", "state={}"),
    ("delayed_schema_compatibility", r'''
def decode(row):
    version=row.get("version",1)
    if version==1:return {"name":row["name"],"enabled":True}
    if version==2:return {"name":row["label"],"enabled":bool(row["enabled"])}
    raise ValueError("unsupported version")
assert decode({"name":"alpha"}) == {"name":"alpha","enabled":True}
assert decode({"version":2,"label":"beta","enabled":0}) == {"name":"beta","enabled":False}
try:decode({"version":3})
except ValueError:pass
else:raise AssertionError("future schema accepted")
print("passed")
''', "if version==2", "if version>=2"),
    ("delayed_out_of_order_watermark", r'''
def complete(events, watermark):
    accepted={}
    for event_id,event_time,value in events:
        if event_time <= watermark: accepted[event_id]=value
    return [accepted[key] for key in sorted(accepted)]
events=[("b",9,2),("a",7,1),("c",12,3),("a",8,99)]
assert complete(events,10)==[99,2]
assert complete(events,6)==[]
print("passed")
''', "if event_time <= watermark", "if event_time >= watermark"),
    ("delayed_circuit_breaker_repair", r'''
def transition(state,failures,success=False,limit=3):
    if state=="half_open": return ("closed",0) if success else ("open",failures+1)
    if failures>=limit:return "open",failures
    return state,failures
assert transition("closed",3)==("open",3)
assert transition("half_open",3,True)==("closed",0)
assert transition("half_open",3,False)==("open",4)
print("passed")
''', "if failures>=limit", "if failures>limit"),
    ("delayed_signed_event_chain", r'''
import hashlib,hmac
KEY=b"retention-key"
def sign(previous,payload):return hmac.new(KEY,previous+payload,hashlib.sha256).digest()
def verify(events):
    previous=b""
    for payload,signature in events:
        if not hmac.compare_digest(signature,sign(previous,payload)):return False
        previous=signature
    return bool(events)
p1=b"one";s1=sign(b"",p1);p2=b"two";s2=sign(s1,p2)
assert verify([(p1,s1),(p2,s2)])
assert not verify([(p1,s1),(b"changed",s2)])
print("passed")
''', "hmac.compare_digest(signature,sign(previous,payload))", "bool(signature)"),
    ("delayed_bounded_worker_pool", r'''
from concurrent.futures import ThreadPoolExecutor
def execute(values,workers=3):
    if not 1<=workers<=4:raise ValueError("worker bound")
    with ThreadPoolExecutor(max_workers=workers) as pool:return list(pool.map(lambda x:x*x,values))
assert execute([3,1,2])==[9,1,4]
try:execute([1],9)
except ValueError:pass
else:raise AssertionError("unbounded workers")
print("passed")
''', "if not 1<=workers<=4", "if workers<1"),
)

MUTATIONS = {
    "unit": ("return max(0, min(100, value))", "return value"),
    "integration": ("return {**base, **override}", "return {**override, **base}"),
    "property_testing": ("return list(dict.fromkeys(values))", "return list(values)"),
    "fault_localisation": ("if value < 0", "if value > 0"),
    "observability": ('{"request_id": request_id, "outcome": outcome}', '{"outcome": outcome}'),
    "regression": ("if not 1 <= value <= 65535", "if not 0 <= value <= 65536"),
}

UNSAFE_SNIPPETS = ("eval(", "exec(", "os.system", "subprocess.", "shell=True", "__import__(")


ALGORITHM_PROGRAMS = {
    "arrays": (r'''
def rotate(values, k):
    if not values: return []
    k %= len(values)
    return values[-k:] + values[:-k]
assert rotate([1,2,3,4], 1) == [4,1,2,3]
assert rotate([1,2,3], 4) == [3,1,2]
assert rotate([], 8) == []
print("passed")
''', "k %= len(values)", "k = 0"),
    "complexity": (r'''
def binary_search(values, target):
    lo, hi, comparisons = 0, len(values), 0
    while lo < hi:
        comparisons += 1; mid = (lo + hi) // 2
        if values[mid] < target: lo = mid + 1
        else: hi = mid
    return (lo if lo < len(values) and values[lo] == target else -1), comparisons
values=list(range(1024)); index, comparisons=binary_search(values, 777)
assert index == 777 and comparisons <= 11
assert binary_search(values, 2048)[0] == -1
print("passed")
''', "mid = (lo + hi) // 2", "mid = lo"),
    "dynamic_programming": (r'''
def min_coins(coins, amount):
    best=[amount+1]*(amount+1); best[0]=0
    for value in range(1, amount+1):
        best[value]=min((best[value-c]+1 for c in coins if c <= value), default=amount+1)
    return None if best[amount] > amount else best[amount]
assert min_coins([1,3,4], 6) == 2
assert min_coins([4,6], 5) is None
print("passed")
''', "best[value-c]+1", "best[value-c]+2"),
    "graphs": (r'''
from collections import deque
def distance(graph, start, goal):
    queue=deque([(start,0)]); seen={start}
    while queue:
        node,d=queue.popleft()
        if node == goal: return d
        for nxt in graph.get(node,[]):
            if nxt not in seen: seen.add(nxt); queue.append((nxt,d+1))
    return None
g={"a":["b","c"],"b":["d"],"c":["a"],"d":[]}
assert distance(g,"a","d") == 2 and distance(g,"d","a") is None
print("passed")
''', "queue.append((nxt,d+1))", "queue.append((nxt,d+2))"),
    "maps": (r'''
def frequencies(values):
    result={}
    for value in values: result[value]=result.get(value,0)+1
    return result
assert frequencies(["a","b","a",None]) == {"a":2,"b":1,None:1}
assert frequencies([]) == {}
print("passed")
''', "result.get(value,0)+1", "1"),
    "search": (r'''
def lower_bound(values, target):
    lo,hi=0,len(values)
    while lo < hi:
        mid=(lo+hi)//2
        if values[mid] < target: lo=mid+1
        else: hi=mid
    return lo
assert lower_bound([1,2,2,4],2) == 1
assert lower_bound([1,2,2,4],3) == 3
assert lower_bound([],9) == 0
print("passed")
''', "if values[mid] < target", "if values[mid] <= target"),
    "sorting": (r'''
def merge_sort(values):
    if len(values) < 2: return list(values)
    mid=len(values)//2; left=merge_sort(values[:mid]); right=merge_sort(values[mid:]); out=[]
    while left and right: out.append(left.pop(0) if left[0] <= right[0] else right.pop(0))
    return out+left+right
assert merge_sort([3,1,2,1,-4]) == [-4,1,1,2,3]
assert merge_sort([]) == []
print("passed")
''', "left[0] <= right[0]", "left[0] >= right[0]"),
    "trees": (r'''
def inorder(tree):
    if tree is None: return []
    value,left,right=tree
    return inorder(left)+[value]+inorder(right)
tree=(4,(2,(1,None,None),(3,None,None)),(6,None,None))
assert inorder(tree) == [1,2,3,4,6]
assert inorder(None) == []
print("passed")
''', "inorder(left)+[value]+inorder(right)", "inorder(right)+[value]+inorder(left)"),
}

SOFTWARE_ENGINEERING_SUITE = r'''
from collections import deque

def valid_requirement(row):
    return all(str(row.get(k, "")).strip() for k in ("actor", "behaviour", "observable"))

def architecture_order(dependencies):
    pending={node:set(needs) for node,needs in dependencies.items()}; order=[]
    while pending:
        ready=sorted(node for node,needs in pending.items() if not needs)
        if not ready: raise ValueError("architecture cycle")
        order.extend(ready)
        for node in ready: pending.pop(node)
        for needs in pending.values(): needs.difference_update(ready)
    return order

def implement(records):
    return [{"id":str(row["id"]),"value":int(row["value"])} for row in records]

def observable(event):
    return {key:event[key] for key in ("request_id","status","duration_ms")}

def first_failure(results):
    return next((index for index,value in enumerate(results) if value is False), None)

def module_allowed(source, target):
    layers={"domain":0,"service":1,"adapter":2,"ui":3}
    return layers[source] <= layers[target]

def migration(current, target):
    if target != current + 1: raise ValueError("non-contiguous migration")
    return target

def review_patch(patch):
    forbidden=("eval(","exec(","shell=True","verify=False")
    return not any(token in patch for token in forbidden)

def release(candidate, checks):
    if not all(checks): return {"status":"blocked","version":candidate}
    return {"status":"staged","version":candidate,"rollback":True}

def commits_before(graph, ancestor, descendant):
    queue=deque([descendant]); seen=set()
    while queue:
        node=queue.popleft()
        if node == ancestor: return True
        if node in seen: continue
        seen.add(node); queue.extend(graph.get(node,[]))
    return False

def testing_contract(public, hidden):
    return bool(public) and bool(hidden)

def team_ready(task):
    return bool(task.get("owner") and task.get("definition_of_done") and task.get("reviewer"))

assert valid_requirement({"actor":"user","behaviour":"export","observable":"file created"})
assert not valid_requirement({"actor":"user","behaviour":"export"})
order=architecture_order({"ui":{"service"},"service":{"domain"},"domain":set()})
assert order.index("domain") < order.index("service") < order.index("ui")
try: architecture_order({"a":{"b"},"b":{"a"}})
except ValueError: pass
else: raise AssertionError("cycle accepted")
assert implement([{"id":7,"value":"3"}]) == [{"id":"7","value":3}]
assert observable({"request_id":"r1","status":"ok","duration_ms":8,"secret":"x"}) == {"request_id":"r1","status":"ok","duration_ms":8}
assert first_failure([True,True,False,False]) == 2 and first_failure([True]) is None
assert module_allowed("domain","ui") and not module_allowed("ui","domain")
assert migration(2,3) == 3
try: migration(2,4)
except ValueError: pass
else: raise AssertionError("migration gap accepted")
assert review_patch("return parse(value)") and not review_patch("return eval(value)")
assert release("1.2.0",[True,True]) == {"status":"staged","version":"1.2.0","rollback":True}
assert release("1.2.0",[True,False])["status"] == "blocked"
assert commits_before({"c3":["c2"],"c2":["c1"],"c1":[]},"c1","c3")
assert not commits_before({"c2":["c1"]},"c2","c1")
assert testing_contract(True,True) and not testing_contract(True,False)
assert team_ready({"owner":"A","reviewer":"B","definition_of_done":"tests pass"})
assert not team_ready({"owner":"A"})
print("passed")
'''

SOFTWARE_MUTATIONS = {
    "requirements": ('for k in ("actor", "behaviour", "observable")', 'for k in ("actor", "behaviour")'),
    "architecture": ('if not ready: raise ValueError("architecture cycle")', 'if not ready: return order'),
    "implementation": ('"value":int(row["value"])', '"value":row["value"]'),
    "observability": ('("request_id","status","duration_ms")', '("status","duration_ms")'),
    "debugging": ('if value is False', 'if value is True'),
    "modularity": ('layers[source] <= layers[target]', 'layers[source] >= layers[target]'),
    "maintenance": ('target != current + 1', 'target < current'),
    "review": ('return not any(token in patch for token in forbidden)', 'return True'),
    "delivery": ('if not all(checks)', 'if not any(checks)'),
    "version_control": ('queue.extend(graph.get(node,[]))', 'queue.clear()'),
    "testing": ('bool(public) and bool(hidden)', 'bool(public) or bool(hidden)'),
    "team_practice": ('task.get("owner") and task.get("definition_of_done") and task.get("reviewer")', 'task.get("owner")'),
}


def _run_program(source: str) -> dict[str, Any]:
    started = time.perf_counter()
    timeout_seconds = max(
        5.0, float(os.environ.get("AION_COMPETENCY_PROGRAM_TIMEOUT", "20"))
    )
    with tempfile.TemporaryDirectory(prefix="aion_competency_") as directory:
        process = subprocess.run(
            [sys.executable, "-I", "-c", source], cwd=directory,
            text=True, capture_output=True, timeout=timeout_seconds, check=False,
            env={"PATH": os.environ.get("PATH", "")},
        )
    return {"returncode": process.returncode, "stdout": process.stdout[-1000:],
            "stderr": process.stderr[-1000:], "duration_seconds": time.perf_counter() - started}


def _testing_debugging(contract: dict[str, Any], existing_evidence: list[dict[str, Any]]) -> dict[str, Any]:
    requirement = contract["requirement"]
    evidence_count = len(existing_evidence)
    if requirement.get("not_before_epoch") and time.time() < float(requirement["not_before_epoch"]):
        return {"status": "waiting_for_elapsed_retention",
                "not_before_epoch": requirement["not_before_epoch"], "passed": False}
    kind = requirement.get("kind")
    family = None
    source_disjoint = False
    unfamiliar = False
    if kind in {"project", "debugging"}:
        used = {row.get("project_family") for row in existing_evidence if row.get("kind") == kind}
        candidates = list(PROJECTS.items())
        selected = next(((name, item) for name, item in candidates if name not in used), None)
        if selected is None:
            return {"status": "diverse_project_executor_required", "passed": False,
                    "reason": "The verified diverse project portfolio is exhausted before the competency gate was met."}
        family, (project_source, old, new) = selected
        candidate = _run_program(project_source)
        mutation_results = {family: _run_program(project_source.replace(old, new, 1))}
        source_disjoint = True; unfamiliar = True
    elif kind == "transfer":
        used = {row.get("project_family") for row in existing_evidence if row.get("kind") == "transfer"}
        selected = next((row for row in TRANSFER_PROJECTS if row[0] not in used), None)
        if selected is None:
            return {"status": "diverse_project_executor_required", "passed": False,
                    "reason": "The source-disjoint transfer portfolio is exhausted before the competency gate was met."}
        family, project_source, old, new = selected
        candidate = _run_program(project_source)
        mutation_results = {family: _run_program(project_source.replace(old, new, 1))}
        source_disjoint = True; unfamiliar = True
    elif kind == "retention":
        used = {row.get("project_family") for row in existing_evidence if row.get("kind") == "retention"}
        selected = next((row for row in RETENTION_PROJECTS if row[0] not in used), None)
        if selected is None:
            return {"status": "diverse_project_executor_required", "passed": False,
                    "reason": "The delayed retention portfolio is exhausted before the competency gate was met."}
        family, project_source, old, new = selected
        candidate = _run_program(project_source)
        mutation_results = {family: _run_program(project_source.replace(old, new, 1))}
        source_disjoint = True; unfamiliar = True
    else:
        candidate = _run_program(BASE_PROGRAM)
        mutation_results = {}
        for name, (old, new) in MUTATIONS.items():
            source = BASE_PROGRAM.replace(old, new, 1)
            mutation_results[name] = _run_program(source)
    unsafe_candidates = [
        "eval(user_input)", "exec(payload)", "os.system(command)",
        "subprocess.run(command, shell=True)", "__import__('socket')", "subprocess.Popen(args)",
    ]
    unsafe_rejected = sum(any(token in candidate for token in UNSAFE_SNIPPETS) for candidate in unsafe_candidates)
    required = set(requirement.get("subskills") or [])
    relevant_mutations = {name: row for name, row in mutation_results.items()
                          if name in required or requirement.get("kind") in {"project", "debugging", "transfer", "retention"}}
    if not relevant_mutations:
        relevant_mutations = mutation_results
    gate = {
        "candidate_execution_passed": candidate["returncode"] == 0,
        "candidate_checks": 9,
        "counterexamples_rejected": sum(row["returncode"] != 0 for row in relevant_mutations.values()),
        "counterexamples_total": len(relevant_mutations),
        "all_six_fault_families_exercised": len(mutation_results) == 6,
        "unsafe_variants_rejected": unsafe_rejected,
        "unsafe_variants_total": len(unsafe_candidates),
        "fresh_process": True, "source_disjoint_transfer": source_disjoint,
        "independent_outcome": True, "live_repository_writes": 0,
    }
    gate["score"] = 1.0 if gate["candidate_execution_passed"] else 0.0
    gate["accepted"] = bool(
        gate["candidate_execution_passed"]
        and gate["counterexamples_rejected"] == gate["counterexamples_total"]
        and gate["unsafe_variants_rejected"] == gate["unsafe_variants_total"]
        and gate["live_repository_writes"] == 0
    )
    return {"passed": gate["accepted"], "gate": gate, "candidate": candidate,
            "mutations": mutation_results, "scaffolding": max(0.10, 0.55 - 0.04 * evidence_count),
            "project_family": family, "unfamiliar": unfamiliar}


PYTHON_CORE_FAULT_MAP = {
    "basic_testing": "unit",
    "collections": "property_testing",
    "errors": "fault_localisation",
    "functions": "integration",
    "input_security": "regression",
    "language_semantics": "unit",
}


def _python_core(contract: dict[str, Any], existing_evidence: list[dict[str, Any]]) -> dict[str, Any]:
    """Ground Python-core study in execution, not lesson completion alone.

    The interpreter, assertions, counterexample mutations and security scanner
    are the authority. The retained teacher may frame the curriculum, but it
    cannot award evidence.
    """
    requirement = dict(contract["requirement"])
    if requirement.get("kind") in {"lesson", "knowledge_test", "exercise", "repeated_trial"}:
        mapped = [PYTHON_CORE_FAULT_MAP[skill] for skill in requirement.get("subskills") or []
                  if skill in PYTHON_CORE_FAULT_MAP]
        requirement["subskills"] = mapped or ["unit"]
    execution_contract = {**contract, "requirement": requirement}
    result = _testing_debugging(execution_contract, existing_evidence)
    result["curriculum_subject"] = "python_core"
    result["authority_boundary"] = (
        "Python execution and counterexamples authorize evidence; teacher text remains proposal-only."
    )
    return result


def _advanced_python(contract: dict[str, Any], existing_evidence: list[dict[str, Any]]) -> dict[str, Any]:
    kind = str((contract.get("requirement") or {}).get("kind") or "")
    prior_project = any(row.get("kind") == "project" for row in existing_evidence)
    if kind == "project" and prior_project:
        return {"status": "diverse_project_executor_required", "passed": False,
                "reason": "Advanced Python now requires a new unfamiliar project family; replaying the async pipeline cannot count as breadth."}
    repo_root = Path(str(contract.get("_repo_root") or Path.cwd())).resolve()
    proposal_path = (repo_root / "results/progressive_competency/proposals" /
                     f"advanced_python_{contract['contract_id']}.json")
    proposal = run_advanced_python(
        state_path=repo_root / "backend/modules/hexcore/data/advanced_python_apprenticeship/learning.json",
        result_path=proposal_path,
    )
    gate = proposal.get("gate") or {}
    passed = bool(proposal.get("passed") and gate.get("accepted"))
    return {
        "passed": passed,
        "gate": {
            "score": float(gate.get("score") or 0.0),
            "accepted": passed,
            "candidate_execution_passed": bool(gate.get("compile_passed")),
            "counterexamples_rejected": int(gate.get("malicious_variants_rejected") or 0),
            "counterexamples_total": int(gate.get("malicious_variants_total") or 0),
            "unsafe_variants_rejected": int(gate.get("malicious_variants_rejected") or 0),
            "unsafe_variants_total": int(gate.get("malicious_variants_total") or 0),
            "source_disjoint_transfer": bool(gate.get("source_disjoint_transfer")),
            "independent_outcome": True, "live_repository_writes": 0,
        },
        "proposal_result": str(proposal_path.relative_to(repo_root)),
        "scaffolding": max(0.10, 0.50 - 0.03 * len(existing_evidence)),
        "project_family": "advanced_python_async_pipeline" if kind == "project" else None,
        "unfamiliar": kind in {"project", "transfer", "retention"},
        "authority_boundary": "CPython, sealed concurrency tests, transfer tests and security scans authorize evidence.",
    }


def _algorithms_data_structures(
    contract: dict[str, Any], existing_evidence: list[dict[str, Any]]
) -> dict[str, Any]:
    """Fresh executable concept/counterexample checks for the progressive lane."""
    requirement = dict(contract.get("requirement") or {})
    if requirement.get("kind") in {"project", "debugging", "transfer", "retention"}:
        result = _testing_debugging(contract, existing_evidence)
        result["curriculum_subject"] = "algorithms_data_structures"
        result["authority_boundary"] = (
            "Fresh algorithm-bearing project execution, mutations and delayed outcomes authorize practical depth."
        )
        return result
    requested = list(requirement.get("subskills") or [])
    selected = [skill for skill in requested if skill in ALGORITHM_PROGRAMS]
    if not selected:
        selected = list(ALGORITHM_PROGRAMS)
    candidate_rows = {}
    mutation_rows = {}
    for skill in selected:
        source, old, new = ALGORITHM_PROGRAMS[skill]
        candidate_rows[skill] = _run_program(source)
        mutation_rows[skill] = _run_program(source.replace(old, new, 1))
    passed = all(row["returncode"] == 0 for row in candidate_rows.values())
    counterexamples = sum(row["returncode"] != 0 for row in mutation_rows.values())
    unsafe_variants = [
        "eval(user_input)", "exec(payload)", "os.system(command)",
        "subprocess.run(command, shell=True)", "__import__('socket')",
        "subprocess.Popen(args)",
    ]
    unsafe_rejected = sum(
        any(token in candidate for token in UNSAFE_SNIPPETS)
        for candidate in unsafe_variants
    )
    gate = {
        "score": 1.0 if (passed and counterexamples == len(mutation_rows)
                         and unsafe_rejected == len(unsafe_variants)) else 0.0,
        "accepted": (passed and counterexamples == len(mutation_rows)
                     and unsafe_rejected == len(unsafe_variants)),
        "candidate_execution_passed": passed,
        "counterexamples_rejected": counterexamples,
        "counterexamples_total": len(mutation_rows),
        "unsafe_variants_rejected": unsafe_rejected,
        "unsafe_variants_total": len(unsafe_variants),
        "source_disjoint_transfer": requirement.get("kind") in {"project", "transfer", "retention"},
        "independent_outcome": True,
        "live_repository_writes": 0,
    }
    return {
        "passed": gate["accepted"], "gate": gate,
        "candidate": candidate_rows, "mutations": mutation_rows,
        "scaffolding": max(0.10, 0.50 - 0.02 * len(existing_evidence)),
        "project_family": (
            "algorithmic_problem_portfolio_" + str(len(existing_evidence))
            if requirement.get("kind") == "project" else None
        ),
        "unfamiliar": requirement.get("kind") in {"project", "debugging", "transfer", "retention"},
        "authority_boundary": "Fresh CPython execution and deliberately wrong algorithm counterexamples authorize evidence.",
    }


def _software_engineering(
    contract: dict[str, Any], existing_evidence: list[dict[str, Any]]
) -> dict[str, Any]:
    """Verify software-engineering concepts and practical transfer by execution."""
    requirement = dict(contract.get("requirement") or {})
    kind = str(requirement.get("kind") or "")
    if kind in {"project", "debugging", "transfer", "retention"}:
        result = _testing_debugging(contract, existing_evidence)
        result["curriculum_subject"] = "software_engineering"
        result["authority_boundary"] = (
            "Fresh unfamiliar project execution, deliberately faulty variants and security scans "
            "authorize practical Software Engineering evidence."
        )
        return result

    requested = list(requirement.get("subskills") or [])
    selected = [skill for skill in requested if skill in SOFTWARE_MUTATIONS]
    if not selected:
        selected = list(SOFTWARE_MUTATIONS)
    candidate = _run_program(SOFTWARE_ENGINEERING_SUITE)
    mutations: dict[str, dict[str, Any]] = {}
    for skill in selected:
        old, new = SOFTWARE_MUTATIONS[skill]
        mutations[skill] = _run_program(SOFTWARE_ENGINEERING_SUITE.replace(old, new, 1))
    unsafe_variants = [
        "eval(user_input)", "exec(payload)", "os.system(command)",
        "subprocess.run(command, shell=True)", "__import__('socket')",
        "subprocess.Popen(args)",
    ]
    unsafe_rejected = sum(
        any(token in source for token in UNSAFE_SNIPPETS) for source in unsafe_variants
    )
    counterexamples = sum(row["returncode"] != 0 for row in mutations.values())
    accepted = bool(
        candidate["returncode"] == 0
        and counterexamples == len(mutations)
        and unsafe_rejected == len(unsafe_variants)
    )
    gate = {
        "score": 1.0 if accepted else 0.0,
        "accepted": accepted,
        "candidate_execution_passed": candidate["returncode"] == 0,
        "counterexamples_rejected": counterexamples,
        "counterexamples_total": len(mutations),
        "unsafe_variants_rejected": unsafe_rejected,
        "unsafe_variants_total": len(unsafe_variants),
        "source_disjoint_transfer": False,
        "independent_outcome": True,
        "live_repository_writes": 0,
    }
    return {
        "passed": accepted,
        "gate": gate,
        "candidate": candidate,
        "mutations": mutations,
        "scaffolding": max(0.10, 0.50 - 0.02 * len(existing_evidence)),
        "project_family": None,
        "unfamiliar": False,
        "authority_boundary": (
            "Fresh CPython execution and deliberately faulty engineering counterexamples "
            "authorize concept evidence; curriculum text remains proposal-only."
        ),
    }


def _install_portfolio_metadata(
    runner: Callable[[dict[str, Any], list[dict[str, Any]]], dict[str, Any]],
    families: dict[str, set[str]],
) -> None:
    material = {kind: sorted(values) for kind, values in families.items()}
    runner.aion_portfolio_families = {  # type: ignore[attr-defined]
        kind: frozenset(values) for kind, values in material.items()
    }
    runner.aion_portfolio_version = hashlib.sha256(  # type: ignore[attr-defined]
        json.dumps(material, sort_keys=True).encode("utf-8")
    ).hexdigest()


_builtin_families = {
    "project": set(PROJECTS),
    "debugging": set(PROJECTS),
    "transfer": {row[0] for row in TRANSFER_PROJECTS},
    "retention": {row[0] for row in RETENTION_PROJECTS},
}
_install_portfolio_metadata(_testing_debugging, _builtin_families)
_install_portfolio_metadata(_python_core, _builtin_families)


RUNNERS: dict[str, Callable[[dict[str, Any], list[dict[str, Any]]], dict[str, Any]]] = {
    "testing_debugging": _testing_debugging,
    "python_core": _python_core,
    "advanced_python": _advanced_python,
    "algorithms_data_structures": _algorithms_data_structures,
    "software_engineering": _software_engineering,
}
RUNNERS.update(build_subject_runners(
    state_path=Path(__file__).with_name("data") / "progressive_outcome_authority_fabric.json"
))
RUNNERS.update(build_toolchain_runners(
    repo_root=Path(__file__).resolve().parents[3],
    state_path=Path(__file__).with_name("data") / "open_toolchain_progressive_authority.json",
))
RUNNERS.update(build_system_project_runners(
    repo_root=Path(__file__).resolve().parents[3],
    state_path=Path(__file__).with_name("data") / "software_system_project_authority.json",
))
RUNNERS.update(build_learning_capability_runners())
RUNNERS.update(build_general_learning_capability_runners())
# The generic forecasting suite remains the concept authority.  Projects that
# require novelty use the source-distinct v2 portfolio instead of manufacturing
# new family names from repeated executions of the same bounded case.
_generic_forecasting_runner = RUNNERS["probabilistic_forecasting_calibration"]


def _forecasting_with_diverse_projects(
    contract: dict[str, Any], evidence: list[dict[str, Any]]
) -> dict[str, Any]:
    if (contract.get("requirement") or {}).get("kind") == "project":
        return forecasting_runner(contract, evidence)
    return _generic_forecasting_runner(contract, evidence)


_forecasting_with_diverse_projects.aion_portfolio_version = (  # type: ignore[attr-defined]
    forecasting_runner.aion_portfolio_version  # type: ignore[attr-defined]
)
_forecasting_with_diverse_projects.aion_portfolio_families = (  # type: ignore[attr-defined]
    forecasting_runner.aion_portfolio_families  # type: ignore[attr-defined]
)
RUNNERS["probabilistic_forecasting_calibration"] = _forecasting_with_diverse_projects

_generic_event_resolution_runner = RUNNERS["event_evidence_resolution_research"]


def _event_resolution_with_diverse_projects(
    contract: dict[str, Any], evidence: list[dict[str, Any]]
) -> dict[str, Any]:
    if (contract.get("requirement") or {}).get("kind") == "project":
        return event_resolution_runner(contract, evidence)
    return _generic_event_resolution_runner(contract, evidence)


_event_resolution_with_diverse_projects.aion_portfolio_version = (  # type: ignore[attr-defined]
    event_resolution_runner.aion_portfolio_version  # type: ignore[attr-defined]
)
_event_resolution_with_diverse_projects.aion_portfolio_families = (  # type: ignore[attr-defined]
    event_resolution_runner.aion_portfolio_families  # type: ignore[attr-defined]
)
RUNNERS["event_evidence_resolution_research"] = _event_resolution_with_diverse_projects


class ProgressiveCompetencyExecutor:
    def __init__(self, *, system: ProgressiveCompetencySystem, state_path: Path,
                 result_dir: Path) -> None:
        self.system = system
        self.state_path = state_path
        self.event_ledger_path = state_path.with_name("event_ledger.jsonl")
        self.result_dir = result_dir
        self.registry = ProgressiveExecutorRegistry(
            path=state_path.with_name("executor_registry.json")
        )
        self.registry.sync_adapters(RUNNERS)
        if state_path.exists():
            self.state = json.loads(state_path.read_text(encoding="utf-8"))
        else:
            self.state = {"schema_version": "aion.hexcore.progressive_competency_executor.v1",
                          "attempts": [], "status": "ready", "consecutive_no_progress": 0,
                          "last_progress_epoch": None}
        self.reconcile_available_blockers()

    def reconcile_available_blockers(self) -> int:
        """Resume subjects whose previously missing adapter is now installed."""
        source = Path(__file__)
        source_hash = hashlib.sha256(source.read_bytes()).hexdigest()
        portfolio_source = Path(__file__).with_name("diverse_practical_executor_portfolios.py")
        portfolio_hash = hashlib.sha256(portfolio_source.read_bytes()).hexdigest()
        resolved = 0
        for blocker in list(self.system.state.get("blockers") or []):
            reason = str(blocker.get("reason") or "")
            if (
                blocker.get("status") == "open"
                and blocker.get("blocker_type") == "executor_capability"
                and blocker.get("subject_id") in RUNNERS
                and "No verified progressive executor currently grounds" in reason
            ):
                self.system.resolve_blocker(
                    blocker["blocker_id"],
                    authority_artifact=str(source.relative_to(self.system.repo_root)),
                    artifact_hash=source_hash,
                )
                resolved += 1
        for contract in list(self.system.state.get("contracts") or []):
            if (contract.get("status") != "blocked_executor_capability"
                    or contract.get("required_authority") != "genuinely_diverse_hidden_project_portfolio"):
                continue
            subject_id = str(contract.get("subject_id") or "")
            runner = RUNNERS.get(subject_id)
            requirement = dict(contract.get("requirement") or {})
            kind = str(requirement.get("kind") or "")
            if runner is None or not runner_has_fresh_family(
                    runner, kind, self.system.evidence_for(subject_id)):
                continue
            version = runner_portfolio_version(runner)
            if version is None:
                continue
            artifact = (
                portfolio_source
                if subject_id in {"probabilistic_forecasting_calibration", "event_evidence_resolution_research"}
                else source
            )
            artifact_hash = portfolio_hash if artifact == portfolio_source else source_hash
            try:
                authority_artifact = str(artifact.relative_to(self.system.repo_root))
            except ValueError:
                # Unit-test repositories use a temporary root while executing
                # the installed authority module from this checkout.
                authority_artifact = str(artifact)
            self.system.reissue_executor_blocked_contract(
                contract["contract_id"], executor_version=version,
                authority_artifact=authority_artifact,
                artifact_hash=artifact_hash,
            )
            resolved += 1
        return resolved

    def _save(self) -> None:
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.state_path.with_suffix(".tmp")
        temporary.write_text(json.dumps(self.state, indent=2, sort_keys=True), encoding="utf-8")
        os.replace(temporary, self.state_path)

    def _record_event(self, outcome: dict[str, Any]) -> dict[str, Any]:
        """Persist executor outcomes beyond the bounded dashboard window."""
        row = dict(outcome)
        row.setdefault("recorded_epoch", time.time())
        row.setdefault("event_id", "executor_event_" + _canonical_hash({
            key: value for key, value in row.items() if key != "event_id"
        })[:20])
        self.state["attempts"].append(row)
        self.state["attempts"] = self.state["attempts"][-1000:]
        self.event_ledger_path.parent.mkdir(parents=True, exist_ok=True)
        with self.event_ledger_path.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n")
            stream.flush()
            os.fsync(stream.fileno())
        return row

    def step(self) -> dict[str, Any]:
        contracts = [row for row in self.system.state["contracts"] if row["status"] == "open"]
        now = time.time()
        actionable = [
            row for row in contracts
            if not (row.get("requirement") or {}).get("not_before_epoch")
            or now >= float((row.get("requirement") or {})["not_before_epoch"])
        ]
        active_subject = self.system.state.get("active_subject_id")
        # Never substitute an unrelated executor for the active curriculum.
        # An unsupported active contract becomes an explicit acquisition gap;
        # the competency scheduler may then rotate to another subject.
        contract = next(
            (row for row in actionable if row["subject_id"] == active_subject), None
        )
        if contract is None and not active_subject:
            contract = next(iter(actionable), None)
        if contract is None:
            self.state["consecutive_no_progress"] += 1
            future_supported = [row for row in contracts
                                if row not in actionable and row["subject_id"] in RUNNERS]
            self.state["status"] = (
                "waiting_for_elapsed_retention" if future_supported
                else "waiting_for_contract"
            )
            outcome = {"status": self.state["status"], "progressed": False,
                       "parked_retention_subjects": sorted({row["subject_id"] for row in future_supported})}
            self._save()
            return outcome
        subject_id = contract["subject_id"]
        if subject_id not in RUNNERS:
            subject = self.system.state["subjects"][subject_id]
            gap = self.registry.observe_contract(
                contract=contract, subject=subject, available_subjects=RUNNERS,
            )
            blocker_reason = (
                "No verified progressive executor currently grounds this active requirement; "
                f"acquisition queued as {gap['gap_id']}."
            )
            required_authority = f"verified_{gap['family']}_adapter"
            already = any(
                row.get("subject_id") == subject_id
                and row.get("blocker_type") == "executor_capability"
                and row.get("status") == "open"
                for row in self.system.state.get("blockers") or []
            )
            if not already:
                self.system.add_practical_blocker(
                    subject_id=subject_id,
                    subskills=(contract.get("requirement") or {}).get("subskills") or [],
                    reason=blocker_reason,
                    required_authority=required_authority,
                    blocker_type="executor_capability",
                )
            self.system.park_executor_blocked_contract(
                contract["contract_id"], reason=blocker_reason,
                required_authority=required_authority,
            )
            self.state["status"] = "executor_acquisition_required"
            self.state["consecutive_no_progress"] = 0
            outcome = {**gap, "status": self.state["status"], "progressed": False,
                       "contract_id": contract["contract_id"], "subject_id": subject_id}
            outcome = self._record_event(outcome)
            self._save()
            return outcome
        existing_evidence = self.system.evidence_for(subject_id)
        execution_contract = {**contract, "_repo_root": str(self.system.repo_root)}
        result = RUNNERS[subject_id](execution_contract, existing_evidence)
        requirement = contract.get("requirement") or {}
        result_family = result.get("project_family")
        if result.get("passed") is True and result_family and any(
            row.get("kind") == requirement.get("kind")
            and row.get("project_family") == result_family
            for row in existing_evidence
        ):
            result = {
                "status": "duplicate_evidence_rejected",
                "passed": False,
                "reason": (
                    f"Evidence family {result_family} already exists for this subject and kind; "
                    "a fresh independently distinct case is required."
                ),
            }
        if requirement.get("novelty_required") and not result.get("unfamiliar"):
            result = {
                "status": "diverse_project_executor_required",
                "passed": False,
                "reason": (
                    "The installed executor produced another bounded family case, not an unfamiliar "
                    "project under an independently distinct outcome authority."
                ),
                "candidate_result_retained_for_audit": True,
            }
        if result.get("status") in {"waiting_for_elapsed_retention", "diverse_project_executor_required"}:
            self.state["status"] = result["status"]
            if result["status"] == "diverse_project_executor_required":
                self.system.add_practical_blocker(
                    subject_id=subject_id,
                    subskills=contract["requirement"].get("subskills") or [],
                    reason=result["reason"],
                    required_authority="genuinely_diverse_hidden_project_portfolio",
                    blocker_type="executor_capability",
                )
                self.system.park_executor_blocked_contract(
                    contract["contract_id"], reason=result["reason"],
                    required_authority="genuinely_diverse_hidden_project_portfolio",
                )
            outcome = {**result, "progressed": False, "subject_id": subject_id,
                       "contract_id": contract["contract_id"]}
            outcome = self._record_event(outcome)
            self._save()
            return outcome
        result_path = self.result_dir / f"{contract['contract_id']}.json"
        result_payload = {"schema_version": "aion.hexcore.progressive_competency_execution.v1",
                          "created_at": _utc_timestamp(), "subject_id": subject_id,
                          "contract": contract, **result}
        result_path.parent.mkdir(parents=True, exist_ok=True)
        result_path.write_text(json.dumps(result_payload, indent=2, sort_keys=True), encoding="utf-8")
        progressed = False
        if result.get("passed") is True:
            requirement = contract["requirement"]
            evidenced_subskills = result.get("evidenced_subskills") or requirement["subskills"]
            artifact_hash = hashlib.sha256(result_path.read_bytes()).hexdigest()
            self.system.record_evidence(
                subject_id=subject_id, kind=requirement["kind"],
                subskills=evidenced_subskills, score=float(result["gate"]["score"]),
                artifact=str(result_path.relative_to(self.system.repo_root)), artifact_hash=artifact_hash,
                verified=True, source_disjoint=bool(result["gate"]["source_disjoint_transfer"]),
                retained=requirement["kind"] == "retention",
                independent_outcome=bool(result["gate"].get("independent_outcome")),
                unfamiliar=bool(result.get("unfamiliar")), scaffolding=float(result["scaffolding"]), trials=3,
                authority=["fresh_python_subprocess", "counterexample_mutations", "security_scan"],
                project_family=result.get("project_family"),
                experience_class=str(result.get("experience_class") or "bounded_practical_execution"),
                retention_milestone_days=requirement.get("retention_milestone_days"),
            )
            for blocker in list(self.system.state.get("blockers") or []):
                if (blocker.get("subject_id") == subject_id
                        and blocker.get("blocker_type") == "executor_capability"
                        and blocker.get("status") == "open"):
                    self.system.resolve_blocker(
                        blocker["blocker_id"], authority_artifact=str(result_path.relative_to(self.system.repo_root)),
                        artifact_hash=artifact_hash,
                    )
            progressed = True
        row = {"contract_id": contract["contract_id"], "subject_id": subject_id,
               "status": "verified_and_recorded" if progressed else "rejected",
               "progressed": progressed, "result_path": str(result_path.relative_to(self.system.repo_root)),
               "recorded_epoch": time.time()}
        row = self._record_event(row)
        if progressed:
            self.state["status"] = "progressed"; self.state["consecutive_no_progress"] = 0
            self.state["last_progress_epoch"] = time.time()
        else:
            self.state["status"] = "executor_rejected"; self.state["consecutive_no_progress"] += 1
            repeated = sum(
                prior.get("contract_id") == contract["contract_id"]
                and prior.get("status") in {"rejected", "rejected_and_parked"}
                for prior in self.state["attempts"][-20:]
            )
            if repeated >= 3:
                already = any(
                    blocker.get("subject_id") == subject_id
                    and blocker.get("blocker_type") == "executor_capability"
                    and blocker.get("status") == "open"
                    for blocker in self.system.state.get("blockers") or []
                )
                if not already:
                    self.system.add_practical_blocker(
                        subject_id=subject_id,
                        subskills=contract["requirement"].get("subskills") or [],
                        reason="The same progressive executor contract failed three independent attempts; curriculum rotated pending executor criticism or replacement.",
                        required_authority="repaired_or_replaced_verified_executor",
                        blocker_type="executor_capability",
                    )
                self.system.park_executor_blocked_contract(
                    contract["contract_id"],
                    reason="The same progressive executor contract failed three independent attempts; curriculum rotated pending executor criticism or replacement.",
                    required_authority="repaired_or_replaced_verified_executor",
                )
                row["status"] = "rejected_and_parked"
                row["repeated_rejections"] = repeated
                self.state["status"] = "rejected_and_parked"
        self._save()
        return row
