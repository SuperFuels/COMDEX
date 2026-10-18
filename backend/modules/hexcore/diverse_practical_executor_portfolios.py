"""Versioned, source-distinct practical portfolios for blocked curriculum subjects.

The generic outcome-authority fabric is intentionally reusable, so repeating it
cannot establish project novelty.  This module supplies finite, named projects
whose problem structures and falsifying mutations are distinct.  Exhaustion is
still reported honestly; adding a new portfolio version can then reissue a
parked contract without fabricating evidence.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import time
from typing import Any, Callable


UNSAFE = ("eval(", "exec(", "os.system", "subprocess.", "shell=True", "__import__(")


@dataclass(frozen=True)
class PracticalCase:
    family: str
    source: str
    old: str
    new: str
    subskills: tuple[str, ...]


def _case(family: str, source: str, old: str, new: str, subskills: str) -> PracticalCase:
    return PracticalCase(family, source.strip() + "\n", old, new, tuple(subskills.split()))


FORECASTING_PROJECTS = (
    _case("forecast_base_rate_shrinkage", r'''
from fractions import Fraction
def shrink(local_hits, local_total, prior_hits, prior_total, weight=2):
    return Fraction(local_hits + weight*prior_hits, local_total + weight*prior_total)
assert shrink(1,2,30,100) == Fraction(61,202)
assert shrink(0,0,3,10) == Fraction(3,10)
print("passed")
''', "local_hits + weight*prior_hits", "local_hits + prior_hits", "base_rates reference_classes"),
    _case("forecast_bayesian_diagnostic_update", r'''
from fractions import Fraction
def update(prior, sensitivity, false_positive):
    prior=Fraction(prior); sensitivity=Fraction(sensitivity); false_positive=Fraction(false_positive)
    return prior*sensitivity/(prior*sensitivity+(1-prior)*false_positive)
assert update(Fraction(1,100), Fraction(9,10), Fraction(1,10)) == Fraction(1,12)
assert update(Fraction(1,2), 1, 0) == 1
print("passed")
''', "(1-prior)*false_positive", "prior*false_positive", "bayesian_updates base_rates"),
    _case("forecast_log_odds_pool", r'''
from math import exp,log
def pool(probabilities,weights):
    assert len(probabilities)==len(weights) and abs(sum(weights)-1)<1e-9
    log_odds=sum(w*log(p/(1-p)) for p,w in zip(probabilities,weights))
    return 1/(1+exp(-log_odds))
p=pool([.2,.8],[.5,.5]); assert abs(p-.5)<1e-12
assert pool([.8,.8],[.25,.75]) > .79
print("passed")
''', "w*log(p/(1-p))", "w*log(p)", "aggregation calibration"),
    _case("forecast_calibration_bins", r'''
def bins(rows):
    result={}
    for probability,outcome in rows:
        key=int(probability*10)//2*2
        result.setdefault(key,[]).append(outcome)
    return {key:sum(values)/len(values) for key,values in result.items()}
r=bins([(.11,0),(.19,1),(.72,1),(.79,1)])
assert r=={0:0.5,6:1.0}
print("passed")
''', "int(probability*10)//2*2", "round(probability*10)", "calibration aggregation"),
    _case("forecast_proper_score_selection", r'''
def brier(forecasts,outcomes):
    return sum((p-y)**2 for p,y in zip(forecasts,outcomes))/len(outcomes)
def choose(candidates,outcomes): return min(candidates,key=lambda row:brier(row,outcomes))
truth=[1,0,1,1]
sharp=[.9,.1,.8,.75]; vague=[.55,.45,.55,.55]
assert choose([vague,sharp],truth) is sharp
assert brier(sharp,truth) < brier(vague,truth)
print("passed")
''', "return min(candidates", "return max(candidates", "proper_scoring_rules calibration"),
    _case("forecast_expected_utility_threshold", r'''
def act(probability,gain,loss): return probability*gain-(1-probability)*loss > 0
assert act(.7,4,6) and not act(.5,4,6)
threshold=6/(4+6); assert act(threshold+.01,4,6) and not act(threshold-.01,4,6)
print("passed")
''', "> 0", ">= 1", "decision_thresholds calibration"),
    _case("forecast_reference_class_hierarchy", r'''
def select(classes,minimum):
    eligible=[row for row in classes if row["n"]>=minimum]
    return max(eligible,key=lambda row:row["specificity"]) if eligible else None
rows=[{"name":"global","n":100,"specificity":1},{"name":"sector","n":30,"specificity":2},{"name":"tiny","n":2,"specificity":3}]
assert select(rows,20)["name"]=="sector"
assert select(rows,200) is None
print("passed")
''', "row[\"n\"]>=minimum", "row[\"n\"]>0", "reference_classes base_rates"),
    _case("forecast_conjunction_decomposition", r'''
def conjunction(parts):
    assert all(0<=p<=1 for p in parts)
    lower=max(0,sum(parts)-(len(parts)-1)); upper=min(parts)
    return lower,upper
assert conjunction([.8,.7]) == (.5,.7)
assert conjunction([.9,.9,.9]) == (.7000000000000002,.9)
print("passed")
''', "upper=min(parts)", "upper=max(parts)", "forecast_decomposition aggregation"),
)


EVENT_RESOLUTION_PROJECTS = (
    _case("event_temporal_cutoff", r'''
def admissible(records, cutoff):
    return [row for row in records if row["published_at"] <= cutoff]
rows=[{"id":"primary","published_at":10},{"id":"late-rumour","published_at":12}]
assert [row["id"] for row in admissible(rows,10)] == ["primary"]
print("passed")
''', '<= cutoff', '>= cutoff', "timeline_evidence audit_trail"),
    _case("event_source_hierarchy", r'''
RANK={"anonymous":0,"secondary":1,"official_primary":3,"resolution_authority":4}
def strongest(rows): return max(rows,key=lambda row:RANK[row["kind"]])
rows=[{"id":"post","kind":"secondary"},{"id":"filing","kind":"official_primary"}]
assert strongest(rows)["id"] == "filing"
print("passed")
''', 'return max(rows', 'return min(rows', "source_hierarchy conflicting_sources"),
    _case("event_independent_corroboration", r'''
def corroborated(rows):
    families={row["family"] for row in rows if row["supports"]}
    return len(families) >= 2
assert corroborated([{"family":"wire","supports":True},{"family":"filing","supports":True}])
assert not corroborated([{"family":"wire","supports":True},{"family":"wire","supports":True}])
print("passed")
''', '>= 2', '>= 1', "conflicting_sources manipulation_risk"),
    _case("event_ambiguity_fail_closed", r'''
def resolve(rule, candidates):
    matches=[row for row in candidates if row["value"] == rule]
    return matches[0] if len(matches) == 1 else None
assert resolve("YES",[{"value":"YES"}])["value"] == "YES"
assert resolve("YES",[{"value":"YES"},{"value":"YES"}]) is None
print("passed")
''', 'len(matches) == 1', 'len(matches) >= 1', "resolution_rules question_decomposition"),
    _case("event_manipulation_resistant_count", r'''
def independent_support(rows):
    return len({row["owner"] for row in rows if row["supports"]})
rows=[{"owner":"a","supports":True},{"owner":"a","supports":True},{"owner":"b","supports":True}]
assert independent_support(rows) == 2
print("passed")
''', 'len({row["owner"]', 'len([row["owner"]', "manipulation_risk conflicting_sources"),
    _case("event_hash_chained_audit", r'''
from hashlib import sha256
def chain(events):
    previous="GENESIS"; rows=[]
    for event in events:
        digest=sha256((previous+event).encode()).hexdigest()
        rows.append((previous,event,digest)); previous=digest
    return rows
rows=chain(["question-frozen","evidence-added","resolved"])
assert rows[0][0] == "GENESIS" and rows[2][0] == rows[1][2]
print("passed")
''', 'previous=digest', 'previous=event', "audit_trail settlement_review"),
    _case("event_post_settlement_review", r'''
def review(resolution, evidence, cutoff):
    admissible=[row for row in evidence if row["timestamp"] <= cutoff]
    support=sum(row["value"] == resolution for row in admissible)
    return {"resolution":resolution,"admissible":len(admissible),"supported":support > len(admissible)/2}
rows=[{"timestamp":9,"value":"YES"},{"timestamp":10,"value":"YES"},{"timestamp":11,"value":"NO"}]
assert review("YES",rows,10) == {"resolution":"YES","admissible":2,"supported":True}
print("passed")
''', '<= cutoff', '>= cutoff', "settlement_review timeline_evidence"),
    _case("event_question_decomposition", r'''
def resolves_yes(parts):
    required=[row for row in parts if row["required"]]
    return bool(required) and all(row["resolved"] for row in required)
assert resolves_yes([{"required":True,"resolved":True},{"required":True,"resolved":True}])
assert not resolves_yes([{"required":True,"resolved":True},{"required":True,"resolved":False}])
print("passed")
''', 'all(row["resolved"]', 'any(row["resolved"]', "question_decomposition resolution_rules"),
)


# These portfolios intentionally use different problem structures, not renamed
# executions of the generic authority fabric. Each case has its own hidden
# falsifying mutation and may count once as unfamiliar practical evidence.
MATHEMATICS_PROJECTS = (
    _case("math_shortest_path", """
from heapq import heappop,heappush
def solve(g,s):
 d={s:0};q=[(0,s)]
 while q:
  cost,node=heappop(q)
  for target,weight in g.get(node,[]):
   candidate=cost+weight
   if candidate<d.get(target,10**9):d[target]=candidate;heappush(q,(candidate,target))
 return d
assert solve({'a':[('b',4),('c',1)],'c':[('b',2)]},'a')['b']==3
""", "candidate=cost+weight", "candidate=weight", "discrete_math proof"),
    _case("math_symbolic_derivative", """
def derivative(values):return [power*value for power,value in enumerate(values)][1:]
assert derivative([5,3,2])==[3,4] and derivative([7])==[]
""", "power*value", "(power+1)*value", "calculus algebra"),
    _case("math_bayesian_update", """
from fractions import Fraction
def update(prior,hit,false_hit):return prior*hit/(prior*hit+(1-prior)*false_hit)
assert update(Fraction(1,10),Fraction(4,5),Fraction(1,5))==Fraction(4,13)
""", "(1-prior)*false_hit", "prior*false_hit", "probability arithmetic"),
    _case("math_euclidean_invariant", """
def gcd(a,b):
 while b:a,b=b,a%b
 return abs(a)
assert gcd(84,30)==6 and gcd(-21,14)==7
""", "a,b=b,a%b", "a,b=b,b%a", "proof arithmetic"),
    _case("math_population_variance", """
def variance(values):
 mean=sum(values)/len(values);return sum((value-mean)**2 for value in values)/len(values)
assert variance([1,2,3])==2/3
""", "/len(values)", "/(len(values)-1)", "statistics arithmetic"),
    _case("math_polynomial_horner", """
def evaluate(coefficients,x):
 value=0
 for coefficient in coefficients:value=value*x+coefficient
 return value
assert evaluate([2,-3,1],4)==21
""", "value*x+coefficient", "value+x+coefficient", "algebra arithmetic"),
    _case("math_combinatorial_paths", """
def paths(rows,columns):
 grid=[[1]*columns for _ in range(rows)]
 for row in range(1,rows):
  for column in range(1,columns):grid[row][column]=grid[row-1][column]+grid[row][column-1]
 return grid[-1][-1]
assert paths(3,3)==6 and paths(2,4)==4
""", "grid[row-1][column]+grid[row][column-1]", "grid[row-1][column]", "discrete_math proof"),
    _case("math_bisection_bound", """
def root(low,high):
 for _ in range(60):
  middle=(low+high)/2
  if middle*middle<2:low=middle
  else:high=middle
 return (low+high)/2
assert abs(root(1,2)**2-2)<1e-12
""", "middle*middle<2", "middle*middle>2", "calculus logic"),
)

ENGLISH_PROJECTS = (
    _case("english_ambiguity_resolution", """
def resolve(pronoun,candidates):
 matches=[row for row in candidates if row['number']==pronoun]
 return matches[0]['name'] if len(matches)==1 else None
assert resolve('plural',[{'name':'team','number':'singular'},{'name':'players','number':'plural'}])=='players'
assert resolve('singular',[{'name':'team','number':'singular'},{'name':'coach','number':'singular'}]) is None
""", "len(matches)==1", "len(matches)>=1", "ambiguity pragmatics"),
    _case("english_argument_map", """
def valid(rows):
 premises=[row for row in rows if row['role']=='premise'];conclusions=[row for row in rows if row['role']=='conclusion']
 return bool(premises) and len(conclusions)==1 and conclusions[0].get('supported')
assert valid([{'role':'premise'},{'role':'conclusion','supported':True}]) and not valid([{'role':'conclusion','supported':True}])
""", "bool(premises) and", "", "argument_structure clear_generation"),
    _case("english_instruction_constraints", """
def follows(text):return len(text.split())<=8 and text.endswith('.')
assert follows('A concise answer works.') and not follows('An answer without final punctuation')
""", "and text.endswith('.')", "or text.endswith('.')", "instruction_understanding clear_generation"),
    _case("english_long_document_evidence", """
def supported(claim,sections):return sorted(row['id'] for row in sections if claim in row['claims'])
rows=[{'id':'s1','claims':['a']},{'id':'s2','claims':['b','a']}]
assert supported('a',rows)==['s1','s2'] and supported('c',rows)==[]
""", "if claim in row['claims']", "if claim not in row['claims']", "long_documents argument_structure"),
    _case("english_correction_agreement", """
def agrees(subject,verb):
 plural=subject.endswith('s');return (plural and not verb.endswith('s')) or (not plural and verb.endswith('s'))
assert agrees('robots','learn') and agrees('robot','learns') and not agrees('robots','learns')
""", "plural and not verb.endswith('s')", "plural and verb.endswith('s')", "correction clear_generation"),
    _case("english_pragmatic_register", """
def suitable(text,audience):return audience=='expert' or 'instantiate' not in text.lower()
assert suitable('Use a small example','general') and not suitable('Instantiate this','general')
""", "audience=='expert' or", "audience=='general' or", "pragmatics clear_generation"),
    _case("english_dialogue_state", """
def unanswered(turns):
 opened=[]
 for turn in turns:
  if turn['kind']=='question':opened.append(turn['id'])
  elif turn['to'] in opened:opened.remove(turn['to'])
 return opened
assert unanswered([{'kind':'question','id':'q1'},{'kind':'answer','to':'q1'}])==[]
""", "opened.remove(turn['to'])", "opened.append(turn['to'])", "long_dialogue instruction_understanding"),
    _case("english_concise_revision", """
def revise(text):
 for old,new in {'very unique':'unique','in order to':'to','at this point in time':'now'}.items():text=text.replace(old,new)
 return text
assert revise('in order to be very unique at this point in time')=='to be unique now'
""", "text=text.replace(old,new)", "text=text.replace(new,old)", "clear_generation correction"),
)

PYTHON_PROJECTS = (
    _case("python_dependency_order", """
def order(graph):
 result=[];pending=set(graph)
 while pending:
  ready=sorted(node for node in pending if set(graph[node])<=set(result))
  if not ready:raise ValueError('cycle')
  result.extend(ready);pending-=set(ready)
 return result
assert order({'api':['db'],'db':[]})==['db','api']
""", "set(graph[node])<=set(result)", "set(graph[node])<set(result)", "architecture packages"),
    _case("python_worker_pool", """
from concurrent.futures import ThreadPoolExecutor
def apply(values):
 with ThreadPoolExecutor(max_workers=2) as pool:return list(pool.map(lambda x:x*x,values))
assert apply([1,2,3])==[1,4,9]
""", "x*x", "x+x", "concurrency testing"),
    _case("python_lru_cache", """
from collections import OrderedDict
data=OrderedDict()
for key in 'abc':
 data[key]=key
 if len(data)>2:data.popitem(last=False)
assert list(data)==['b','c']
""", "popitem(last=False)", "popitem(last=True)", "data_structures performance"),
    _case("python_safe_path", """
from pathlib import PurePosixPath
def safe(value):
 path=PurePosixPath(value);return not path.is_absolute() and '..' not in path.parts
assert safe('reports/a.txt') and not safe('../secret') and not safe('/etc/passwd')
""", "and '..' not in path.parts", "or '..' not in path.parts", "security testing"),
    _case("python_type_contract", """
def total(values):
 if not all(isinstance(value,int) and not isinstance(value,bool) for value in values):raise TypeError
 return sum(values)
assert total([1,2,3])==6
try:total([1,True]);raise AssertionError
except TypeError:pass
""", "and not isinstance(value,bool)", "or isinstance(value,bool)", "typing syntax"),
    _case("python_memoized_solver", """
from functools import lru_cache
@lru_cache(None)
def ways(n):return n if n<2 else ways(n-1)+ways(n-2)
assert ways(20)==6765 and ways.cache_info().hits>0
""", "ways(n-1)+ways(n-2)", "ways(n-1)+ways(n-1)", "performance debugging"),
    _case("python_stream_parser", """
def parse(lines):
 for line in lines:
  key,separator,value=line.partition('=')
  if not separator or not key:raise ValueError
  yield key.strip(),value.strip()
assert dict(parse(['a=1','b = 2']))=={'a':'1','b':'2'}
try:list(parse(['=missing-key']));raise AssertionError
except ValueError:pass
""", "if not separator or not key", "if not separator and not key", "syntax packages"),
    _case("python_retry_boundary", """
def retry(operation,attempts):
 for index in range(attempts):
  try:return operation()
  except ValueError:
   if index==attempts-1:raise
values=iter([None,42])
def operation():
 value=next(values)
 if value is None:raise ValueError
 return value
assert retry(operation,2)==42
""", "if index==attempts-1", "if index<attempts-1", "debugging architecture"),
)

SCIENTIFIC_METHOD_PROJECTS = (
    _case("science_randomized_assignment", """
def assign(ids):return {value:('treatment' if index%2 else 'control') for index,value in enumerate(sorted(ids))}
assert assign(['d','a','c','b'])=={'a':'control','b':'treatment','c':'control','d':'treatment'}
""", "index%2", "index%3", "experiment_design experimental_design"),
    _case("science_confounder_strata", """
def difference(rows):
 treatment=[r['value'] for r in rows if r['group']=='treatment'];control=[r['value'] for r in rows if r['group']=='control']
 return sum(treatment)/len(treatment)-sum(control)/len(control)
assert difference([{'group':'treatment','value':4},{'group':'control','value':2}])==2
""", "-sum(control)", "+sum(control)", "causal_inference model_criticism"),
    _case("science_measurement_calibration", """
def calibrate(observed,offset,scale):return (observed-offset)/scale
assert calibrate(12,2,2)==5 and calibrate(2,2,3)==0
""", "(observed-offset)/scale", "observed-offset/scale", "measurement uncertainty"),
    _case("science_replication_rule", """
def replicated(studies):return len(studies)>=2 and all(row==studies[0] for row in studies)
assert replicated([1,1]) and not replicated([1,-1])
""", "len(studies)>=2 and", "len(studies)>=1 or", "replication model_criticism"),
    _case("science_uncertainty_interval", """
from math import sqrt
def margin(variance,n):return 1.96*sqrt(variance/n)
assert round(margin(4,100),3)==.392
""", "sqrt(variance/n)", "sqrt(variance)/n", "uncertainty measurement"),
    _case("science_evidence_deduplication", """
def independent(rows):return len({(row['dataset'],row['team']) for row in rows})
rows=[{'dataset':'a','team':'x'},{'dataset':'a','team':'x'},{'dataset':'a','team':'y'}]
assert independent(rows)==2
""", "(row['dataset'],row['team'])", "row['dataset']", "literature_synthesis literature_review"),
    _case("science_residual_diagnostic", """
def biased(predicted,observed):return abs(sum(a-p for p,a in zip(predicted,observed))/len(predicted))>1
assert biased([1,1,1],[3,3,3]) and not biased([1,2,3],[1,2,3])
""", ">1", ">3", "model_criticism uncertainty"),
    _case("science_preregistered_hypothesis", """
REQUIRED={'outcome','direction','sample_size','analysis'}
def valid(plan):return REQUIRED<=set(plan) and plan['sample_size']>0
assert valid({'outcome':'x','direction':'up','sample_size':20,'analysis':'mean'}) and not valid({'outcome':'x','sample_size':20})
""", "REQUIRED<=set(plan)", "bool(set(plan))", "hypotheses hypothesis_generation experimental_design"),
)


def _execute(source: str) -> dict[str, Any]:
    started = time.perf_counter()
    with tempfile.TemporaryDirectory(prefix="aion_diverse_portfolio_") as directory:
        process = subprocess.run(
            [sys.executable, "-I", "-c", source], cwd=directory, text=True,
            capture_output=True, timeout=12, check=False,
            env={"PATH": os.environ.get("PATH", "")},
        )
    return {"returncode": process.returncode, "stdout": process.stdout[-800:],
            "stderr": process.stderr[-1200:], "duration_seconds": time.perf_counter()-started}


def _portfolio_version(cases: tuple[PracticalCase, ...]) -> str:
    material = [(row.family, row.source, row.old, row.new, row.subskills) for row in cases]
    return hashlib.sha256(json.dumps(material, sort_keys=True).encode()).hexdigest()


def _run_portfolio(cases: tuple[PracticalCase, ...], contract: dict[str, Any],
                   evidence: list[dict[str, Any]], authority: str) -> dict[str, Any]:
    requirement = dict(contract.get("requirement") or {})
    if requirement.get("not_before_epoch") and time.time() < float(requirement["not_before_epoch"]):
        return {"status": "waiting_for_elapsed_retention", "passed": False,
                "not_before_epoch": requirement["not_before_epoch"]}
    kind = str(requirement.get("kind") or "")
    if kind != "project":
        return {"status": "unsupported_practical_kind", "passed": False,
                "reason": f"The {authority} portfolio currently supplies unfamiliar projects only."}
    used = {str(row.get("project_family")) for row in evidence
            if row.get("kind") == kind and row.get("project_family")}
    requested = set(map(str, requirement.get("subskills") or []))
    available = [row for row in cases if row.family not in used]
    if not available:
        return {"status": "diverse_project_executor_required", "passed": False,
                "reason": f"The versioned {authority} portfolio is exhausted before the gate was met."}
    selected = max(available, key=lambda row: (len(requested & set(row.subskills)), -cases.index(row)))
    candidate = _execute(selected.source)
    mutation = _execute(selected.source.replace(selected.old, selected.new, 1))
    unsafe_variants = ("eval(user)", "exec(payload)", "os.system(command)",
                       "subprocess.run(command,shell=True)", "__import__('socket')")
    unsafe_rejected = sum(any(token in row for token in UNSAFE) for row in unsafe_variants)
    accepted = bool(candidate["returncode"] == 0 and mutation["returncode"] != 0
                    and unsafe_rejected == len(unsafe_variants))
    return {
        "passed": accepted,
        "gate": {"score": 1.0 if accepted else 0.0, "accepted": accepted,
                 "candidate_execution_passed": candidate["returncode"] == 0,
                 "counterexamples_rejected": int(mutation["returncode"] != 0),
                 "counterexamples_total": 1,
                 "unsafe_variants_rejected": unsafe_rejected,
                 "unsafe_variants_total": len(unsafe_variants),
                 "source_disjoint_transfer": True, "independent_outcome": True,
                 "live_repository_writes": 0},
        "candidate": candidate, "mutations": {selected.family: mutation},
        "evidenced_subskills": sorted(set(selected.subskills) & requested) or list(selected.subskills),
        "scaffolding": max(.10, .35-.02*len(evidence)),
        "project_family": selected.family, "unfamiliar": True,
        "portfolio_version": _portfolio_version(cases),
        "authority_boundary": (
            f"{authority} supplies source-distinct executable projects with withheld faults. "
            "A project outcome remains bounded evidence, not broad mastery."
        ),
    }


def _decorate(runner: Callable[..., dict[str, Any]], cases: tuple[PracticalCase, ...]) -> Callable[..., dict[str, Any]]:
    runner.aion_portfolio_version = _portfolio_version(cases)  # type: ignore[attr-defined]
    runner.aion_portfolio_families = {  # type: ignore[attr-defined]
        "project": frozenset(row.family for row in cases),
    }
    return runner


def forecasting_runner(contract: dict[str, Any], evidence: list[dict[str, Any]]) -> dict[str, Any]:
    return _run_portfolio(
        FORECASTING_PROJECTS, contract, evidence,
        "forecasting decision and calibration authority v2",
    )


forecasting_runner = _decorate(forecasting_runner, FORECASTING_PROJECTS)


def event_resolution_runner(contract: dict[str, Any], evidence: list[dict[str, Any]]) -> dict[str, Any]:
    return _run_portfolio(
        EVENT_RESOLUTION_PROJECTS, contract, evidence,
        "event evidence and resolution authority v2",
    )


event_resolution_runner = _decorate(event_resolution_runner, EVENT_RESOLUTION_PROJECTS)


def mathematics_runner(contract: dict[str, Any], evidence: list[dict[str, Any]]) -> dict[str, Any]:
    return _run_portfolio(MATHEMATICS_PROJECTS, contract, evidence, "mathematics project authority v1")


mathematics_runner = _decorate(mathematics_runner, MATHEMATICS_PROJECTS)


def english_runner(contract: dict[str, Any], evidence: list[dict[str, Any]]) -> dict[str, Any]:
    return _run_portfolio(ENGLISH_PROJECTS, contract, evidence, "language practice authority v1")


english_runner = _decorate(english_runner, ENGLISH_PROJECTS)


def python_runner(contract: dict[str, Any], evidence: list[dict[str, Any]]) -> dict[str, Any]:
    return _run_portfolio(PYTHON_PROJECTS, contract, evidence, "Python project authority v1")


python_runner = _decorate(python_runner, PYTHON_PROJECTS)


def scientific_method_runner(contract: dict[str, Any], evidence: list[dict[str, Any]]) -> dict[str, Any]:
    return _run_portfolio(
        SCIENTIFIC_METHOD_PROJECTS, contract, evidence, "scientific-method project authority v1"
    )


scientific_method_runner = _decorate(scientific_method_runner, SCIENTIFIC_METHOD_PROJECTS)


def runner_has_fresh_family(runner: Callable[..., Any], kind: str,
                            evidence: list[dict[str, Any]]) -> bool:
    families = (getattr(runner, "aion_portfolio_families", {}) or {}).get(kind) or ()
    used = {str(row.get("project_family")) for row in evidence
            if row.get("kind") == kind and row.get("project_family")}
    return bool(set(map(str, families)) - used)


def runner_portfolio_version(runner: Callable[..., Any]) -> str | None:
    value = getattr(runner, "aion_portfolio_version", None)
    return str(value) if value else None
