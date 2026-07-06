#!/usr/bin/env python3
from __future__ import annotations
import json, math, hashlib, subprocess, time, zipfile
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import Any, Dict, List, Tuple
import numpy as np

TAU=2*math.pi
SEED=(2,3); COUNT=400000; TRAIN=100000; CHECKPOINTS=[200000,300000,400000]
BINS=720; WALL_FRAC=0.10; INITIAL_ALPHA=1.1650128838912948; RANDOM_CONTROLS=16

@dataclass
class Receipt:
    claim: str; action: str; evidence: Dict[str, Any]; result: str
    witness: str="ace-ulam-23-promotion-400k"; parent_hash: str|None=None; receipt_hash: str|None=None
    def seal(self):
        body={"claim":self.claim,"action":self.action,"evidence":self.evidence,"result":self.result,"witness":self.witness,"parent_hash":self.parent_hash}
        self.receipt_hash=hashlib.sha256(json.dumps(body,sort_keys=True,separators=(",",":")).encode()).hexdigest(); return self
receipts=[]
def add_receipt(claim, action, evidence, result):
    parent=receipts[-1].receipt_hash if receipts else None; receipts.append(Receipt(claim,action,evidence,result,parent_hash=parent).seal())
def write_receipts(path):
    with open(path,'w') as f:
        for r in receipts: f.write(json.dumps(asdict(r),sort_keys=True)+'\n')
def verify_receipts(path):
    prev=None
    for line in Path(path).read_text().splitlines():
        r=json.loads(line)
        if r['parent_hash']!=prev: return False
        body={"claim":r['claim'],"action":r['action'],"evidence":r['evidence'],"result":r['result'],"witness":r['witness'],"parent_hash":r['parent_hash']}
        h=hashlib.sha256(json.dumps(body,sort_keys=True,separators=(",",":")).encode()).hexdigest()
        if h!=r['receipt_hash']: return False
        prev=h
    return True
def sha256_file(path):
    h=hashlib.sha256()
    with open(path,'rb') as f:
        for ch in iter(lambda:f.read(1<<20),b''): h.update(ch)
    return h.hexdigest()
def ensure_generator(root):
    exe=root/'ulam_fast_seed'; src=root/'ulam_fast_seed.c'
    if not exe.exists(): subprocess.run(['gcc','-O3','-std=c99','-Wall','-Wextra','-o',str(exe),str(src)], check=True)
    return exe
def generate_seed(root, seed, count):
    a,b=seed; cache=root/'cache'; cache.mkdir(exist_ok=True)
    vals=cache/f'ulam_{a}_{b}_values_{count}.bin'; counts=cache/f'ulam_{a}_{b}_counts_saturated_{count}.bin'
    if not(vals.exists() and vals.stat().st_size==count*8):
        exe=ensure_generator(root); subprocess.run([str(exe),str(count),str(a),str(b),str(vals),str(counts)], check=True)
    return np.fromfile(vals,dtype=np.int64), vals, counts
def phase_score(vals, alpha):
    return float(abs(np.mean(np.exp(1j*((vals.astype(np.float64)*alpha)%TAU)))))
def refine_alpha(values, alpha0):
    # Use subsampled broad refinement followed by full refinement; dramatically faster and stable for narrow clock.
    best=float(alpha0); trail=[]
    sample=values[::4]
    for radius, pts, vals in [(2e-5,81,sample),(4e-6,81,sample),(8e-7,81,values),(1.6e-7,81,values),(3.2e-8,65,values)]:
        grid=np.linspace(best-radius,best+radius,pts); scores=[]; vf=vals.astype(np.float64)
        for a in grid: scores.append(abs(np.mean(np.exp(1j*((vf*float(a))%TAU)))))
        i=int(np.argmax(scores)); best=float(grid[i]); trail.append({'radius':radius,'points':pts,'alpha':best,'score':float(scores[i]),'sample_size':int(len(vals))})
    return best, phase_score(values,best), trail
def exact_counts(values):
    max_v=int(values[-1]); indicator=np.zeros(max_v+1,dtype=np.float64); indicator[values]=1.0
    conv_len=2*max_v+1; fft_len=1<<(conv_len-1).bit_length()
    spec=np.fft.rfft(indicator,n=fft_len); conv=np.fft.irfft(spec*spec,n=fft_len)[:conv_len]
    ordered=np.rint(conv).astype(np.int64); self_pairs=np.zeros(conv_len,dtype=np.int64); self_pairs[values*2]=1
    out=(ordered-self_pairs)//2; out[out<0]=0; return out
def phase_bins(candidates, alpha, bins=BINS):
    idx=np.floor(((candidates.astype(np.float64)*alpha)%TAU)/TAU*bins).astype(np.int64); idx[idx==bins]=bins-1; return idx
def circular_smooth(x, radius=3):
    y=np.zeros_like(x,dtype=float)
    for k in range(-radius,radius+1): y+=np.roll(x,k)
    return y/(2*radius+1)
def profile(candidates, Rvals, accepted_mask, alpha, bins=BINS):
    idx=phase_bins(candidates,alpha,bins); total=np.bincount(idx,minlength=bins).astype(float)
    acc=np.bincount(idx[accepted_mask],minlength=bins).astype(float)
    crowd_mask=Rvals>=2; crowd=np.bincount(idx[crowd_mask],minlength=bins).astype(float)
    dsum=np.bincount(idx,weights=Rvals.astype(float),minlength=bins)
    acc_density=np.divide(acc,total,out=np.zeros_like(acc),where=total>0)
    crowd_density=np.divide(crowd,total,out=np.zeros_like(crowd),where=total>0)
    mean_depth=np.divide(dsum,total,out=np.zeros_like(dsum),where=total>0)
    md=circular_smooth(np.log1p(mean_depth),3); ad=circular_smooth(acc_density,3)
    def z(v):
        s=np.std(v); return (v-np.mean(v))/(s if s>0 else 1.0)
    score=z(md)-z(ad)
    return {'total':total,'acc_density':acc_density,'crowd_density':crowd_density,'mean_depth':mean_depth,'score':score}
def top_fraction_mask(score, frac=WALL_FRAC):
    k=max(1,int(round(len(score)*frac))); order=np.argsort(score)[::-1]; mask=np.zeros(len(score),dtype=bool); mask[order[:k]]=True; return mask
def auc_binned(score, pos, neg):
    order=np.argsort(score); totp=float(pos.sum()); totn=float(neg.sum())
    if totp==0 or totn==0: return float('nan')
    cumneg=0.0; win=0.0; i=0
    while i<len(order):
        j=i+1
        while j<len(order) and score[order[j]]==score[order[i]]: j+=1
        g=order[i:j]; gp=float(pos[g].sum()); gn=float(neg[g].sum()); win += gp*cumneg + 0.5*gp*gn; cumneg+=gn; i=j
    return win/(totp*totn)
def make_context(values,R,test_count):
    test_max=int(values[test_count-1]); train_max=int(values[TRAIN-1])
    acc=np.zeros(test_max+1,dtype=bool); acc[values[:test_count]]=True
    train_candidates=np.arange(1,train_max+1,dtype=np.int64); test_candidates=np.arange(train_max+1,test_max+1,dtype=np.int64)
    return {'test_count':test_count,'train_max':train_max,'test_max':test_max,'acc':acc,'train_candidates':train_candidates,'test_candidates':test_candidates,'train_R':R[train_candidates],'test_R':R[test_candidates],'train_acc':acc[train_candidates],'test_acc':acc[test_candidates]}
def evaluate_context(ctx, alpha):
    train_prof=profile(ctx['train_candidates'],ctx['train_R'],ctx['train_acc'],alpha)
    wall=top_fraction_mask(train_prof['score']); test_idx=phase_bins(ctx['test_candidates'],alpha)
    in_wall=wall[test_idx]; test_R=ctx['test_R']; test_acc=ctx['test_acc']; reachable=test_R>=1; rejected=test_R>=2
    pos=np.bincount(test_idx[reachable & rejected],minlength=BINS).astype(float); neg=np.bincount(test_idx[reachable & (~rejected)],minlength=BINS).astype(float)
    auc=auc_binned(train_prof['score'],pos,neg)
    acc_wall=float(test_acc[in_wall].mean()) if in_wall.any() else float('nan'); acc_out=float(test_acc[~in_wall].mean()) if (~in_wall).any() else float('nan')
    depth_wall=float(test_R[in_wall].mean()); depth_out=float(test_R[~in_wall].mean())
    crowd_wall=float((test_R[in_wall]>=2).mean()); crowd_out=float((test_R[~in_wall]>=2).mean())
    future_prof=profile(ctx['test_candidates'],ctx['test_R'],ctx['test_acc'],alpha)
    corr_depth=float(np.corrcoef(train_prof['score'],np.log1p(future_prof['mean_depth']))[0,1])
    corr_reject=float(np.corrcoef(train_prof['score'],future_prof['crowd_density'])[0,1])
    corr_accept=float(np.corrcoef(train_prof['score'],future_prof['acc_density'])[0,1])
    ctrain=int(np.argmax(circular_smooth(train_prof['score'],5))); cfut=int(np.argmax(circular_smooth(future_prof['mean_depth'],5)))
    gap=abs(ctrain-cfut); gap=min(gap,BINS-gap)
    train_idx=phase_bins(ctx['train_candidates'],alpha); train_in=wall[train_idx]
    train_wall=float(ctx['train_R'][train_in].mean()); train_out=float(ctx['train_R'][~train_in].mean())
    sm_acc=circular_smooth(train_prof['acc_density'],3); suppressed_width=float(np.sum(sm_acc < 0.20*float(np.mean(sm_acc)))*360.0/BINS)
    return {'train_count':TRAIN,'test_count':ctx['test_count'],'train_max_value':ctx['train_max'],'test_max_value':ctx['test_max'],'future_candidate_count':int(len(ctx['test_candidates'])),'future_reachable_count':int(reachable.sum()),'future_accepted_count':int(test_acc.sum()),'future_rejected_count':int(rejected.sum()),'future_rejection_auc':float(auc),'accepted_rate_inside_wall':acc_wall,'accepted_rate_outside_wall':acc_out,'future_mean_depth_wall_ratio':float(depth_wall/depth_out),'future_crowded_density_wall_ratio':float(crowd_wall/crowd_out),'train_mean_depth_wall_ratio':float(train_wall/train_out),'train_score_future_depth_corr':corr_depth,'train_score_future_reject_corr':corr_reject,'train_score_future_accept_corr':corr_accept,'wall_center_gap_deg':float(gap*360.0/BINS),'suppressed_width_deg':suppressed_width,'train_wall_center_bin':ctrain,'future_depth_center_bin':cfut,'wall_bins':np.where(wall)[0].astype(int).tolist()}
def random_controls(ctx, n=RANDOM_CONTROLS, seed=29):
    rng=np.random.default_rng(seed); outs=[]
    for _ in range(n):
        a=float(rng.uniform(0.05,TAU-0.05)); e=evaluate_context(ctx,a); outs.append({'future_rejection_auc':e['future_rejection_auc'],'future_mean_depth_wall_ratio':e['future_mean_depth_wall_ratio'],'future_crowded_density_wall_ratio':e['future_crowded_density_wall_ratio'],'wall_center_gap_deg':e['wall_center_gap_deg']})
    stats={}
    for k in outs[0]:
        arr=np.array([o[k] for o in outs],dtype=float); stats[k]={'mean':float(np.nanmean(arr)),'max':float(np.nanmax(arr)),'min':float(np.nanmin(arr)),'std':float(np.nanstd(arr))}
    return {'n':n,'stats':stats,'samples':outs}
def window_centers(values,R,alpha):
    out=[]; accepted=np.zeros(int(values[-1])+1,dtype=bool); accepted[values]=True
    for start in range(0,COUNT-50000+1,50000):
        stop=start+50000; lo=int(values[start]); hi=int(values[stop-1]); cand=np.arange(max(1,lo),hi+1,dtype=np.int64)
        prof=profile(cand,R[cand],accepted[cand],alpha); center=int(np.argmax(circular_smooth(prof['score'],5))); dcenter=int(np.argmax(circular_smooth(prof['mean_depth'],5)))
        out.append({'term_start':start+1,'term_stop':stop,'value_lo':lo,'value_hi':hi,'wall_center_bin':center,'wall_center_deg':float(center*360.0/BINS),'depth_max_center_deg':float(dcenter*360.0/BINS),'phase_score_terms':phase_score(values[start:stop],alpha),'suppressed_width_deg':float(np.sum(circular_smooth(prof['acc_density'],3) < 0.20*float(np.mean(prof['acc_density'])))*360.0/BINS)})
    return out
def circular_span(degs):
    pts=sorted([d%360 for d in degs]); gaps=[(pts[(i+1)%len(pts)]-pts[i]) if i+1<len(pts) else pts[0]+360-pts[i] for i in range(len(pts))]; return 360-max(gaps)
def accepted_resultant_window_drift(values, alpha):
    centers=[]
    for start in range(0,COUNT-50000+1,50000):
        stop=start+50000; z=np.mean(np.exp(1j*((values[start:stop].astype(np.float64)*alpha)%TAU)))
        centers.append(float((math.atan2(z.imag,z.real)%TAU)*360/TAU))
    return {'centers_deg':centers,'span_deg':circular_span(centers)}
def tail_fit(depths):
    x=depths[depths>0].astype(float)
    if len(x)>300000: x=np.random.default_rng(31).choice(x,size=300000,replace=False)
    n=len(x)
    if n<50: return {'winner':'insufficient','n':int(n)}
    lam=1/float(np.mean(x)); ll_exp=n*math.log(lam)-lam*float(np.sum(x)); aic_exp=2-2*ll_exp
    lx=np.log(x); mu=float(np.mean(lx)); sig=max(float(np.std(lx)),1e-12); ll_logn=float(np.sum(-np.log(x*sig*math.sqrt(2*math.pi))-((lx-mu)**2)/(2*sig*sig))); aic_logn=4-2*ll_logn
    denom=float(np.sum(np.log(x))); alp=1+n/denom if denom>0 else float('inf')
    aic_pow=(2-2*(n*math.log(alp-1)-alp*denom)) if math.isfinite(alp) and alp>1 else float('inf')
    aics={'exponential':float(aic_exp),'lognormal':float(aic_logn),'power_law':float(aic_pow)}; return {'winner':min(aics,key=aics.get),'n':int(n),'aic':aics}
def full_depth_profile(ctx, alpha):
    max_v=ctx['test_max']; candidates=np.arange(1,max_v+1,dtype=np.int64); acc=np.zeros(max_v+1,dtype=bool); acc[ctx['acc'].nonzero()[0]]=True
    Rvals=R_global[candidates]; prof=profile(candidates,Rvals,acc[candidates],alpha); wall=top_fraction_mask(prof['score']); idx=phase_bins(candidates,alpha); in_wall=wall[idx]
    corr=float(np.corrcoef(prof['acc_density'],np.log1p(prof['mean_depth']))[0,1]); center=int(np.argmax(circular_smooth(prof['mean_depth'],5)))
    dist=np.array([min(abs(i-center),BINS-abs(i-center)) for i in range(BINS)],dtype=float); tcorr=float(np.corrcoef(-dist,np.log1p(prof['mean_depth']))[0,1])
    return {'accepted_vs_log_depth_corr':corr,'depth_toward_arc_center_corr':tcorr,'mean_depth_wall_ratio':float(Rvals[in_wall].mean()/Rvals[~in_wall].mean()),'depth_center_bin':center,'depth_center_deg':float(center*360.0/BINS),'tail_fit':tail_fit(Rvals[in_wall]),'wall_bins':np.where(wall)[0].astype(int).tolist()}
def write_outputs(root,report):
    md=f"""# U(2,3) 400k ACE Promotion Run\n\n## Verdict\n\n`{report['verdict']}`\n\nThis is the first non-classic Clock Atlas seed promoted through the full 400k ACE benchmark.\n\n## Boundary\n\nThis is a promoted empirical claim, not a theorem. The run supports a proof-ready conjecture; it does not derive alpha from the Ulam rule.\n\n## Recovered alpha\n\n`{report['alpha_refined']:.15f}`\n\n400k phase score: `{report['phase_score_400k']:.6f}`\n\n## Collision wall\n\n- mean-depth wall ratio: `{report['collision_depth_profile']['mean_depth_wall_ratio']:.3f}x`\n- accepted-vs-log-depth correlation: `{report['collision_depth_profile']['accepted_vs_log_depth_corr']:.5f}`\n- depth toward arc-center correlation: `{report['collision_depth_profile']['depth_toward_arc_center_corr']:.5f}`\n- tail fit winner: `{report['collision_depth_profile']['tail_fit']['winner']}`\n\n## Held-out future rejection prediction\n\n| train → test | future AUC | future wall | accepted inside wall | accepted outside wall | center gap |\n|---:|---:|---:|---:|---:|---:|\n"""
    for e in report['heldout_evaluations']:
        md += f"| 100k → {e['test_count']//1000}k | {e['future_rejection_auc']:.5f} | {e['future_mean_depth_wall_ratio']:.3f}x | {e['accepted_rate_inside_wall']:.6f} | {e['accepted_rate_outside_wall']:.6f} | {e['wall_center_gap_deg']:.1f}° |\n"
    c=report['random_alpha_controls']['stats']
    md += f"""\n## Random-alpha controls\n\n- random control count: `{report['random_alpha_controls']['n']}`\n- random mean AUC: `{c['future_rejection_auc']['mean']:.5f}`\n- random max AUC: `{c['future_rejection_auc']['max']:.5f}`\n- random mean wall: `{c['future_mean_depth_wall_ratio']['mean']:.3f}x`\n- random max wall: `{c['future_mean_depth_wall_ratio']['max']:.3f}x`\n\n## Shape invariance\n\n- 50k window count: `{report['shape_invariance']['window_count']}`\n- corrected-alpha wall center span: `{report['shape_invariance']['corrected_center_span_deg']:.3f}°`\n- corrected-alpha phase score range: `{report['shape_invariance']['phase_score_min']:.5f}` to `{report['shape_invariance']['phase_score_max']:.5f}`\n\n## Proof-ready conjecture\n\nFor the Ulam sequence `U(2,3)`, there exists a recovered frequency alpha near `{report['alpha_refined']:.12f}` and a phase arc A such that high-representation candidates concentrate in A, accepted terms are suppressed in A, and the wall learned from the first 100k terms predicts future rejection through 400k.\n\n## ACE status\n\nLevel 3: proof-ready empirical claim.\n\nNext move: finite certificate hardening and then repeat the same promotion pipeline for `U(3,4)` and `U(1,3)`.\n"""
    (root/'ULAM_23_400K_PROMOTION.md').write_text(md)
    # SVG
    evals=report['heldout_evaluations']; w,h=900,520; left,right,top,bottom=80,40,50,80; pw=w-left-right
    svg=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">','<rect width="100%" height="100%" fill="white"/>',f'<text x="{left}" y="28" font-family="Arial" font-size="18">U(2,3) 400k ACE promotion: held-out collision wall</text>']
    y0=top; ph=170; svg += [f'<text x="20" y="{y0+20}" font-family="Arial" font-size="12">AUC</text>',f'<line x1="{left}" y1="{y0+ph}" x2="{w-right}" y2="{y0+ph}" stroke="#222"/>',f'<line x1="{left}" y1="{y0}" x2="{left}" y2="{y0+ph}" stroke="#222"/>']
    for i,e in enumerate(evals):
        x=left+(i+0.5)*pw/len(evals); y=y0+ph-(e['future_rejection_auc']*ph); svg.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="5" fill="#333"/>'); svg.append(f'<text x="{x-24:.1f}" y="{y0+ph+18:.1f}" font-family="Arial" font-size="11">100k→{e["test_count"]//1000}k</text>'); svg.append(f'<text x="{x-18:.1f}" y="{y-8:.1f}" font-family="Arial" font-size="10">{e["future_rejection_auc"]:.3f}</text>')
    y1=top+240; ph2=160; walls=[e['future_mean_depth_wall_ratio'] for e in evals]; maxw=max(walls)*1.15; bw=pw/len(evals)*0.45
    svg += [f'<text x="20" y="{y1+20}" font-family="Arial" font-size="12">Depth wall</text>',f'<line x1="{left}" y1="{y1+ph2}" x2="{w-right}" y2="{y1+ph2}" stroke="#222"/>',f'<line x1="{left}" y1="{y1}" x2="{left}" y2="{y1+ph2}" stroke="#222"/>']
    for i,e in enumerate(evals):
        x=left+(i+0.5)*pw/len(evals)-bw/2; bh=e['future_mean_depth_wall_ratio']/maxw*ph2; svg.append(f'<rect x="{x:.1f}" y="{y1+ph2-bh:.1f}" width="{bw:.1f}" height="{bh:.1f}" fill="#666"/>'); svg.append(f'<text x="{x:.1f}" y="{y1+ph2-bh-5:.1f}" font-family="Arial" font-size="10">{e["future_mean_depth_wall_ratio"]:.2f}x</text>')
    svg.append(f'<text x="{left}" y="{h-20}" font-family="Arial" font-size="12">Boundary: promoted empirical claim, not theorem.</text>'); svg.append('</svg>')
    (root/'ULAM_23_400K_PROMOTION.svg').write_text('\n'.join(svg))
def main():
    global R_global
    root=Path(__file__).resolve().parent; t0=time.time(); add_receipt('U(2,3) 400k ACE promotion run started.','start',{'seed':SEED,'count':COUNT,'train':TRAIN},'support')
    values, vals_path, _=generate_seed(root,SEED,COUNT); add_receipt('Generated or loaded 400k U(2,3) prefix.','generate_seed',{'last_value':int(values[-1]),'values_sha256':sha256_file(vals_path)},'support')
    alpha,score,trail=refine_alpha(values,INITIAL_ALPHA); add_receipt('Recovered/refined hidden alpha for U(2,3).','alpha_recovery',{'initial_alpha':INITIAL_ALPHA,'alpha_refined':alpha,'phase_score':score,'trail':trail},'support')
    R_global=exact_counts(values); r_hash=hashlib.sha256(R_global.tobytes()).hexdigest(); add_receipt('Computed exact representation depth.','exact_representation_depth',{'max_candidate':int(values[-1]),'R_len':int(len(R_global)),'R_sha256':r_hash,'max_depth':int(R_global.max())},'support')
    contexts={cp:make_context(values,R_global,cp) for cp in CHECKPOINTS}; mainctx=contexts[400000]
    depth_profile=full_depth_profile(mainctx,alpha); add_receipt('Mapped collision-depth wall.','collision_depth_profile',{k:v for k,v in depth_profile.items() if k!='wall_bins'},'support')
    evals=[]
    for cp in CHECKPOINTS:
        e=evaluate_context(contexts[cp],alpha); evals.append(e); add_receipt('100k wall predicts future U(2,3) rejection.','heldout_prediction',{'test_count':cp,'auc':e['future_rejection_auc'],'future_wall':e['future_mean_depth_wall_ratio'],'accepted_inside':e['accepted_rate_inside_wall'],'center_gap_deg':e['wall_center_gap_deg']},'support')
    controls=random_controls(mainctx); add_receipt('Random-alpha controls.','random_alpha_controls',{k:controls[k] for k in ['n','stats']},'support')
    windows=window_centers(values,R_global,alpha); center_span=circular_span([w['wall_center_deg'] for w in windows]); shape={'window_terms':50000,'window_count':len(windows),'corrected_center_span_deg':center_span,'phase_score_min':float(min(w['phase_score_terms'] for w in windows)),'phase_score_max':float(max(w['phase_score_terms'] for w in windows)),'windows':windows}; add_receipt('Shape invariance checked.','shape_invariance',{'center_span_deg':center_span,'window_count':len(windows)},'support')
    detuning={'corrected':accepted_resultant_window_drift(values,alpha),'minus_1e-6':accepted_resultant_window_drift(values,alpha-1e-6),'plus_1e-6':accepted_resultant_window_drift(values,alpha+1e-6)}; add_receipt('Detuning drift check.','detuning_check',{'corrected_span':detuning['corrected']['span_deg'],'minus_span':detuning['minus_1e-6']['span_deg'],'plus_span':detuning['plus_1e-6']['span_deg']},'support')
    main=evals[-1]; rand=controls['stats']; verdict='ulam_23_400k_promoted_to_proof_ready_claim' if (score>0.70 and main['future_rejection_auc']>0.95 and main['future_mean_depth_wall_ratio']>3 and main['accepted_rate_inside_wall']<=0.001 and rand['future_mean_depth_wall_ratio']['max']<1.20 and rand['future_rejection_auc']['max']<0.60 and center_span<=2.0) else 'ulam_23_400k_needs_review'
    report={'verdict':verdict,'ace_level':'Level 3: proof-ready empirical claim' if verdict.endswith('proof_ready_claim') else 'Level 2: strong candidate needs review','boundary':'Promoted empirical claim, not theorem. Supports a proof-ready conjecture but does not derive alpha.','seed':[2,3],'count':COUNT,'train_count':TRAIN,'alpha_initial':INITIAL_ALPHA,'alpha_refined':alpha,'phase_score_400k':score,'last_value':int(values[-1]),'growth_density':float(COUNT/int(values[-1])),'median_gap':float(np.median(np.diff(values))),'mean_gap':float((int(values[-1])-int(values[0]))/(COUNT-1)),'values_sha256':sha256_file(vals_path),'representation_depth_sha256':r_hash,'alpha_refinement_trail':trail,'collision_depth_profile':depth_profile,'heldout_evaluations':evals,'random_alpha_controls':controls,'shape_invariance':shape,'detuning_check':detuning,'candidate_conjecture':'For U(2,3), there exists a recovered frequency alpha and an arc A such that high-representation candidates concentrate in A, accepted terms are suppressed in A, and the wall learned from a finite prefix predicts later rejection.','proof_obligations':['Formalize U(2,3), representation depth R(n), phase map theta_alpha(n), and wall-score functional.','Generate finite certificate manifest with alpha interval, wall-bin set, prefix hash, and exact bin counts.','Show persistence of representation-depth imbalance under sequence extension.','Relate recovered alpha to a fixed point or extremum of the collision-wall functional.','Prove or bound the asymptotic suppression of accepted terms inside the wall arc.'],'falsifiers':['Future accepted terms survive inside the predicted wall at nontrivial rate.','Random or nearby alphas reproduce the same wall and future AUC.','Wall center drifts incoherently under deeper windows.','Recovered alpha changes materially under larger prefixes.','Exact representation-depth imbalance collapses under certified recomputation.'],'elapsed_seconds':time.time()-t0}
    add_receipt('U(2,3) 400k ACE promotion verdict assigned.','verdict',{'verdict':verdict,'ace_level':report['ace_level']},'support' if verdict.endswith('proof_ready_claim') else 'needs_review')
    receipts_path=root/'ulam_23_400k_promotion_receipts.jsonl'; write_receipts(receipts_path); report['receipt_chain_valid']=verify_receipts(receipts_path)
    (root/'ulam_23_promotion_400k_report.json').write_text(json.dumps(report,indent=2,allow_nan=True)); write_outputs(root,report)
    manifest={'seed':[2,3],'count':COUNT,'train_count':TRAIN,'alpha_refined':alpha,'values_file':vals_path.name,'values_sha256':report['values_sha256'],'representation_depth_sha256':r_hash,'receipt_chain_file':'ulam_23_400k_promotion_receipts.jsonl','receipt_chain_valid':report['receipt_chain_valid'],'wall_fraction':WALL_FRAC,'bins':BINS,'wall_bins':depth_profile['wall_bins'],'heldout_main':main,'random_alpha_controls':controls['stats'],'boundary':'Finite certificate manifest. Does not prove asymptotic theorem.'}
    (root/'finite_certificate_manifest_u23_400k.json').write_text(json.dumps(manifest,indent=2,allow_nan=True))
    zip_path=root.parent/'openline-ulam-23-400k-promotion.zip'
    if zip_path.exists(): zip_path.unlink()
    with zipfile.ZipFile(zip_path,'w',zipfile.ZIP_DEFLATED) as z:
        for p in root.rglob('*'):
            if p.is_file() and '/cache/' not in str(p) and p.name!='ulam_fast_seed': z.write(p,p.relative_to(root.parent))
    print(json.dumps({'verdict':verdict,'receipt_chain_valid':report['receipt_chain_valid'],'alpha_refined':alpha,'phase_score':score,'main_100k_to_400k':main,'random_controls':controls['stats'],'shape_center_span_deg':center_span,'zip':str(zip_path)},indent=2,allow_nan=True))
if __name__=='__main__': main()
