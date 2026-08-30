from __future__ import annotations
import argparse, hashlib, json, math, statistics, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT))
from is003.audit import audit, ACTIONS, LAGS
from is003.grid import load_grid, verify_grid

def sha_text(s): return hashlib.sha256(s.encode()).hexdigest()
def snap_sha(i,w): return sha_text(json.dumps({'integration_state_sha256':i,'wrapper_state_sha256':w},sort_keys=True,separators=(',',':')))
def median(xs): return statistics.median(xs) if xs else None

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--unitree-root',type=Path,required=True); ap.add_argument('--oracle-root',type=Path,required=True); ap.add_argument('--output',type=Path,required=True); args=ap.parse_args()
    sys.path.insert(0,str(args.oracle_root/'src'))
    from intervention_transition.adapter import UnitreeG1Adapter
    from intervention_transition.common import load_protocol, canonical_sha256
    protocol_path=args.oracle_root/'config/protocol.frozen.json'
    protocol_sha=hashlib.sha256(protocol_path.read_bytes()).hexdigest()
    if protocol_sha!='41fd6dc77bd16abdeaf141a733a86f6328b159c8fd44107cae0a59a34a502130':
        raise SystemExit(f'upstream protocol hash mismatch: {protocol_sha}')
    protocol=json.loads(protocol_path.read_text())
    grid=load_grid(); errors=verify_grid(grid)
    expected_grid=json.loads((ROOT/'PREREGISTRATION.json').read_text())['grid_sha256']
    actual_grid=hashlib.sha256((ROOT/'GRID.json').read_bytes()).hexdigest()
    if actual_grid!=expected_grid: errors.append(f'grid/preregistration hash mismatch: {actual_grid}')
    if errors: raise SystemExit('; '.join(errors))
    adapter=UnitreeG1Adapter(args.unitree_root,protocol); body=adapter.root_body_id(); dt=adapter.dt
    rollout_steps=int(round(float(protocol['rollout']['horizon_seconds'])/dt)); final_window=int(round(0.30/dt)); push_steps=int(round(0.08/dt)); warm=int(round(1.0/dt))
    rows=[]; receipts=[]
    for c in grid['contexts']:
        d=adapter.new_data(); w=adapter.new_wrapper(); adapter.step_n(d,w,warm+int(round(float(c['phase_offset_seconds'])/dt)))
        d.xfrc_applied[body,:]=0.0; d.xfrc_applied[body,0]=float(c['push_force_newtons'])*float(c['push_direction_x']); d.xfrc_applied[body,1]=float(c['push_force_newtons'])*float(c['push_direction_y']); d.xfrc_applied[body,4]=float(c['push_pitch_torque_sign'])*float(c['push_pitch_torque_magnitude_nm'])
        adapter.step_n(d,w,push_steps); d.xfrc_applied[body,:]=0.0; adapter.mujoco.mj_forward(adapter.model,d)
        snap=adapter.snapshot(d,w); ih=hashlib.sha256(snap['integration'].tobytes()).hexdigest(); wo={'action':[float(x) for x in snap['wrapper'].action],'target_dof_pos':[float(x) for x in snap['wrapper'].target_dof_pos],'obs':[float(x) for x in snap['wrapper'].obs],'counter':int(snap['wrapper'].counter),'cmd':[float(x) for x in snap['wrapper'].cmd],'policy_state':adapter.policy_state_hashes(snap['wrapper'])}; wh=canonical_sha256(wo)
        receipts.append({**c,'integration_state_sha256':ih,'wrapper_state_sha256':wh,'snapshot_health':adapter.state_health(d)})
        risk=f"force:{float(c['push_force_newtons']):g}|abs_pitch_torque:{abs(float(c['push_pitch_torque_magnitude_nm'])):g}"
        for action_id in ACTIONS:
            cmd=protocol['actions'][action_id]
            for lag in LAGS:
                bd,bw=adapter.restore(snap); switch=int(math.ceil((lag/1000.0)/dt)); failed=False; switched=False; hs=[]; gs=[]
                for step in range(rollout_steps):
                    if not switched and step>=switch: bw.cmd[:]=adapter.np.asarray(cmd,dtype=adapter.np.float64); switched=True
                    adapter.step(bd,bw); h=adapter.state_health(bd); hs.append(h['height']); gs.append(h['gravity_horizontal_norm'])
                    if switched and ((not h['finite']) or h['height']<0.45 or h['gravity_z']>-0.35): failed=True; break
                success=False if failed else bool(hs and gs and median(hs[-final_window:])>=0.60 and median(gs[-final_window:])<=0.45)
                rows.append({'schema':'openline.ace.intervention-outcome.v3','dataset_id':'is003-unitree-confirmatory','evidence_mode':'deterministic_rollout','context_id':c['context_id'],'split':c['split'],'stratum':c['stratum'],'snapshot_sha256':snap_sha(ih,wh),'apparent_risk_bucket':risk,'action_id':action_id,'lag_ms':lag,'replicate':0,'trial_id':f"{c['context_id']}:{action_id}:{lag}",'outcome_success':success,'target_sha256':sha_text(protocol['rollout']['target_id']),'constraint_set_sha256':sha_text(protocol['rollout']['constraint_set_id']),'policy_authority':'NONE'})
    args.output.mkdir(parents=True,exist_ok=True); (args.output/'context_receipts.json').write_text(json.dumps(receipts,indent=2,sort_keys=True)+'\n'); (args.output/'canonical_rows.jsonl').write_text(''.join(json.dumps(r,sort_keys=True,separators=(',',':'))+'\n' for r in sorted(rows,key=lambda r:(r['context_id'],r['action_id'],r['lag_ms']))))
    result=audit(rows); result['grid_sha256']=hashlib.sha256((ROOT/'GRID.json').read_bytes()).hexdigest(); result['source_pins']={'openline_receipt_gate':'20db896fafabe197039e567f364ec5f7a6c3d699','unitree_rl_gym':'276801e46c5d433564f24658bac64f254b7d2d4b'}; result['canonical_rows_sha256']=hashlib.sha256((args.output/'canonical_rows.jsonl').read_bytes()).hexdigest(); (args.output/'result.json').write_text(json.dumps(result,indent=2,sort_keys=True)+'\n'); (args.output/'result.sha256').write_text(hashlib.sha256((args.output/'result.json').read_bytes()).hexdigest()+'  result.json\n'); print(json.dumps(result,indent=2,sort_keys=True))
if __name__=='__main__': main()
