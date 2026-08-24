from __future__ import annotations

def decision_truth(t0, component):
    out={}
    for d in t0["decisions"]:
        target=d["target"]; dtype=d["decision_type"]
        runtime=component in t0["closures"][target]["runtime"]
        build=component in t0["closures"][target]["build"]
        dev=component in t0["closures"][target]["dev"]
        if dtype=="runtime_security_acceptance":
            affected=runtime
        elif dtype=="build_security_acceptance":
            affected=build
        elif dtype=="test_security_acceptance":
            affected=dev
        elif dtype=="build_acceptance":
            affected=False
        elif dtype=="promotion_permission":
            affected=runtime or build
        else:
            raise ValueError(f"unknown decision type: {dtype}")
        out[d["decision_id"]]=bool(affected)
    return out
