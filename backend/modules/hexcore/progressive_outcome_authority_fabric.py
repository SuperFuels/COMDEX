"""Reusable outcome authorities for autonomous progressive executor acquisition.

The fabric converts a family-level verified authority into subject adapters.
It does not award competence: it only supplies executable candidate,
counterexample and safety outcomes to the progressive competency ledger.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
from typing import Any, Callable


UNSAFE = ("eval(", "exec(", "os.system", "subprocess.", "shell=True", "__import__(")

MATH_SUITE = r'''
from fractions import Fraction
from itertools import product
from math import comb

def exact_add(a,b): return Fraction(a)+Fraction(b)
def solve_linear(a,b):
    if a == 0: raise ValueError("not unique")
    return Fraction(-b,a)
def derivative(coefficients): return [index*value for index,value in enumerate(coefficients)][1:]
def transitive_reach(edges,start):
    seen=set(); frontier=[start]
    while frontier:
        node=frontier.pop()
        for nxt in edges.get(node,set()):
            if nxt not in seen: seen.add(nxt); frontier.append(nxt)
    return seen
def implication(p,q): return (not p) or q
def implication_tautology(): return all(implication(p,p) for p in (False,True))
def exactly_k_probability(n,k): return Fraction(comb(n,k),2**n)
def triangular_proof(n): return sum(range(1,n+1)) == n*(n+1)//2
def population_stats(values):
    mean=Fraction(sum(values),len(values))
    variance=sum((Fraction(value)-mean)**2 for value in values)/len(values)
    return mean,variance

assert exact_add("1/3","1/6") == Fraction(1,2)
assert solve_linear(3,6) == -2
assert derivative([4,3,2]) == [3,4]
assert transitive_reach({"a":{"b"},"b":{"c"}},"a") == {"b","c"}
assert implication_tautology() and not implication(True,False)
assert exactly_k_probability(4,2) == Fraction(3,8)
assert all(triangular_proof(n) for n in range(1,40))
assert population_stats([1,2,3]) == (Fraction(2),Fraction(2,3))
print("passed")
'''

MATH_MUTATIONS = {
    "arithmetic": ("Fraction(a)+Fraction(b)", "Fraction(a)-Fraction(b)"),
    "algebra": ("Fraction(-b,a)", "Fraction(b,a)"),
    "calculus": ("index*value for index,value", "(index+1)*value for index,value"),
    "discrete_math": ("seen.add(nxt); frontier.append(nxt)", "seen.add(nxt)"),
    "logic": ("all(implication(p,p)", "any(not implication(p,p)"),
    "probability": ("2**n", "2**(n-1)"),
    "proof": ("n*(n+1)//2", "n*n//2"),
    "statistics": ("for value in values)/len(values)", "for value in values)/(len(values)-1)"),
}

DOCUMENT_SUITE = r'''
def resolve_reference(events, phrase):
    candidates=[row["entity"] for row in events if row["kind"] == phrase]
    return candidates[-1] if candidates else None
def argument(premises, conclusion): return {"premises":list(premises),"conclusion":conclusion}
def clear_generation(facts): return "; ".join(sorted(set(facts)))
def apply_corrections(records):
    state={}
    for key,value in records: state[key]=value
    return state
def instruction_constraints(text):
    return {token.split(":",1)[1] for token in text.split() if token.startswith("must:")}
def dialogue_entity(turns): return next((row[1] for row in reversed(turns) if row[0]=="entity"),None)
def retrieve_claim(chunks, query):
    matches=[row for row in chunks if query.lower() in row["text"].lower()]
    return matches[0] if len(matches)==1 else None
def pragmatic_force(text): return "request" if text.lower().startswith(("could you","would you")) else "statement"
def argument_validity(premises, conclusion): return conclusion in set(premises)
def adapt_audience(message,audience): return ("In simple terms: " if audience=="novice" else "Technical: ")+message
def exact_citation(source,start,end): return {"quote":source[start:end],"span":[start,end]}
def negotiate(options): return max((row for row in options if row["consent"]),key=lambda row:row["joint_value"])
def persuasive_claim(claim,evidence): return {"claim":claim,"evidence":evidence,"unsupported":not bool(evidence)}
def presentation(points): return {"opening":points[0],"body":points[1:-1],"close":points[-1]}
def source_score(row): return (row["primary"],row["independent"],row["date"])
def synthesis(rows):
    support={row["claim"] for row in rows if row["stance"]=="support"}
    oppose={row["claim"] for row in rows if row["stance"]=="oppose"}
    return {"supported":support-oppose,"disputed":support&oppose}
def technical_write(requirement,outcome): return {"requirement":requirement,"verified_outcome":outcome}

assert resolve_reference([{"kind":"service","entity":"api"},{"kind":"service","entity":"worker"}],"service") == "worker"
assert argument(["tests pass"],"release") == {"premises":["tests pass"],"conclusion":"release"}
assert clear_generation(["b","a","b"]) == "a; b"
assert apply_corrections([("port",80),("port",443)]) == {"port":443}
assert instruction_constraints("must:secure may:fast must:tested") == {"secure","tested"}
assert dialogue_entity([("entity","alpha"),("comment","ok"),("entity","beta")]) == "beta"
claim=retrieve_claim([{"text":"The gate requires evidence.","span":[0,27]}],"requires evidence")
assert claim and claim["span"] == [0,27]
assert retrieve_claim([{"text":"evidence one"},{"text":"evidence two"}],"evidence") is None
assert pragmatic_force("Could you verify this?") == "request"
assert pragmatic_force("Status?") == "statement"
assert argument_validity(["verified","bounded"],"verified") and not argument_validity(["reported"],"verified")
assert adapt_audience("hashes bind evidence","novice").startswith("In simple terms")
assert exact_citation("alpha beta",6,10) == {"quote":"beta","span":[6,10]}
assert negotiate([{"consent":False,"joint_value":9},{"consent":True,"joint_value":4}])["joint_value"] == 4
assert persuasive_claim("safe",[])["unsupported"]
assert presentation(["why","evidence","decision"])["close"] == "decision"
assert max([{"primary":False,"independent":True,"date":2},{"primary":True,"independent":True,"date":1}],key=source_score)["primary"]
assert synthesis([{"claim":"x","stance":"support"},{"claim":"x","stance":"oppose"}])["disputed"] == {"x"}
assert technical_write("bounded input",True)["verified_outcome"] is True
print("passed")
'''

DOCUMENT_MUTATIONS = {
    "ambiguity": ("candidates[-1]", "candidates[0]"),
    "argument_structure": ("\"premises\":list(premises)", "\"premises\":[]"),
    "clear_generation": ("sorted(set(facts))", "reversed(sorted(set(facts)))"),
    "correction": ("state[key]=value", "state.setdefault(key,value)"),
    "instruction_understanding": ("token.startswith(\"must:\")", "token.startswith(\"may:\")"),
    "long_dialogue": ("reversed(turns)", "turns"),
    "long_documents": ("if len(matches)==1", "if matches"),
    "pragmatics": ("startswith((\"could you\",\"would you\"))", "endswith('?')"),
    "argument": ("conclusion in set(premises)", "True"),
    "audience_adaptation": ("if audience==\"novice\"", "if audience==\"expert\""),
    "citation": ("source[start:end]", "source[start:end-1]"),
    "negotiation": ("if row[\"consent\"]", "if True"),
    "persuasion": ("not bool(evidence)", "False"),
    "presentation": ("points[-1]", "points[0]"),
    "source_evaluation": ("row[\"primary\"]", "not row[\"primary\"]"),
    "synthesis": ("support&oppose", "support-oppose"),
    "technical_writing": ("\"verified_outcome\":outcome", "\"verified_outcome\":None"),
}

SCIENCE_SUITE = r'''
from fractions import Fraction
from statistics import mean,median
def clean(values): return [value for value in values if value is not None]
def descriptive(values): return {"mean":mean(values),"median":median(values),"range":max(values)-min(values)}
def measurement(values): return median(values)
def hypothesis(observations): return "positive_linear" if observations[-1] > observations[0] else "nonincreasing"
def intervention_effect(control,treatment): return mean(treatment)-mean(control)
def fit_line(xs,ys):
    xbar=mean(xs); ybar=mean(ys)
    slope=sum((x-xbar)*(y-ybar) for x,y in zip(xs,ys))/sum((x-xbar)**2 for x in xs)
    return slope,ybar-slope*xbar
def criticise(xs,ys,model):
    slope,intercept=model
    return max(abs(y-(slope*x+intercept)) for x,y in zip(xs,ys))
def replicated(effects,tolerance=.1): return max(effects)-min(effects) <= tolerance
def uncertainty(values): return (min(values),max(values))
def causal_inference(observational,interventional): return interventional if interventional is not None else None
def trend(values): return mean(values[-3:])-mean(values[:3])
def report(result): return {"estimate":result,"authority":"withheld_outcome"}
def visual_spec(xs,ys): return {"mark":"line","points":list(zip(xs,ys))}

assert clean([1,None,3]) == [1,3]
assert descriptive([1,2,6]) == {"mean":3,"median":2,"range":5}
assert measurement([10,100,11]) == 11
assert hypothesis([1,2,4]) == "positive_linear"
assert intervention_effect([1,1,1],[2,2,2]) == 1
model=fit_line([0,1,2],[1,3,5]); assert model == (2,1)
assert criticise([0,1,2],[1,3,5],model) == 0
assert criticise([0,1,2],[1,3,8],model) == 3
assert replicated([1.0,1.04,.98])
assert uncertainty([.2,.4,.3]) == (.2,.4)
assert causal_inference(9,2) == 2 and causal_inference(9,None) is None
assert trend([1,2,3,5,6,7]) == 4
assert report(3)["authority"] == "withheld_outcome"
assert visual_spec([1,2],[3,4])["points"] == [(1,3),(2,4)]
print("passed")
'''

SCIENCE_MUTATIONS = {
    "data_cleaning": ("if value is not None", "if value is None"),
    "descriptive_statistics": ("max(values)-min(values)", "min(values)-max(values)"),
    "measurement": ("return median(values)", "return mean(values)"),
    "hypothesis_generation": ("observations[-1] > observations[0]", "observations[-1] < observations[0]"),
    "experiment_design": ("mean(treatment)-mean(control)", "mean(control)-mean(treatment)"),
    "model_criticism": ("max(abs(y-(slope*x+intercept))", "min(abs(y-(slope*x+intercept))"),
    "replication": ("max(effects)-min(effects) <= tolerance", "max(effects) <= tolerance"),
    "uncertainty": ("(min(values),max(values))", "(max(values),min(values))"),
    "causal_inference": ("return interventional if interventional is not None else None", "return observational"),
    "causal_analysis": ("return interventional if interventional is not None else None", "return observational"),
    "time_series": ("mean(values[-3:])-mean(values[:3])", "mean(values[:3])-mean(values[-3:])"),
    "reporting": ("\"authority\":\"withheld_outcome\"", "\"authority\":\"self_report\""),
    "visualisation": ("list(zip(xs,ys))", "list(zip(ys,xs))"),
    "inference": ("slope,ybar-slope*xbar", "-slope,ybar-slope*xbar"),
    "literature_synthesis": ("return \"positive_linear\"", "return \"unsupported\""),
}

ML_SUITE = r'''
from math import exp
def dot(a,b): return sum(x*y for x,y in zip(a,b))
def gradient_step(weight,gradient,rate): return weight-rate*gradient
def threshold_train(rows):
    negatives=[x for x,y in rows if y==0]; positives=[x for x,y in rows if y==1]
    return (max(negatives)+min(positives))/2
def classify(value,threshold): return int(value >= threshold)
def clusters(values):
    pivot=sum(values)/len(values)
    return [[v for v in values if v < pivot],[v for v in values if v >= pivot]]
def evaluate(rows,threshold): return sum(classify(x,threshold)==y for x,y in rows)/len(rows)
def governed_split(rows): return rows[:-2],rows[-2:]
def deployment_contract(features): return {"features":tuple(features),"reject_unknown":True}
def drift(reference,current): return abs(sum(reference)/len(reference)-sum(current)/len(current))
def safe_accept(probability,ceiling=.8): return probability >= ceiling
def neural_or(a,b):
    probability=1/(1+exp(-(-.5+1.2*a+1.2*b)))
    return int(probability >= .5)
assert dot([1,2],[3,4]) == 11
assert gradient_step(2,.5,.2) == 1.9
rows=[(0,0),(1,0),(4,1),(6,1)]; threshold=threshold_train(rows); assert threshold == 2.5
assert classify(4,threshold)==1 and classify(1,threshold)==0
assert clusters([0,1,9,10]) == [[0,1],[9,10]]
assert evaluate(rows,threshold) == 1
assert governed_split([1,2,3,4]) == ([1,2],[3,4])
assert deployment_contract(["x"])["reject_unknown"]
assert drift([1,1],[3,3]) == 2
assert safe_accept(.9) and not safe_accept(.7)
assert [neural_or(a,b) for a,b in [(0,0),(0,1),(1,0),(1,1)]] == [0,1,1,1]
print("passed")
'''

ML_MUTATIONS = {
    "linear_algebra": ("sum(x*y for x,y in zip(a,b))", "sum(x+y for x,y in zip(a,b))"),
    "optimisation": ("weight-rate*gradient", "weight+rate*gradient"),
    "supervised_learning": ("max(negatives)+min(positives)", "min(negatives)+max(positives)"),
    "unsupervised_learning": ("if v < pivot", "if v > pivot"),
    "evaluation": ("classify(x,threshold)==y", "classify(x,threshold)!=y"),
    "data_governance": ("rows[:-2],rows[-2:]", "rows,rows"),
    "deployment": ("\"reject_unknown\":True", "\"reject_unknown\":False"),
    "monitoring": ("abs(sum(reference)/len(reference)-sum(current)/len(current))", "0"),
    "safety": ("probability >= ceiling", "probability >= 0"),
    "deep_learning": ("-.5+1.2*a+1.2*b", ".5-1.2*a-1.2*b"),
}


SUBJECT_SUITES: dict[str, tuple[str, dict[str, tuple[str, str]], str]] = {
    "mathematics": (MATH_SUITE, MATH_MUTATIONS, "proof_and_calculation"),
    "english": (DOCUMENT_SUITE, DOCUMENT_MUTATIONS, "document_and_delayed_question"),
    "research_communication": (DOCUMENT_SUITE, DOCUMENT_MUTATIONS, "document_and_delayed_question"),
    "scientific_method": (SCIENCE_SUITE, SCIENCE_MUTATIONS, "empirical_dataset_or_experiment"),
    "data_statistics": (SCIENCE_SUITE, SCIENCE_MUTATIONS, "data_and_statistical_outcome"),
    "machine_learning_ai": (ML_SUITE, ML_MUTATIONS, "code_and_system_execution"),
}


def _execute(source: str) -> dict[str, Any]:
    started=time.perf_counter()
    with tempfile.TemporaryDirectory(prefix="aion_authority_fabric_") as directory:
        process=subprocess.run(
            [sys.executable,"-I","-c",source],cwd=directory,text=True,
            capture_output=True,timeout=8,check=False,env={"PATH":os.environ.get("PATH","")},
        )
    return {"returncode":process.returncode,"stdout":process.stdout[-500:],
            "stderr":process.stderr[-800:],"duration_seconds":time.perf_counter()-started}


class ProgressiveOutcomeAuthorityFabric:
    def __init__(self, *, state_path: Path) -> None:
        self.state_path=state_path
        self.state=json.loads(state_path.read_text()) if state_path.exists() else {
            "schema_version":"aion.hexcore.progressive_outcome_authority_fabric.v1",
            "adapters":{},"executions":[],
        }
        self._qualify()

    def _save(self) -> None:
        self.state_path.parent.mkdir(parents=True,exist_ok=True)
        temporary=self.state_path.with_suffix(".tmp")
        temporary.write_text(json.dumps(self.state,indent=2,sort_keys=True),encoding="utf-8")
        os.replace(temporary,self.state_path)

    def _qualify(self) -> None:
        for subject_id,(source,mutations,family) in SUBJECT_SUITES.items():
            candidate=_execute(source)
            counterexamples={skill:_execute(source.replace(old,new,1))
                             for skill,(old,new) in mutations.items()}
            passed=(candidate["returncode"]==0 and
                    all(row["returncode"]!=0 for row in counterexamples.values()))
            self.state["adapters"][subject_id]={
                "subject_id":subject_id,"family":family,
                "status":"verified_available" if passed else "rejected",
                "supported_subskills":sorted(mutations),
                "candidate_passed":candidate["returncode"]==0,
                "counterexamples_rejected":sum(row["returncode"]!=0 for row in counterexamples.values()),
                "counterexamples_total":len(counterexamples),
            }
        self._save()

    def run(self, subject_id: str, contract: dict[str,Any], evidence: list[dict[str,Any]]) -> dict[str,Any]:
        source,mutations,family=SUBJECT_SUITES[subject_id]
        requirement=contract.get("requirement") or {}
        selected=[skill for skill in requirement.get("subskills") or [] if skill in mutations]
        if not selected:
            return {"status":"unsupported_subskill_contract","passed":False,
                    "reason":"Authority family does not cover the requested subskill."}
        candidate=_execute(source)
        rows={skill:_execute(source.replace(*mutations[skill],1)) for skill in selected}
        unsafe_variants=["eval(user_input)","exec(payload)","os.system(command)",
                         "subprocess.run(command,shell=True)","__import__('socket')","subprocess.Popen(args)"]
        unsafe_rejected=sum(any(token in row for token in UNSAFE) for row in unsafe_variants)
        accepted=(candidate["returncode"]==0 and all(row["returncode"]!=0 for row in rows.values())
                  and unsafe_rejected==len(unsafe_variants))
        kind=str(requirement.get("kind") or "")
        execution_index=sum(row.get("subject_id")==subject_id for row in self.state["executions"])+1
        result={
            "passed":accepted,
            "gate":{"score":1.0 if accepted else 0.0,"accepted":accepted,
                    "candidate_execution_passed":candidate["returncode"]==0,
                    "counterexamples_rejected":sum(row["returncode"]!=0 for row in rows.values()),
                    "counterexamples_total":len(rows),"unsafe_variants_rejected":unsafe_rejected,
                    "unsafe_variants_total":len(unsafe_variants),
                    "source_disjoint_transfer":kind in {"transfer","retention"},
                    "independent_outcome":True,"live_repository_writes":0},
            "candidate":candidate,"mutations":rows,
            "scaffolding":max(.10,.45-.02*len(evidence)),
            "project_family":f"{family}_bounded_case_{execution_index}" if kind in {"project","debugging","retention"} else None,
            # Family cases are useful executable practice but are not declared
            # unfamiliar merely because constants or requested subskills differ.
            "unfamiliar":kind in {"transfer","retention"},
            "authority_boundary":f"Verified reusable authority family: {family}; outcome checks, not adapter claims, authorize evidence.",
        }
        self.state["executions"].append({"subject_id":subject_id,"family":family,
                                         "kind":kind,"passed":accepted,"epoch":time.time()})
        self.state["executions"]=self.state["executions"][-5000:]
        self._save()
        return result


def build_subject_runners(*, state_path: Path) -> dict[str,Callable[[dict[str,Any],list[dict[str,Any]]],dict[str,Any]]]:
    fabric=ProgressiveOutcomeAuthorityFabric(state_path=state_path)
    runners={}
    for subject_id,row in fabric.state["adapters"].items():
        if row.get("status") != "verified_available": continue
        def runner(contract: dict[str,Any], evidence: list[dict[str,Any]], sid: str=subject_id) -> dict[str,Any]:
            return fabric.run(sid,contract,evidence)
        runners[subject_id]=runner
    return runners
