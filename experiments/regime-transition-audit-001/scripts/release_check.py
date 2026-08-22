from pathlib import Path
import json,subprocess,sys
ROOT=Path(__file__).resolve().parents[1]
def rr(cmd): return subprocess.run(cmd,cwd=ROOT,text=True,capture_output=True)
def main():
 checks=[]; p=rr([sys.executable,"-m","unittest","discover","-s","tests","-v"]); checks.append({"name":"unit_tests","passed":p.returncode==0,"stderr":p.stderr})
 p=rr([sys.executable,"scripts/run_audit.py"]); checks.append({"name":"audit_run","passed":p.returncode==0,"stderr":p.stderr})
 r=json.loads((ROOT/"result.json").read_text()) if (ROOT/"result.json").exists() else {}; q=json.loads((ROOT/"preregistration.json").read_text())
 checks += [{"name":"policy_authority_none","passed":r.get("policy_authority")=="NONE"},{"name":"synthetic_ceiling_respected","passed":r.get("verdict")!="PREDICTIVE_ADVANTAGE_CANDIDATE"},{"name":"no_external_claim","passed":r.get("claims",{}).get("external_predictive_value_established") is False},{"name":"half_life_claim_forbidden","passed":"standing_has_a_universal_half_life" in q.get("forbidden_claims",[])}]
 ok=all(x["passed"] for x in checks); print(json.dumps({"schema":"openline.ace.rta001.release_check.v1","passed":ok,"checks":checks},indent=2,sort_keys=True)); return 0 if ok else 2
if __name__=="__main__": raise SystemExit(main())
