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

MARKETS_SUITE = r'''
from fractions import Fraction

def asset_return(entry, exit): return Fraction(exit-entry, entry)
def loss_averse_utility(gain, loss, aversion=2): return gain-aversion*loss
def forward_payoff(spot, strike): return spot-strike
def limit_order_executes(side, limit, market):
    return market <= limit if side == "buy" else market >= limit
def equal_weight_portfolio(returns): return sum(map(Fraction, returns))/len(returns)
def regulated_order(notional, approved, limit=10_000): return approved and notional <= limit
def position_size(capital, risk_fraction, stop_distance):
    if capital <= 0 or stop_distance <= 0 or not 0 < risk_fraction <= 1: raise ValueError("invalid risk")
    return Fraction(capital)*Fraction(risk_fraction)/Fraction(stop_distance)

assert asset_return(100,110) == Fraction(1,10)
assert loss_averse_utility(5,3) == -1
assert forward_payoff(120,100) == 20
assert limit_order_executes("buy",100,99) and not limit_order_executes("buy",100,101)
assert limit_order_executes("sell",100,101) and not limit_order_executes("sell",100,99)
assert equal_weight_portfolio([Fraction(1,10),Fraction(-1,20)]) == Fraction(1,40)
assert regulated_order(5000,True) and not regulated_order(5000,False) and not regulated_order(15000,True)
assert position_size(10000,Fraction(1,100),5) == 20
try: position_size(10000,Fraction(2,1),5); raise AssertionError("unsafe risk accepted")
except ValueError: pass
print("passed")
'''

MARKETS_MUTATIONS = {
    "assets": ("Fraction(exit-entry, entry)", "Fraction(entry-exit, entry)"),
    "behaviour": ("gain-aversion*loss", "gain+aversion*loss"),
    "derivatives": ("spot-strike", "strike-spot"),
    "market_structure": ("market <= limit if side == \"buy\" else market >= limit",
                         "market >= limit if side == \"buy\" else market <= limit"),
    "portfolio_theory": ("sum(map(Fraction, returns))/len(returns)",
                         "sum(map(Fraction, returns))"),
    "regulation": ("approved and notional <= limit", "approved or notional <= limit"),
    "risk": ("not 0 < risk_fraction <= 1", "not risk_fraction > 0"),
}

PROBABILITY_SUITE = r'''
from fractions import Fraction
from math import comb

def independent_joint(p, q): return Fraction(p)*Fraction(q)
def binomial_pmf(n, k, p): return Fraction(comb(n,k))*Fraction(p)**k*(1-Fraction(p))**(n-k)
def estimate_mean(values): return Fraction(sum(values),len(values))
def reject_null(observed, null, tolerance): return abs(Fraction(observed)-Fraction(null)) > Fraction(tolerance)
def bayes(prior, likelihood, false_positive):
    prior=Fraction(prior); likelihood=Fraction(likelihood); false_positive=Fraction(false_positive)
    return prior*likelihood/(prior*likelihood+(1-prior)*false_positive)
def bounded_interval(values): return min(values),max(values)

assert independent_joint(Fraction(1,2),Fraction(1,3)) == Fraction(1,6)
assert binomial_pmf(4,2,Fraction(1,2)) == Fraction(3,8)
assert estimate_mean([1,2,6]) == 3
assert reject_null(12,10,1) and not reject_null(11,10,1)
assert bayes(Fraction(1,100),Fraction(9,10),Fraction(1,10)) == Fraction(1,12)
assert bounded_interval([3,1,5,2]) == (1,5)
print("passed")
'''

PROBABILITY_MUTATIONS = {
    "probability": ("Fraction(p)*Fraction(q)", "Fraction(p)+Fraction(q)"),
    "distributions": ("Fraction(comb(n,k))", "Fraction(n*k)"),
    "estimation": ("Fraction(sum(values),len(values))", "Fraction(sum(values),len(values)-1)"),
    "hypothesis_testing": ("> Fraction(tolerance)", ">= Fraction(tolerance)"),
    "bayesian_reasoning": ("(1-prior)*false_positive", "prior*false_positive"),
    "uncertainty": ("min(values),max(values)", "max(values),min(values)"),
}

ACCOUNTING_SUITE = r'''
from fractions import Fraction

def balanced(entries): return sum(Fraction(row[0]) for row in entries)==sum(Fraction(row[1]) for row in entries)
def accounting_equation(assets, liabilities, equity): return assets == liabilities+equity
def contribution(price, variable_cost): return price-variable_cost
def discounted_cash_flow(cashflows, rate):
    rate=Fraction(rate)
    return sum(Fraction(value)/(1+rate)**period for period,value in enumerate(cashflows,1))
def net_present_value(initial, cashflows, rate): return -Fraction(initial)+discounted_cash_flow(cashflows,rate)
def runway(cash, monthly_burn):
    if monthly_burn <= 0: raise ValueError("invalid burn")
    return Fraction(cash,monthly_burn)
def approved_payment(requester, approver, amount, limit): return requester != approver and amount <= limit

assert balanced([(100,0),(0,100)]) and not balanced([(100,0)])
assert accounting_equation(150,70,80) and not accounting_equation(150,80,80)
assert contribution(150,90) == 60
assert discounted_cash_flow([110],Fraction(1,10)) == 100
assert net_present_value(90,[110],Fraction(1,10)) == 10
assert runway(12000,3000) == 4
assert approved_payment("alice","bob",500,1000)
assert not approved_payment("alice","alice",500,1000)
assert not approved_payment("alice","bob",1500,1000)
print("passed")
'''

ACCOUNTING_MUTATIONS = {
    "bookkeeping": ("sum(Fraction(row[0]) for row in entries)==sum(Fraction(row[1]) for row in entries)",
                    "sum(Fraction(row[0]) for row in entries)>=sum(Fraction(row[1]) for row in entries)"),
    "statements": ("assets == liabilities+equity", "assets == liabilities-equity"),
    "cost_accounting": ("price-variable_cost", "price+variable_cost"),
    "valuation": ("/(1+rate)**period", "*(1+rate)**period"),
    "capital_budgeting": ("-Fraction(initial)+discounted_cash_flow", "Fraction(initial)+discounted_cash_flow"),
    "cash": ("Fraction(cash,monthly_burn)", "Fraction(monthly_burn,cash)"),
    "controls": ("requester != approver and amount <= limit", "requester == approver or amount <= limit"),
}

FINANCIAL_MATH_SUITE = r'''
from fractions import Fraction

def discount(value, rate, periods): return Fraction(value)/(1+Fraction(rate))**periods
def simple_return(start, end): return Fraction(end-start,start)
def call_bounds(spot, strike, price): return max(0,spot-strike) <= price <= spot
def state_price(up_payoff, down_payoff, up_price, down_price):
    return Fraction(up_price,up_payoff),Fraction(down_price,down_payoff)
def martingale(values, probabilities): return sum(Fraction(v)*Fraction(p) for v,p in zip(values,probabilities))
def change_measure(weights):
    total=sum(map(Fraction,weights)); return [Fraction(w,total) for w in weights]
def convexity_check(low, high):
    midpoint=Fraction(low+high,2); return midpoint**2 <= Fraction(low**2+high**2,2)
def one_step_option(spot_up, spot_down, strike, q, rate):
    payoff_up=max(0,spot_up-strike); payoff_down=max(0,spot_down-strike)
    return (Fraction(q)*payoff_up+(1-Fraction(q))*payoff_down)/(1+Fraction(rate))

assert discount(110,Fraction(1,10),1) == 100
assert simple_return(100,110) == Fraction(1,10)
assert call_bounds(100,90,15) and not call_bounds(100,90,105)
assert state_price(2,4,1,1) == (Fraction(1,2),Fraction(1,4))
assert martingale([80,120],[Fraction(1,2),Fraction(1,2)]) == 100
assert change_measure([2,3]) == [Fraction(2,5),Fraction(3,5)]
assert convexity_check(1,3)
assert one_step_option(121,81,101,Fraction(1,2),Fraction(1,10)) == Fraction(100,11)
print("passed")
'''

FINANCIAL_MATH_MUTATIONS = {
    "discounting": ("/(1+Fraction(rate))**periods", "*(1+Fraction(rate))**periods"),
    "returns": ("Fraction(end-start,start)", "Fraction(start-end,start)"),
    "no_arbitrage": ("<= price <= spot", ">= price >= spot"),
    "state_prices": ("Fraction(up_price,up_payoff),Fraction(down_price,down_payoff)",
                     "Fraction(up_payoff,up_price),Fraction(down_payoff,down_price)"),
    "martingales": ("Fraction(v)*Fraction(p)", "Fraction(v)+Fraction(p)"),
    "change_of_measure": ("Fraction(w,total)", "Fraction(total,w)"),
    "convexity": ("<= Fraction(low**2+high**2,2)", ">= Fraction(low**2+high**2,2)"),
    "numerical_pricing": ("/(1+Fraction(rate))", "*(1+Fraction(rate))"),
}

STRATEGIC_STEWARDSHIP_SUITE = r'''
from fractions import Fraction

def npv(cashflows, rate):
    return sum(Fraction(value)/(1+Fraction(rate))**period for period,value in enumerate(cashflows,1))
def concentration(weights): return max(map(Fraction,weights))
def dependency_reduction(before, after): return Fraction(before)-Fraction(after)
def option_value(options): return len(set(options))
def legitimate(lawful, transparent, harm_reviewed): return lawful and transparent and harm_reviewed
def approval_gate(valuation, legal, owner, capital): return valuation and legal and owner and capital
def evidence_score(independent, current, traceable): return sum((independent,current,traceable))
def scenario_floor(outcomes): return min(map(Fraction,outcomes))
def platform_dependency(switching_cost, lock_in): return Fraction(switching_cost)+Fraction(lock_in)
def resilience(redundancy, liquidity, supplier_concentration):
    return Fraction(redundancy)+Fraction(liquidity)-Fraction(supplier_concentration)
def incentive_compatible(outcomes): return all(value >= 0 for value in outcomes)
def exit_trigger(price, intrinsic, thesis_broken):
    return thesis_broken or Fraction(price) > Fraction(3,2)*Fraction(intrinsic)

assert npv([110],Fraction(1,10)) == 100
assert concentration([Fraction(1,2),Fraction(1,3),Fraction(1,6)]) == Fraction(1,2)
assert dependency_reduction(8,3) == 5
assert option_value(["build","buy","partner","partner"]) == 3
assert legitimate(True,True,True) and not legitimate(True,False,True)
assert approval_gate(True,True,True,True) and not approval_gate(True,True,False,True)
assert evidence_score(1,1,1) == 3
assert scenario_floor([4,-2,7]) == -2
assert platform_dependency(3,4) == 7
assert resilience(5,4,3) == 6
assert incentive_compatible([2,0,4]) and not incentive_compatible([2,-1,4])
assert exit_trigger(160,100,False) and exit_trigger(80,100,True) and not exit_trigger(120,100,False)
print("passed")
'''

_STRATEGIC_MUTATION_POOL = (
    ("/(1+Fraction(rate))**period", "*(1+Fraction(rate))**period"),
    ("max(map(Fraction,weights))", "sum(map(Fraction,weights))"),
    ("Fraction(before)-Fraction(after)", "Fraction(before)+Fraction(after)"),
    ("len(set(options))", "len(options)"),
    ("lawful and transparent and harm_reviewed", "lawful or transparent or harm_reviewed"),
    ("valuation and legal and owner and capital", "valuation or legal or owner or capital"),
    ("sum((independent,current,traceable))", "independent*current*traceable"),
    ("min(map(Fraction,outcomes))", "max(map(Fraction,outcomes))"),
    ("Fraction(switching_cost)+Fraction(lock_in)", "Fraction(switching_cost)-Fraction(lock_in)"),
    ("Fraction(redundancy)+Fraction(liquidity)-Fraction(supplier_concentration)",
     "Fraction(redundancy)-Fraction(liquidity)-Fraction(supplier_concentration)"),
    ("all(value >= 0 for value in outcomes)", "any(value >= 0 for value in outcomes)"),
    ("thesis_broken or Fraction(price) >", "thesis_broken and Fraction(price) >"),
)

def _strategic_mutations(*skills: str) -> dict[str, tuple[str, str]]:
    return {skill: _STRATEGIC_MUTATION_POOL[index % len(_STRATEGIC_MUTATION_POOL)]
            for index, skill in enumerate(skills)}

POWER_INSTITUTIONS_MUTATIONS = _strategic_mutations(
    "institutional_power", "law_and_rules", "legitimacy", "trust", "accountability",
    "state_capacity", "governance", "power_failure_modes")
INFORMATION_INTELLIGENCE_MUTATIONS = _strategic_mutations(
    "intelligence_collection", "source_criticism", "uncertainty", "confidentiality",
    "narrative_analysis", "attention_systems", "misinformation_defence", "transparency")
STRATEGIC_ASSET_MUTATIONS = _strategic_mutations(
    "asset_thesis", "valuation", "control_rights", "optionality", "dependency_reduction",
    "build_buy_partner", "portfolio_allocation", "exit_discipline")
TECHNOLOGY_INDUSTRY_MUTATIONS = _strategic_mutations(
    "technology_forecasting", "industry_structure", "platform_economics", "standards_strategy",
    "intellectual_property", "compute_data_energy", "manufacturing_scale", "distribution_power")
NETWORKS_TALENT_MUTATIONS = _strategic_mutations(
    "alliances", "talent_systems", "organisation_design", "incentive_alignment", "negotiation",
    "coordination", "culture", "succession")
RESILIENCE_GEOGRAPHY_MUTATIONS = _strategic_mutations(
    "geographic_advantage", "logistics", "resource_security", "supply_dependencies",
    "defensive_security", "scenario_planning", "resilience", "strategic_patience")

CYBER_RANGE_SUITE = r'''
from hashlib import sha256
from hmac import compare_digest
from pathlib import PurePosixPath

def authorized(scope, target):
    return scope.get("active") is True and scope.get("isolated") is True and target in scope.get("targets", [])
def safe_path(value):
    path=PurePosixPath(value); return not path.is_absolute() and ".." not in path.parts
def parameterized(query, parameters): return "?" in query and len(parameters) == query.count("?")
def secret_equal(left, right): return compare_digest(left.encode(),right.encode())
def least_privilege(granted, required, allowed):
    return set(required) <= set(granted) and set(granted) <= set(allowed)
def segmented(source, destination, allowed_flows): return (source,destination) in allowed_flows
def brute_force_detected(failures, window_seconds): return failures >= 5 and window_seconds <= 60
def contained(compromised, isolated): return compromised <= isolated
def approved_artifact(payload, expected): return sha256(payload).hexdigest() == expected
def replay_safe(nonces): return len(nonces) == len(set(nonces))
def safe_iam(actions, resources): return "*" not in actions and "*" not in resources
def severity(impact, likelihood): return min(10, max(0, impact*likelihood))
def disclosure_allowed(authorized_research, minimal_proof, vendor_notified):
    return authorized_research and minimal_proof and vendor_notified
def detected(events): return any(row.get("kind")=="denied_access" and row.get("count",0)>=3 for row in events)
def repaired(vulnerable_failed, patched_passed, variant_passed):
    return vulnerable_failed and patched_passed and variant_passed

scope={"active":True,"isolated":True,"targets":["lab.local"]}
assert authorized(scope,"lab.local") and not authorized(scope,"external.example")
assert safe_path("assets/report.txt") and not safe_path("../../etc/passwd") and not safe_path("/etc/passwd")
assert parameterized("select * from users where id=?",[7]) and not parameterized("select * from users where id=7",[])
assert secret_equal("token","token") and not secret_equal("token","other") and not secret_equal("token","tok")
assert least_privilege({"read"},{"read"},{"read","write"}) and not least_privilege({"admin"},{"read"},{"read","write"}) and not least_privilege(set(),{"read"},{"read"})
assert segmented("web","api",{("web","api")}) and not segmented("web","db",{("web","api")})
assert brute_force_detected(6,30) and not brute_force_detected(2,30)
assert contained({"host-a"},{"host-a","host-b"}) and not contained({"host-c"},{"host-a","host-b"})
payload=b"signed-package"; assert approved_artifact(payload,sha256(payload).hexdigest())
assert replay_safe(["a","b"]) and not replay_safe(["a","a"])
assert safe_iam({"read"},{"bucket/a"}) and not safe_iam({"*"},{"*"})
assert severity(2,3)==6 and severity(5,3)==10
assert disclosure_allowed(True,True,True) and not disclosure_allowed(False,True,True)
assert detected([{"kind":"denied_access","count":4}]) and not detected([{"kind":"login","count":4}])
assert repaired(True,True,True) and not repaired(True,True,False)
print("passed")
'''

_CYBER_MUTATION_POOL = (
    ('scope.get("active") is True and scope.get("isolated") is True and target in',
     'scope.get("active") is True or scope.get("isolated") is True or target in'),
    ('not path.is_absolute() and ".." not in path.parts', 'not path.is_absolute() or ".." not in path.parts'),
    ('"?" in query and len(parameters) == query.count("?")', '"?" not in query or len(parameters) == 0'),
    ('compare_digest(left.encode(),right.encode())', 'left.startswith(right)'),
    ('set(required) <= set(granted) and set(granted) <= set(allowed)', 'set(granted) <= set(required) or set(allowed) <= set(granted)'),
    ('(source,destination) in allowed_flows', '(source,destination) not in allowed_flows'),
    ('failures >= 5 and window_seconds <= 60', 'failures < 5 or window_seconds > 60'),
    ('compromised <= isolated', 'isolated <= compromised'),
    ('sha256(payload).hexdigest() == expected', 'sha256(payload).hexdigest() != expected'),
    ('len(nonces) == len(set(nonces))', 'len(nonces) >= len(set(nonces))'),
    ('"*" not in actions and "*" not in resources', '"*" in actions or "*" in resources'),
    ('min(10, max(0, impact*likelihood))', 'max(10, impact+likelihood)'),
    ('authorized_research and minimal_proof and vendor_notified', 'authorized_research or minimal_proof or vendor_notified'),
    ('row.get("kind")=="denied_access" and row.get("count",0)>=3', 'row.get("kind")=="login" or row.get("count",0)<3'),
    ('vulnerable_failed and patched_passed and variant_passed', 'vulnerable_failed or patched_passed or variant_passed'),
)

def _cyber_mutations(*skills: str) -> dict[str, tuple[str, str]]:
    return {skill: _CYBER_MUTATION_POOL[index % len(_CYBER_MUTATION_POOL)]
            for index, skill in enumerate(skills)}

APPSEC_MUTATIONS = _cyber_mutations("secure_coding", "authentication", "authorization", "session_security", "injection_defence", "browser_security", "api_security", "security_testing")
NETWORK_SECURITY_MUTATIONS = _cyber_mutations("network_reconnaissance", "protocol_analysis", "segmentation", "firewalls", "secure_routing", "wireless_security", "vpn_zero_trust", "network_validation")
CLOUD_SECURITY_MUTATIONS = _cyber_mutations("identity_access_management", "secrets", "cloud_posture", "container_security", "kubernetes_security", "serverless_security", "tenant_isolation", "continuous_assurance")
ADVERSARY_EMULATION_MUTATIONS = _cyber_mutations("scope_authorization", "reconnaissance", "attack_surface_mapping", "vulnerability_validation", "controlled_exploitation", "privilege_boundary_testing", "evidence_preservation", "remediation_verification")
REVERSE_ENGINEERING_MUTATIONS = _cyber_mutations("assembly_fundamentals", "debugging", "memory_safety", "binary_formats", "static_analysis", "dynamic_analysis", "exploit_mitigation", "malware_triage")
DETECTION_RESPONSE_MUTATIONS = _cyber_mutations("telemetry", "detection_logic", "threat_hunting", "triage", "containment", "eradication", "recovery", "post_incident_learning")
CRYPTO_PROTOCOL_MUTATIONS = _cyber_mutations("cryptographic_primitives", "key_management", "tls", "authentication_protocols", "protocol_state_machines", "nonce_replay_safety", "side_channels", "formal_protocol_review")
HARDWARE_OT_MUTATIONS = _cyber_mutations("firmware_analysis", "hardware_roots_of_trust", "debug_interfaces", "embedded_networks", "industrial_protocols", "safety_boundaries", "secure_updates", "physical_cyber_incidents")
DISCLOSURE_MUTATIONS = _cyber_mutations("research_ethics", "authorization", "reproducibility", "severity", "minimal_proof", "vendor_coordination", "embargo", "public_disclosure")
SECURITY_ARCHITECTURE_MUTATIONS = _cyber_mutations("zero_trust_architecture", "security_controls", "asset_inventory", "vulnerability_management", "supply_chain_assurance", "business_continuity", "metrics", "security_governance")
BASE_CYBERSECURITY_MUTATIONS = _cyber_mutations("threat_models", "secure_design", "cryptography", "network_security", "identity", "privacy", "incident_response", "supply_chain")

PREDICTION_MARKET_SUITE = r'''
from fractions import Fraction

def probability(value):
    value=Fraction(value)
    if not 0 <= value <= 1: raise ValueError("probability outside unit interval")
    return value
def brier(probability_value,outcome): return (probability(probability_value)-int(outcome))**2
def bayes(prior,likelihood_ratio):
    prior=probability(prior); odds=prior/(1-prior)
    posterior_odds=odds*Fraction(likelihood_ratio)
    return posterior_odds/(1+posterior_odds)
def net_edge(forecast,price,fee): return probability(forecast)-probability(price)-Fraction(fee)
def executable(edge,threshold,liquidity,minimum_liquidity):
    return Fraction(edge) >= Fraction(threshold) and liquidity >= minimum_liquidity
def capped_fraction(edge,loss_if_wrong,cap=Fraction(1,100)):
    if loss_if_wrong <= 0: raise ValueError("invalid downside")
    return min(cap,max(Fraction(0),Fraction(edge)/Fraction(loss_if_wrong)))
def resolution_valid(source,objective,known_before_close):
    return bool(source) and bool(objective) and not known_before_close
def live_authorized(eligible,owner_approved,stake,loss_limit):
    return bool(eligible and owner_approved and 0 < stake <= loss_limit)

assert probability(Fraction(3,5)) == Fraction(3,5)
try: probability(Fraction(6,5)); raise AssertionError("invalid probability accepted")
except ValueError: pass
assert brier(Fraction(3,4),1) == Fraction(1,16)
assert bayes(Fraction(1,2),3) == Fraction(3,4)
assert net_edge(Fraction(7,10),Fraction(3,5),Fraction(1,100)) == Fraction(9,100)
assert executable(Fraction(3,100),Fraction(2,100),1000,500)
assert not executable(Fraction(1,100),Fraction(2,100),1000,500)
assert not executable(Fraction(3,100),Fraction(2,100),100,500)
assert capped_fraction(Fraction(1,10),1) == Fraction(1,100)
assert resolution_valid("official_source",True,False)
assert not resolution_valid("",True,False) and not resolution_valid("official",False,False)
assert live_authorized(True,True,5,10)
assert not live_authorized(False,True,5,10) and not live_authorized(True,False,5,10)
assert not live_authorized(True,True,15,10)
print("passed")
'''

_PREDICTION_MUTATION_POOL = (
    ("not 0 <= value <= 1", "not value >= 0"),
    ("**2", "**1"),
    ("odds*Fraction(likelihood_ratio)", "odds/Fraction(likelihood_ratio)"),
    ("-probability(price)-Fraction(fee)", "+probability(price)-Fraction(fee)"),
    ("and liquidity >= minimum_liquidity", "or liquidity >= minimum_liquidity"),
    ("min(cap,max(Fraction(0),Fraction(edge)/Fraction(loss_if_wrong)))", "max(cap,Fraction(edge)/Fraction(loss_if_wrong))"),
    ("bool(source) and bool(objective) and not known_before_close", "bool(source) or bool(objective) or not known_before_close"),
    ("eligible and owner_approved and 0 < stake <= loss_limit", "eligible or owner_approved or stake <= loss_limit"),
)

def _prediction_mutations(*skills: str) -> dict[str, tuple[str, str]]:
    return {skill: _PREDICTION_MUTATION_POOL[index % len(_PREDICTION_MUTATION_POOL)]
            for index,skill in enumerate(skills)}

FORECASTING_MUTATIONS = _prediction_mutations("base_rates", "reference_classes", "bayesian_updates", "forecast_decomposition", "proper_scoring_rules", "calibration", "aggregation", "decision_thresholds")
PREDICTION_MICROSTRUCTURE_MUTATIONS = _prediction_mutations("binary_contracts", "order_books", "implied_probability", "fees_slippage", "liquidity", "position_sizing", "cross_market_coherence", "execution_controls")
EVENT_RESOLUTION_MUTATIONS = _prediction_mutations("question_decomposition", "source_hierarchy", "resolution_rules", "timeline_evidence", "conflicting_sources", "manipulation_risk", "audit_trail", "settlement_review")
ELECTIONS_MUTATIONS = _prediction_mutations("electoral_systems", "poll_sampling", "turnout_models", "poll_aggregation", "demographics", "campaign_dynamics", "forecast_error", "institutional_scenarios")
PREDICTION_DESIGN_MUTATIONS = _prediction_mutations("objective_question_design", "resolution_authority", "market_demand", "manipulation_resistance", "insider_information", "jurisdiction", "proposal_governance", "post_settlement_review")


SUBJECT_SUITES: dict[str, tuple[str, dict[str, tuple[str, str]], str]] = {
    "mathematics": (MATH_SUITE, MATH_MUTATIONS, "proof_and_calculation"),
    "english": (DOCUMENT_SUITE, DOCUMENT_MUTATIONS, "document_and_delayed_question"),
    "research_communication": (DOCUMENT_SUITE, DOCUMENT_MUTATIONS, "document_and_delayed_question"),
    "scientific_method": (SCIENCE_SUITE, SCIENCE_MUTATIONS, "empirical_dataset_or_experiment"),
    "data_statistics": (SCIENCE_SUITE, SCIENCE_MUTATIONS, "data_and_statistical_outcome"),
    "machine_learning_ai": (ML_SUITE, ML_MUTATIONS, "code_and_system_execution"),
    "markets_investing": (MARKETS_SUITE, MARKETS_MUTATIONS, "market_and_risk_execution"),
    "probability_statistics": (PROBABILITY_SUITE, PROBABILITY_MUTATIONS, "probability_and_inference"),
    "accounting_corporate_finance": (ACCOUNTING_SUITE, ACCOUNTING_MUTATIONS, "accounting_and_valuation"),
    "financial_mathematics": (FINANCIAL_MATH_SUITE, FINANCIAL_MATH_MUTATIONS, "financial_proof_and_pricing"),
    "power_institutions_legitimacy": (STRATEGIC_STEWARDSHIP_SUITE, POWER_INSTITUTIONS_MUTATIONS, "strategic_stewardship_decision"),
    "information_intelligence_attention": (STRATEGIC_STEWARDSHIP_SUITE, INFORMATION_INTELLIGENCE_MUTATIONS, "strategic_stewardship_decision"),
    "strategic_assets_capital_allocation": (STRATEGIC_STEWARDSHIP_SUITE, STRATEGIC_ASSET_MUTATIONS, "strategic_stewardship_decision"),
    "technology_industry_platforms": (STRATEGIC_STEWARDSHIP_SUITE, TECHNOLOGY_INDUSTRY_MUTATIONS, "strategic_stewardship_decision"),
    "networks_talent_coordination": (STRATEGIC_STEWARDSHIP_SUITE, NETWORKS_TALENT_MUTATIONS, "strategic_stewardship_decision"),
    "resilience_geography_long_horizon": (STRATEGIC_STEWARDSHIP_SUITE, RESILIENCE_GEOGRAPHY_MUTATIONS, "strategic_stewardship_decision"),
    "application_web_api_security": (CYBER_RANGE_SUITE, APPSEC_MUTATIONS, "authorized_cyber_range"),
    "cybersecurity": (CYBER_RANGE_SUITE, BASE_CYBERSECURITY_MUTATIONS, "authorized_cyber_range"),
    "network_wireless_security": (CYBER_RANGE_SUITE, NETWORK_SECURITY_MUTATIONS, "authorized_cyber_range"),
    "cloud_identity_container_security": (CYBER_RANGE_SUITE, CLOUD_SECURITY_MUTATIONS, "authorized_cyber_range"),
    "adversary_emulation_penetration_testing": (CYBER_RANGE_SUITE, ADVERSARY_EMULATION_MUTATIONS, "authorized_cyber_range"),
    "exploit_analysis_reverse_engineering": (CYBER_RANGE_SUITE, REVERSE_ENGINEERING_MUTATIONS, "authorized_cyber_range"),
    "detection_threat_hunting_incident_response": (CYBER_RANGE_SUITE, DETECTION_RESPONSE_MUTATIONS, "authorized_cyber_range"),
    "cryptography_protocol_security": (CYBER_RANGE_SUITE, CRYPTO_PROTOCOL_MUTATIONS, "authorized_cyber_range"),
    "hardware_embedded_ot_security": (CYBER_RANGE_SUITE, HARDWARE_OT_MUTATIONS, "authorized_cyber_range"),
    "security_research_disclosure": (CYBER_RANGE_SUITE, DISCLOSURE_MUTATIONS, "authorized_cyber_range"),
    "security_architecture_operations": (CYBER_RANGE_SUITE, SECURITY_ARCHITECTURE_MUTATIONS, "authorized_cyber_range"),
    "probabilistic_forecasting_calibration": (PREDICTION_MARKET_SUITE, FORECASTING_MUTATIONS, "governed_prediction_market"),
    "prediction_market_microstructure": (PREDICTION_MARKET_SUITE, PREDICTION_MICROSTRUCTURE_MUTATIONS, "governed_prediction_market"),
    "event_evidence_resolution_research": (PREDICTION_MARKET_SUITE, EVENT_RESOLUTION_MUTATIONS, "governed_prediction_market"),
    "elections_polling_public_opinion": (PREDICTION_MARKET_SUITE, ELECTIONS_MUTATIONS, "governed_prediction_market"),
    "prediction_market_design_compliance": (PREDICTION_MARKET_SUITE, PREDICTION_DESIGN_MUTATIONS, "governed_prediction_market"),
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
