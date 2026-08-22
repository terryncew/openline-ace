from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Mapping

DECISIVE={"APPROVED","CHANGES_REQUESTED","DISMISSED"}

def parse_ts(s):
    return datetime.fromisoformat(s.replace("Z","+00:00"))

def detect_regime(row, prereg):
    inherited=prereg["inherits_rta001"]
    crossed=0
    for name,spec in inherited["signal_dimensions"].items():
        crossed += float(row[name]) >= float(spec["threshold"])
    return crossed >= int(inherited["regime_rule"]["minimum_dimensions_crossed"])

def freshness_probability(age):
    return max(0.0,min(1.0,0.15+0.70*float(age)))

def candidate_probability(age, regime):
    base=freshness_probability(age)
    return max(base,0.82) if regime else min(base,0.28)

def build_case(pr, reviews, commits, prereg):
    approvals=sorted([r for r in reviews if r.get("state")=="APPROVED" and r.get("submitted_at")], key=lambda r:r["submitted_at"])
    if not approvals:
        return None
    first=parse_ts(approvals[0]["submitted_at"])
    checkpoint=first.timestamp()+24*3600
    closed=parse_ts(pr["closed_at"]).timestamp() if pr.get("closed_at") else None
    if closed is not None and closed <= checkpoint:
        return None

    pre=[r for r in reviews if r.get("submitted_at") and parse_ts(r["submitted_at"]).timestamp() <= checkpoint]
    decisive=[r for r in pre if r.get("state") in DECISIVE]
    if not decisive:
        return None

    latest_approval=max(parse_ts(r["submitted_at"]).timestamp() for r in pre if r.get("state")=="APPROVED")
    age=min(1.0,max(0.0,(checkpoint-latest_approval)/3600/168))

    first_decisive=min(parse_ts(r["submitted_at"]).timestamp() for r in decisive)
    commit_times=[parse_ts(c["commit"]["committer"]["date"]).timestamp()
                  for c in commits
                  if c.get("commit",{}).get("committer",{}).get("date")]
    churn_count=sum(1 for t in commit_times if first_decisive < t <= checkpoint)
    dependency_churn=min(1.0,churn_count/4.0)

    n=len(decisive)
    contradiction=sum(1 for r in decisive if r.get("state")=="CHANGES_REQUESTED")/n
    withdrawn=sum(1 for r in decisive if r.get("state")=="DISMISSED")/n

    post=[r for r in reviews if r.get("submitted_at") and parse_ts(r["submitted_at"]).timestamp() > checkpoint]
    failure=any(r.get("state") in {"CHANGES_REQUESTED","DISMISSED"} for r in post)

    return {
        "case_id": int(pr["number"]),
        "pr_number": int(pr["number"]),
        "checkpoint": datetime.fromtimestamp(checkpoint,timezone.utc).isoformat().replace("+00:00","Z"),
        "age_since_last_verification": age,
        "dependency_churn": dependency_churn,
        "contradiction_rate": contradiction,
        "support_withdrawal_rate": withdrawn,
        "later_standing_failure": bool(failure),
        "provenance": "external_github_review_history"
    }

def _metrics(rows, prereg, candidate):
    y=[bool(r["later_standing_failure"]) for r in rows]
    probs=[]
    for r in rows:
        age=float(r["age_since_last_verification"])
        probs.append(candidate_probability(age,detect_regime(r,prereg)) if candidate else freshness_probability(age))
    pred=[p>=.5 for p in probs]
    tp=sum(a and b for a,b in zip(y,pred)); fn=sum(a and not b for a,b in zip(y,pred))
    tn=sum((not a) and (not b) for a,b in zip(y,pred)); fp=sum((not a) and b for a,b in zip(y,pred))
    tpr=tp/(tp+fn) if tp+fn else 0.0
    tnr=tn/(tn+fp) if tn+fp else 0.0
    ba=(tpr+tnr)/2
    brier=sum((p-(1.0 if a else 0.0))**2 for p,a in zip(probs,y))/len(rows)
    ppv=tp/(tp+fp) if tp+fp else 0.0
    return {"balanced_accuracy":ba,"brier_score":brier,"positive_predictive_value":ppv}

def evaluate(rows, prereg):
    rows=sorted(list(rows),key=lambda r:(r["checkpoint"],r["case_id"]))
    min_total=int(prereg["minimum_eligible_cases"])
    if len(rows)<min_total:
        return {"verdict":"DATA_INSUFFICIENT","reason":"eligible_case_floor","eligible_cases":len(rows),"policy_authority":"NONE"}
    cut=len(rows)//2
    held=rows[cut:]
    positives=sum(bool(r["later_standing_failure"]) for r in held)
    if len(held)<int(prereg["minimum_heldout_cases"]) or positives<int(prereg["minimum_positive_outcomes_heldout"]):
        return {"verdict":"DATA_INSUFFICIENT","reason":"heldout_or_positive_floor","eligible_cases":len(rows),"heldout_cases":len(held),"heldout_positives":positives,"policy_authority":"NONE"}

    base=_metrics(held,prereg,False); cand=_metrics(held,prereg,True)
    dba=cand["balanced_accuracy"]-base["balanced_accuracy"]
    dbrier=base["brier_score"]-cand["brier_score"]
    margins=prereg["inherits_rta001"]["promotion_margins"]
    beats=dba>=margins["balanced_accuracy_delta_min"] and dbrier>=margins["brier_improvement_min"]
    return {
        "schema":"openline.ace.rta002.result.v1",
        "verdict":"PREDICTIVE_ADVANTAGE_CANDIDATE" if beats else "NO_PREDICTIVE_ADVANTAGE",
        "policy_authority":"NONE",
        "eligible_cases":len(rows),
        "heldout_cases":len(held),
        "heldout_positives":positives,
        "baseline":base,
        "candidate":cand,
        "deltas":{"balanced_accuracy":dba,"brier_improvement":dbrier},
        "claims":{
            "proves_universal_regime_mechanism":False,
            "proves_causality":False,
            "grants_execution_authority":False,
            "external_predictive_advantage_observed":bool(beats)
        }
    }
