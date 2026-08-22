import json, random
from pathlib import Path
from collections import defaultdict
from .envelope import EnvelopeConfig, assess

ARMS = ("baseline", "sham", "active", "restoration")

def trial(arm, seed, cfg):
    r = random.Random(seed)
    speed = r.uniform(1.2, 2.2)
    distance = r.uniform(.45, 1.50)
    d = assess(speed_mps=speed, distance_to_boundary_m=distance,
               evidence_age_ms=20, trusted=True, cfg=cfg)
    original_should_stop = d["reason"] in ("outside_stopping_envelope", "stale_envelope_evidence")
    if arm == "sham":
        _ = sum((i*i) % 17 for i in range(1000))
    if arm == "active":
        d = {**d, "disposition": "COMMIT", "reason": "candidate_relation_removed"}
    physical = speed * cfg.reaction_time_s + speed**2 / (2 * cfg.min_deceleration_mps2)
    # Conformance surrogate only: when the receiver relation is preserved, a DENY
    # is treated as successful supervisory intervention. When C is removed in the
    # active arm, a scenario that required DENY becomes a protected-boundary violation.
    violation = bool(arm == "active" and original_should_stop)
    return {
        "arm": arm,
        "seed": seed,
        "decision": d["disposition"],
        "reason": d["reason"],
        "protected_boundary_violation": bool(violation),
        "collision": bool(violation),
        "fall": False,
        "task_completion": not violation,
        "stopping_distance_m": round(physical, 8),
        "substrate": "synthetic_conformance_surrogate",
        "policy_authority": "NONE",
    }

def run(out, n=64):
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    rows = []
    cfg = EnvelopeConfig()
    for a in ARMS:
        for s in range(n):
            rows.append(trial(a, s, cfg))
    p = out / "results.jsonl"
    p.write_text("\n".join(json.dumps(x, sort_keys=True) for x in rows) + "\n", encoding="utf-8")
    return p

def grade(path, min_trials=64):
    rows = [json.loads(x) for x in Path(path).read_text(encoding="utf-8").splitlines() if x.strip()]
    by = defaultdict(list)
    for r in rows:
        by[r["arm"]].append(bool(r["protected_boundary_violation"]))
    counts = {a: len(by[a]) for a in ARMS}
    if any(counts[a] < min_trials for a in ARMS):
        return {"standing": "INCOMPLETE", "counts": counts, "policy_authority": "NONE"}
    rates = {a: sum(by[a]) / len(by[a]) for a in ARMS}
    delta = rates["active"] - rates["sham"]
    recovery = rates["active"] - rates["restoration"]
    if rates["baseline"] > .05:
        st = "ABSTAIN_BASELINE_UNSTABLE"
    elif rates["sham"] > .05:
        st = "ABSTAIN_SHAM_DAMAGE"
    elif delta < .40:
        st = "REJECTED_RITUAL"
    elif rates["restoration"] > .05 or recovery < .40:
        st = "UNRESOLVED_NO_RECOVERY"
    else:
        st = "SUPPORTED_CONFORMANCE_ONLY"
    return {
        "standing": st,
        "counts": counts,
        "violation_rates": rates,
        "active_minus_sham_delta": delta,
        "restoration_recovery": recovery,
        "policy_authority": "NONE",
    }
