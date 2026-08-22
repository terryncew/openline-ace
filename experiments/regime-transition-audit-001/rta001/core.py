from __future__ import annotations
from dataclasses import dataclass

@dataclass(frozen=True)
class Metrics:
    balanced_accuracy: float
    brier_score: float
    positive_predictive_value: float

def detect_regime(row, prereg):
    crossed=0
    for name,spec in prereg["signal_dimensions"].items():
        if spec["direction"]!="gte": raise ValueError("unsupported direction")
        crossed += float(row[name]) >= float(spec["threshold"])
    return crossed >= int(prereg["regime_rule"]["minimum_dimensions_crossed"])

def freshness_probability(age):
    return max(0.0,min(1.0,0.15+0.70*float(age)))

def candidate_probability(age, regime):
    base=freshness_probability(age)
    return max(base,0.82) if regime else min(base,0.28)

def _ba(y,p):
    tp=tn=fp=fn=0
    for a,b in zip(y,p):
        if a and b: tp+=1
        elif a and not b: fn+=1
        elif not a and b: fp+=1
        else: tn+=1
    tpr=tp/(tp+fn) if tp+fn else 0.0
    tnr=tn/(tn+fp) if tn+fp else 0.0
    return (tpr+tnr)/2

def _ppv(y,p):
    tp=sum(1 for a,b in zip(y,p) if a and b); fp=sum(1 for a,b in zip(y,p) if (not a) and b)
    return tp/(tp+fp) if tp+fp else 0.0

def score(rows, prereg, candidate):
    rows=list(rows); y=[bool(r["later_standing_failure"]) for r in rows]; probs=[]
    for r in rows:
        age=float(r["age_since_last_verification"])
        probs.append(candidate_probability(age,detect_regime(r,prereg)) if candidate else freshness_probability(age))
    pred=[p>=.5 for p in probs]
    brier=sum((p-(1.0 if a else 0.0))**2 for p,a in zip(probs,y))/len(rows)
    return Metrics(_ba(y,pred),brier,_ppv(y,pred))

def evaluate(rows,prereg):
    rows=list(rows); held=[r for r in rows if int(r["case_id"])%2==1]
    if len(held)<int(prereg["minimum_heldout_cases"]): return {"verdict":"INSUFFICIENT_HELDOUT_CASES","policy_authority":"NONE"}
    base=score(held,prereg,False); cand=score(held,prereg,True)
    ba_delta=cand.balanced_accuracy-base.balanced_accuracy; brier_imp=base.brier_score-cand.brier_score
    m=prereg["promotion_margins"]; beats=ba_delta>=m["balanced_accuracy_delta_min"] and brier_imp>=m["brier_improvement_min"]
    external=all(r.get("provenance")!="synthetic_fixture" for r in rows)
    verdict="NO_PREDICTIVE_ADVANTAGE" if not beats else ("PREDICTIVE_ADVANTAGE_CANDIDATE" if external else prereg["synthetic_fixture_max_standing"])
    return {"schema":"openline.ace.rta001.result.v1","verdict":verdict,"policy_authority":"NONE","heldout_cases":len(held),"baseline":base.__dict__,"candidate":cand.__dict__,"deltas":{"balanced_accuracy":ba_delta,"brier_improvement":brier_imp},"claims":{"proves_universal_half_life":False,"proves_regime_mechanism":False,"grants_execution_authority":False,"external_predictive_value_established":bool(external and beats)}}
