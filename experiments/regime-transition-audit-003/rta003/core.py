
def detect_regime(r,p):
    s=p["inherits_frozen_rta001"]["signal_dimensions"]
    return sum(float(r[k]) >= float(v["threshold"]) for k,v in s.items()) >= int(p["inherits_frozen_rta001"]["minimum_dimensions_crossed"])

def fresh(age):
    return max(0.0,min(1.0,.15+.70*float(age)))

def cand(age,regime):
    b=fresh(age)
    return max(b,.82) if regime else min(b,.28)

def metrics(rows,p,candidate=False):
    y=[bool(r["later_standing_failure"]) for r in rows]
    probs=[cand(r["age_since_last_verification"],detect_regime(r,p)) if candidate else fresh(r["age_since_last_verification"]) for r in rows]
    pred=[x>=.5 for x in probs]
    tp=sum(a and b for a,b in zip(y,pred)); fn=sum(a and not b for a,b in zip(y,pred))
    tn=sum((not a) and (not b) for a,b in zip(y,pred)); fp=sum((not a) and b for a,b in zip(y,pred))
    ba=((tp/(tp+fn) if tp+fn else 0)+(tn/(tn+fp) if tn+fp else 0))/2
    br=sum((q-(1 if a else 0))**2 for q,a in zip(probs,y))/len(rows)
    return {"balanced_accuracy":ba,"brier_score":br}

def split_heldout(rows):
    out=[]
    repos=sorted(set(r["repository"] for r in rows))
    for repo in repos:
        rr=sorted([r for r in rows if r["repository"]==repo],key=lambda r:(r["checkpoint"],r["case_id"]))
        out.extend(r for i,r in enumerate(rr) if i%2==1)
    return out

def evaluate(rows,p):
    rows=list(rows); held=split_heldout(rows)
    repo_counts={x:sum(r["repository"]==x for r in rows) for x in set(r["repository"] for r in rows)}
    enough_repos=sum(v>=20 for v in repo_counts.values())
    positives=sum(bool(r["later_standing_failure"]) for r in held)
    if (len(rows)<p["minimum_eligible_cases_total"] or len(held)<p["minimum_heldout_cases_total"] or
        positives<p["minimum_positive_outcomes_heldout"] or enough_repos<p["minimum_repositories_with_20_eligible_cases"]):
        return {"verdict":"DATA_INSUFFICIENT","eligible_cases":len(rows),"heldout_cases":len(held),
                "heldout_positives":positives,"repository_eligible_counts":repo_counts,"policy_authority":"NONE"}
    b=metrics(held,p,False); c=metrics(held,p,True)
    dba=c["balanced_accuracy"]-b["balanced_accuracy"]; db=b["brier_score"]-c["brier_score"]
    per={}
    guard=True
    for repo in sorted(repo_counts):
        rr=[r for r in held if r["repository"]==repo]
        if len(rr)>=20:
            rb=metrics(rr,p,False); rc=metrics(rr,p,True)
            delta=rc["balanced_accuracy"]-rb["balanced_accuracy"]
            per[repo]={"heldout_cases":len(rr),"balanced_accuracy_delta":delta}
            guard &= delta >= -0.02
    f=p["inherits_frozen_rta001"]
    win=dba>=f["balanced_accuracy_delta_min"] and db>=f["brier_improvement_min"] and guard
    return {"schema":"openline.ace.rta003.result.v1",
            "verdict":"PREDICTIVE_ADVANTAGE_CANDIDATE" if win else "NO_PREDICTIVE_ADVANTAGE",
            "eligible_cases":len(rows),"heldout_cases":len(held),"heldout_positives":positives,
            "baseline":b,"candidate":c,"deltas":{"balanced_accuracy":dba,"brier_improvement":db},
            "cross_repo":per,"cross_repo_guard_passed":guard,"policy_authority":"NONE",
            "claims":{"universal_regime_mechanism":False,"causality":False,"execution_authority":False}}
