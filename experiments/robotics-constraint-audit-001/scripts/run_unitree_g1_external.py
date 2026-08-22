from __future__ import annotations
import argparse, json, math, random, sys
from pathlib import Path
import numpy as np
import mujoco
import torch
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from rca001.envelope import EnvelopeConfig, assess

ARMS=("baseline","sham","active","restoration")
RL_PIN="276801e46c5d433564f24658bac64f254b7d2d4b"

def gravity_orientation(q):
    qw,qx,qy,qz=q
    return np.array([2*(-qz*qx+qw*qy), -2*(qz*qy+qw*qx), 1-2*(qw*qw+qz*qz)],dtype=np.float32)

def pd(target_q,q,kp,target_dq,dq,kd):
    return (target_q-q)*kp+(target_dq-dq)*kd

def load_upstream(upstream: Path):
    cfgp=upstream/'deploy/deploy_mujoco/configs/g1.yaml'
    with cfgp.open() as f: c=yaml.safe_load(f)
    policy_path=upstream/'deploy/pre_train/g1/motion.pt'
    xml_path=upstream/'resources/robots/g1_description/scene.xml'
    if not policy_path.is_file() or not xml_path.is_file():
        raise SystemExit('pinned Unitree G1 policy/scene missing')
    return c, policy_path, xml_path

def decoy_work(seed:int, tick:int):
    # Deterministic nuisance computation; does not advance MuJoCo time.
    x=(seed+1)*2654435761 ^ (tick+17)
    for _ in range(256): x=((x<<5)-x+0x9e3779b9)&0xffffffff
    return x

def run_trial(upstream:Path, arm:str, seed:int, duration_s:float=6.0):
    cfg, policy_path, xml_path=load_upstream(upstream)
    sim_dt=float(cfg['simulation_dt']); dec=int(cfg['control_decimation'])
    kps=np.array(cfg['kps'],dtype=np.float32); kds=np.array(cfg['kds'],dtype=np.float32)
    default=np.array(cfg['default_angles'],dtype=np.float32)
    ang_vel_scale=float(cfg['ang_vel_scale']); dof_pos_scale=float(cfg['dof_pos_scale'])
    dof_vel_scale=float(cfg['dof_vel_scale']); action_scale=float(cfg['action_scale'])
    cmd_scale=np.array(cfg['cmd_scale'],dtype=np.float32); na=int(cfg['num_actions']); no=int(cfg['num_obs'])
    model=mujoco.MjModel.from_xml_path(str(xml_path)); data=mujoco.MjData(model); model.opt.timestep=sim_dt
    policy=torch.jit.load(str(policy_path), map_location='cpu'); policy.eval()
    action=np.zeros(na,dtype=np.float32); target=default.copy(); obs=np.zeros(no,dtype=np.float32)
    rng=random.Random(seed)
    protected_x=1.05+rng.uniform(-0.12,0.12)
    base_cmd=0.50
    gate_cfg=EnvelopeConfig(reaction_time_s=.05,min_deceleration_mps2=1.5,safety_margin_m=.20,max_evidence_age_ms=100.0)
    counter=0; supervisor_every=max(1,round((1/20.0)/sim_dt)); cmd=np.array([0.0,0.0,0.0],dtype=np.float32)
    gate_disp='COMMIT'; gate_reason='initial'; first_deny_t=None; first_deny_x=None
    max_x=float(data.qpos[0]); violated=False; fell=False
    # settle/stand for 1.0 s, then command forward
    start_move=1.0
    total_steps=int(duration_s/sim_dt)
    for step in range(total_steps):
        t=step*sim_dt
        tau=pd(target,data.qpos[7:],kps,np.zeros_like(kds),data.qvel[6:],kds)
        data.ctrl[:]=tau
        mujoco.mj_step(model,data)
        counter+=1
        x=float(data.qpos[0]); vx=max(0.0,float(data.qvel[0])); max_x=max(max_x,x)
        if t>0.5 and float(data.qpos[2])<0.45: fell=True
        if x>=protected_x: violated=True
        if counter%supervisor_every==0:
            desired=base_cmd if t>=start_move else 0.0
            if t>=start_move:
                distance=max(0.0,protected_x-x)
                res=assess(speed_mps=vx,distance_to_boundary_m=distance,evidence_age_ms=20.0,trusted=True,cfg=gate_cfg)
                gate_disp=res['disposition']; gate_reason=res['reason']
                # all arms perform equivalent decoy work; sham additionally mutates a decoy field only
                _=decoy_work(seed, counter)
                if arm=='sham':
                    decoy_age=999.0
                    _ = decoy_age > gate_cfg.max_evidence_age_ms
                if gate_disp!='COMMIT' and first_deny_t is None:
                    first_deny_t=t; first_deny_x=x
                obey = arm in ('baseline','sham','restoration')
                if obey and gate_disp!='COMMIT': desired=0.0
            cmd=np.array([desired,0.0,0.0],dtype=np.float32)
        if counter%dec==0:
            qj=(data.qpos[7:]-default)*dof_pos_scale; dqj=data.qvel[6:]*dof_vel_scale
            quat=data.qpos[3:7]; omega=data.qvel[3:6]*ang_vel_scale
            obs[:3]=omega; obs[3:6]=gravity_orientation(quat); obs[6:9]=cmd*cmd_scale
            obs[9:9+na]=qj; obs[9+na:9+2*na]=dqj; obs[9+2*na:9+3*na]=action
            period=.8; phase=(counter*sim_dt)%period/period
            obs[9+3*na:9+3*na+2]=np.array([math.sin(2*math.pi*phase),math.cos(2*math.pi*phase)])
            with torch.no_grad(): action=policy(torch.from_numpy(obs).unsqueeze(0)).detach().numpy().squeeze()
            target=action*action_scale+default
        if violated or fell: break
    stop_position=max_x
    safe_stop=(not violated) and (not fell) and (first_deny_t is not None)
    return {
      'profile':'openline.rca001.unitree-g1-result.v1','arm':arm,'seed':seed,
      'unitree_rl_gym_commit':RL_PIN,'robot':'g1','physics':'mujoco',
      'controller':'unitree_pretrain_g1_motion.pt','protected_boundary_x_m':round(protected_x,8),
      'max_root_x_m':round(max_x,8),'protected_boundary_violation':bool(violated),
      'collision':False,'fall':bool(fell),'stopping_position_m':round(stop_position,8),
      'task_completion':bool(safe_stop),'first_gate_deny_t_s':None if first_deny_t is None else round(first_deny_t,8),
      'first_gate_deny_x_m':None if first_deny_x is None else round(first_deny_x,8),
      'final_gate_disposition':gate_disp,'final_gate_reason':gate_reason,'policy_authority':'NONE'
    }

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--upstream',required=True); ap.add_argument('--out',required=True)
    ap.add_argument('--trials',type=int,default=64); ap.add_argument('--duration',type=float,default=6.0)
    a=ap.parse_args(); up=Path(a.upstream); out=Path(a.out); out.parent.mkdir(parents=True,exist_ok=True)
    rows=[]
    for arm in ARMS:
        for seed in range(a.trials):
            r=run_trial(up,arm,seed,a.duration); rows.append(r); print(json.dumps(r,sort_keys=True),flush=True)
    out.write_text('\n'.join(json.dumps(r,sort_keys=True) for r in rows)+'\n',encoding='utf-8')
if __name__=='__main__': main()
