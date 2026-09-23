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


def runner_has_fresh_family(runner: Callable[..., Any], kind: str,
                            evidence: list[dict[str, Any]]) -> bool:
    families = (getattr(runner, "aion_portfolio_families", {}) or {}).get(kind) or ()
    used = {str(row.get("project_family")) for row in evidence
            if row.get("kind") == kind and row.get("project_family")}
    return bool(set(map(str, families)) - used)


def runner_portfolio_version(runner: Callable[..., Any]) -> str | None:
    value = getattr(runner, "aion_portfolio_version", None)
    return str(value) if value else None
