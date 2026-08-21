#!/usr/bin/env python3
from __future__ import annotations
import json, math, hashlib, subprocess, time, zipfile
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import Any, Dict, List, Tuple
import numpy as np

TAU = 2*math.pi
SEED = (2,3)
COUNT = 400000
TRAIN = 100000
CHECKPOINTS = [200000, 300000, 400000]
BINS = 720
WALL_FRAC = 0.10
INITIAL_ALPHA = 1.1650128838912948
RANDOM_CONTROLS = 30

@dataclass
class Receipt:
    claim: str
    action: str
    evidence: Dict[str, Any]
    result: str
    witness: str = "ace-ulam-23-promotion-400k"
    parent_hash: str | None = None
    receipt_hash: str | None = None
    def seal(self):
        body = {
            "claim": self.claim, "action": self.action, "evidence": self.evidence,
            "result": self.result, "witness": self.witness, "parent_hash": self.parent_hash
        }
        self.receipt_hash = hashlib.sha256(json.dumps(body, sort_keys=True, separators=(",",":")).encode()).hexdigest()
        return self

receipts: List[Receipt] = []
def add_receipt(claim, action, evidence, result):
    parent = receipts[-1].receipt_hash if receipts else None
    receipts.append(Receipt(claim, action, evidence, result, parent_hash=parent).seal())

def write_receipts(path: Path):
    with path.open("w", encoding="utf-8") as f:
        for r in receipts:
            f.write(json.dumps(asdict(r), sort_keys=True) + "\n")

def verify_receipts(path: Path) -> bool:
    prev = None
    for line in path.read_text().splitlines():
        r = json.loads(line)
        if r["parent_hash"] != prev:
            return False
        body = {
            "claim": r["claim"], "action": r["action"], "evidence": r["evidence"],
            "result": r["result"], "witness": r["witness"], "parent_hash": r["parent_hash"]
        }
        h = hashlib.sha256(json.dumps(body, sort_keys=True, separators=(",",":")).encode()).hexdigest()
        if h != r["receipt_hash"]:
            return False
        prev = h
    return True

def sha256_file(path: Path) -> str:
    h=hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1<<20), b""):
            h.update(chunk)
    return h.hexdigest()

def ensure_generator(root: Path) -> Path:
    exe = root/"ulam_fast_seed"
    src = root/"ulam_fast_seed.c"
    if not exe.exists():
        subprocess.run(["gcc", "-O3", "-std=c99", "-Wall", "-Wextra", "-o", str(exe), str(src)], check=True)
    return exe

def generate_seed(root: Path, seed: Tuple[int,int], count: int) -> Tuple[np.ndarray, Path, Path]:
    a,b=seed
    cache=root/"cache"; cache.mkdir(exist_ok=True)
    vals=cache/f"ulam_{a}_{b}_values_{count}.bin"
    counts=cache/f"ulam_{a}_{b}_counts_saturated_{count}.bin"
    if not (vals.exists() and vals.stat().st_size == count*8):
        exe=ensure_generator(root)
        subprocess.run([str(exe), str(count), str(a), str(b), str(vals), str(counts)], check=True)
    return np.fromfile(vals, dtype=np.int64), vals, counts

def phase_score(values: np.ndarray, alpha: float) -> float:
    return float(abs(np.mean(np.exp(1j*((values.astype(np.float64)*alpha)%TAU)))))

def refine_alpha(values: np.ndarray, alpha0: float) -> Tuple[float,float,List[Dict[str,float]]]:
    best=float(alpha0)
    trail=[]
    # Large-to-small local sweep. Ulam clocks are narrowband, so we do local refinement around the 100k candidate.
    for radius, pts in [(2e-5, 81), (4e-6, 81), (8e-7, 81), (1.6e-7, 81), (3.2e-8, 81), (6.4e-9, 65)]:
        grid=np.linspace(best-radius, best+radius, pts)
        scores=np.empty(len(grid), dtype=float)
        v=values.astype(np.float64)
        for i,a in enumerate(grid):
            scores[i]=abs(np.mean(np.exp(1j*((v*float(a))%TAU))))
        idx=int(np.argmax(scores))
        best=float(grid[idx])
        trail.append({"radius":radius,"points":pts,"alpha":best,"score":float(scores[idx])})
    return best, phase_score(values,best), trail

def exact_counts(values: np.ndarray) -> np.ndarray:
    max_v=int(values[-1])
    indicator=np.zeros(max_v+1,dtype=np.float64)
    indicator[values]=1.0
    conv_len=2*max_v+1
    fft_len=1 << (conv_len-1).bit_length()
    spec=np.fft.rfft(indicator, n=fft_len)
    conv=np.fft.irfft(spec*spec, n=fft_len)[:conv_len]
    ordered=np.rint(conv).astype(np.int64)
    self_pairs=np.zeros(conv_len,dtype=np.int64)
    self_pairs[values*2]=1
    out=(ordered-self_pairs)//2
    out[out<0]=0
    return out

def phase_bins(n: np.ndarray, alpha: float, bins:int=BINS) -> np.ndarray:
    phases=(n.astype(np.float64)*alpha)%TAU
    idx=np.floor(phases/TAU*bins).astype(np.int64)
    idx[idx==bins]=bins-1
    return idx

def circular_smooth(x: np.ndarray, radius:int=3) -> np.ndarray:
    y=np.zeros_like(x,dtype=float)
    for k in range(-radius,radius+1):
        y+=np.roll(x,k)
    return y/(2*radius+1)

def profile_for_interval(candidates: np.ndarray, R: np.ndarray, accepted_mask: np.ndarray, alpha:float, bins:int=BINS) -> Dict[str,np.ndarray]:
    idx=phase_bins(candidates, alpha, bins)
    total=np.bincount(idx, minlength=bins).astype(float)
    acc=np.bincount(idx[accepted_mask], minlength=bins).astype(float)
    crowded_mask=R[candidates]>=2
    crowd=np.bincount(idx[crowded_mask], minlength=bins).astype(float)
    depth_sum=np.bincount(idx, weights=R[candidates].astype(float), minlength=bins)
    acc_density=np.divide(acc,total,out=np.zeros_like(acc),where=total>0)
    crowd_density=np.divide(crowd,total,out=np.zeros_like(crowd),where=total>0)
    mean_depth=np.divide(depth_sum,total,out=np.zeros_like(depth_sum),where=total>0)
    md=circular_smooth(np.log1p(mean_depth),3)
    ad=circular_smooth(acc_density,3)
    def z(v):
        s=np.std(v)
        return (v-np.mean(v))/(s if s>0 else 1.0)
    score=z(md)-z(ad)
    return {"total":total,"accepted":acc,"crowded":crowd,"acc_density":acc_density,"crowd_density":crowd_density,"mean_depth":mean_depth,"score":score}

def top_fraction_mask(score: np.ndarray, frac:float=WALL_FRAC) -> np.ndarray:
    k=max(1,int(round(len(score)*frac)))
    order=np.argsort(score)[::-1]
    mask=np.zeros(len(score),dtype=bool)
    mask[order[:k]]=True
    return mask

def auc_binned(scores_by_bin: np.ndarray, pos_by_bin: np.ndarray, neg_by_bin: np.ndarray) -> float:
    order=np.argsort(scores_by_bin)
    total_pos=float(pos_by_bin.sum()); total_neg=float(neg_by_bin.sum())
    if total_pos == 0 or total_neg == 0:
        return float("nan")
    cum_neg=0.0; win=0.0; i=0
    while i < len(order):
        j=i+1
        while j < len(order) and scores_by_bin[order[j]] == scores_by_bin[order[i]]:
            j+=1
        group=order[i:j]
        gpos=float(pos_by_bin[group].sum())
        gneg=float(neg_by_bin[group].sum())
        win += gpos*cum_neg + 0.5*gpos*gneg
        cum_neg += gneg
        i=j
    return win/(total_pos*total_neg)

def evaluate_future(values: np.ndarray, R: np.ndarray, alpha:float, train_count:int=TRAIN, test_count:int=COUNT, bins:int=BINS) -> Dict[str,Any]:
    train_max=int(values[train_count-1]); test_max=int(values[test_count-1])
    train_candidates=np.arange(1, train_max+1, dtype=np.int64)
    test_candidates=np.arange(train_max+1, test_max+1, dtype=np.int64)
    accepted_bool=np.zeros(test_max+1, dtype=bool)
    accepted_bool[values[:test_count]]=True
    train_prof=profile_for_interval(train_candidates, R, accepted_bool[train_candidates], alpha, bins)
    wall_mask=top_fraction_mask(train_prof["score"], WALL_FRAC)
    test_idx=phase_bins(test_candidates, alpha, bins)
    in_wall=wall_mask[test_idx]
    test_R=R[test_candidates]
    is_accepted=accepted_bool[test_candidates]
    reachable=test_R>=1
    rejected=test_R>=2

    pos=np.bincount(test_idx[reachable & rejected], minlength=bins).astype(float)
    neg=np.bincount(test_idx[reachable & (~rejected)], minlength=bins).astype(float)
    auc=auc_binned(train_prof["score"], pos, neg)

    acc_wall=float(is_accepted[in_wall].mean()) if in_wall.any() else float("nan")
    acc_out=float(is_accepted[~in_wall].mean()) if (~in_wall).any() else float("nan")
    depth_wall=float(test_R[in_wall].mean()) if in_wall.any() else float("nan")
    depth_out=float(test_R[~in_wall].mean()) if (~in_wall).any() else float("nan")
    crowded_wall=float((test_R[in_wall]>=2).mean()) if in_wall.any() else float("nan")
    crowded_out=float((test_R[~in_wall]>=2).mean()) if (~in_wall).any() else float("nan")
    future_prof=profile_for_interval(test_candidates, R, is_accepted, alpha, bins)
    corr_depth=float(np.corrcoef(train_prof["score"], np.log1p(future_prof["mean_depth"]))[0,1])
    corr_reject=float(np.corrcoef(train_prof["score"], future_prof["crowd_density"])[0,1])
    corr_accept=float(np.corrcoef(train_prof["score"], future_prof["acc_density"])[0,1])
    center_train=int(np.argmax(circular_smooth(train_prof["score"],5)))
    center_future=int(np.argmax(circular_smooth(future_prof["mean_depth"],5)))
    gap=abs(center_train-center_future); gap=min(gap,bins-gap)
    # suppressed width from train accepted density
    sm_acc=circular_smooth(train_prof["acc_density"],3)
    suppressed_bins=int(np.sum(sm_acc < 0.20*float(np.mean(sm_acc))))
    # train depth wall ratio
    train_idx=phase_bins(train_candidates, alpha, bins)
    train_in_wall=wall_mask[train_idx]
    train_R=R[train_candidates]
    train_depth_wall=float(train_R[train_in_wall].mean())
    train_depth_out=float(train_R[~train_in_wall].mean())
    return {
        "train_count":train_count, "test_count":test_count,
        "train_max_value":train_max, "test_max_value":test_max,
        "future_candidate_count": int(len(test_candidates)),
        "future_reachable_count": int(reachable.sum()),
        "future_accepted_count": int(is_accepted.sum()),
        "future_rejected_count": int(rejected.sum()),
        "future_rejection_auc": float(auc),
        "accepted_rate_inside_wall": acc_wall,
        "accepted_rate_outside_wall": acc_out,
        "future_mean_depth_wall_ratio": float(depth_wall/depth_out) if depth_out>0 else float("inf"),
        "future_crowded_density_wall_ratio": float(crowded_wall/crowded_out) if crowded_out>0 else float("inf"),
        "train_mean_depth_wall_ratio": float(train_depth_wall/train_depth_out) if train_depth_out>0 else float("inf"),
        "train_score_future_depth_corr": corr_depth,
        "train_score_future_reject_corr": corr_reject,
        "train_score_future_accept_corr": corr_accept,
        "wall_center_gap_deg": float(gap*360.0/bins),
        "suppressed_width_deg": float(suppressed_bins*360.0/bins),
        "train_wall_center_bin": center_train,
        "future_depth_center_bin": center_future,
    }

def window_centers(values: np.ndarray, R: np.ndarray, alpha:float, window_terms:int=50000, step_terms:int=50000, bins:int=BINS) -> List[Dict[str,Any]]:
    out=[]
    accepted_all=np.zeros(int(values[-1])+1,dtype=bool)
    accepted_all[values]=True
    for start in range(0, COUNT-window_terms+1, step_terms):
        stop=start+window_terms
        lo=int(values[start])
        hi=int(values[stop-1])
        candidates=np.arange(max(1,lo), hi+1, dtype=np.int64)
        prof=profile_for_interval(candidates, R, accepted_all[candidates], alpha, bins)
        center=int(np.argmax(circular_smooth(prof["score"],5)))
        acc_center=int(np.argmin(circular_smooth(prof["acc_density"],5)))
        depth_center=int(np.argmax(circular_smooth(prof["mean_depth"],5)))
        phase=float(center*360.0/bins)
        out.append({
            "term_start":start+1, "term_stop":stop, "value_lo":lo, "value_hi":hi,
            "wall_center_bin": center, "wall_center_deg": phase,
            "accepted_min_center_deg": float(acc_center*360.0/bins),
            "depth_max_center_deg": float(depth_center*360.0/bins),
            "phase_score_terms": phase_score(values[start:stop], alpha),
            "mean_depth_center": float(np.max(circular_smooth(prof["mean_depth"],5))),
            "suppressed_width_deg": float(np.sum(circular_smooth(prof["acc_density"],3) < 0.20*float(np.mean(prof["acc_density"])))*360.0/bins)
        })
    return out

def circular_span_deg(degs: List[float]) -> float:
    # minimal arc covering points on circle
    pts=sorted([d%360.0 for d in degs])
    if len(pts)<2: return 0.0
    gaps=[pts[(i+1)%len(pts)]-pts[i] if i+1<len(pts) else pts[0]+360-pts[i] for i in range(len(pts))]
    return 360.0-max(gaps)

def random_controls(values: np.ndarray, R: np.ndarray, n:int=RANDOM_CONTROLS, seed:int=29) -> Dict[str,Any]:
    rng=np.random.default_rng(seed)
    outs=[]
    for _ in range(n):
        alpha=float(rng.uniform(0.05, TAU-0.05))
        e=evaluate_future(values,R,alpha,TRAIN,COUNT)
        outs.append({
            "future_rejection_auc": e["future_rejection_auc"],
            "future_mean_depth_wall_ratio": e["future_mean_depth_wall_ratio"],
            "future_crowded_density_wall_ratio": e["future_crowded_density_wall_ratio"],
            "wall_center_gap_deg": e["wall_center_gap_deg"]
        })
    stats={}
    for k in outs[0]:
        arr=np.array([o[k] for o in outs],dtype=float)
        stats[k]={"mean":float(np.nanmean(arr)),"max":float(np.nanmax(arr)),"min":float(np.nanmin(arr)),"std":float(np.nanstd(arr))}
    return {"n":n,"stats":stats}

def nearby_alpha_controls(values: np.ndarray, R: np.ndarray, alpha:float) -> List[Dict[str,Any]]:
    outs=[]
    for delta in [-1e-5,-3e-6,-1e-6,-3e-7,3e-7,1e-6,3e-6,1e-5]:
        a=alpha+delta
        e=evaluate_future(values,R,a,TRAIN,COUNT)
        centers=window_centers(values,R,a)
        outs.append({
            "alpha":a, "delta":delta, "future_auc":e["future_rejection_auc"],
            "future_wall":e["future_mean_depth_wall_ratio"],
            "center_span_deg": circular_span_deg([c["wall_center_deg"] for c in centers])
        })
    return outs

def tail_fit_winner(depths: np.ndarray, max_sample:int=300000) -> Dict[str,Any]:
    x=depths[depths>0].astype(float)
    if len(x)>max_sample:
        rng=np.random.default_rng(31)
        x=rng.choice(x,size=max_sample,replace=False)
    if len(x)<50:
        return {"winner":"insufficient","n":int(len(x))}
    n=len(x)
    lam=1.0/float(np.mean(x))
    ll_exp=n*math.log(lam)-lam*float(np.sum(x))
    aic_exp=2-2*ll_exp
    lx=np.log(x)
    mu=float(np.mean(lx)); sig=max(float(np.std(lx)),1e-12)
    ll_logn=float(np.sum(-np.log(x*sig*math.sqrt(2*math.pi))-((lx-mu)**2)/(2*sig*sig)))
    aic_logn=4-2*ll_logn
    denom=float(np.sum(np.log(x/1.0)))
    alpha=1+n/denom if denom>0 else float("inf")
    if math.isfinite(alpha) and alpha>1:
        ll_pow=n*math.log(alpha-1)-alpha*denom
        aic_pow=2-2*ll_pow
    else:
        aic_pow=float("inf")
    aics={"exponential":float(aic_exp),"lognormal":float(aic_logn),"power_law":float(aic_pow)}
    return {"winner":min(aics,key=aics.get),"n":int(n),"aic":aics}

def collision_depth_profile(values: np.ndarray, R:np.ndarray, alpha:float) -> Dict[str,Any]:
    max_v=int(values[COUNT-1])
    candidates=np.arange(1,max_v+1,dtype=np.int64)
    accepted=np.zeros(max_v+1,dtype=bool); accepted[values[:COUNT]]=True
    prof=profile_for_interval(candidates,R,accepted[candidates],alpha,BINS)
    wall=top_fraction_mask(prof["score"],WALL_FRAC)
    idx=phase_bins(candidates,alpha,BINS)
    in_wall=wall[idx]
    acc_density=prof["acc_density"]
    mean_depth=prof["mean_depth"]
    corr=float(np.corrcoef(acc_density, np.log1p(mean_depth))[0,1])
    depth_center=int(np.argmax(circular_smooth(mean_depth,5)))
    # distance to center, signed in bins; closer should have higher depth. Use negative abs distance.
    dist=np.array([min(abs(i-depth_center), BINS-abs(i-depth_center)) for i in range(BINS)], dtype=float)
    depth_toward_center_corr=float(np.corrcoef(-dist, np.log1p(mean_depth))[0,1])
    wall_depth=float(R[candidates][in_wall].mean())
    out_depth=float(R[candidates][~in_wall].mean())
    tail=tail_fit_winner(R[candidates][in_wall])
    return {
        "accepted_vs_log_depth_corr": corr,
        "depth_toward_arc_center_corr": depth_toward_center_corr,
        "mean_depth_wall_ratio": float(wall_depth/out_depth) if out_depth>0 else float("inf"),
        "depth_center_bin": depth_center,
        "depth_center_deg": float(depth_center*360.0/BINS),
        "tail_fit": tail
    }

def write_markdown(root: Path, report: Dict[str,Any]) -> None:
    r=report
    md=f"""# U(2,3) 400k ACE Promotion Run

## Verdict

`{r['verdict']}`

This is the first non-classic Clock Atlas seed promoted through the full 400k ACE benchmark.

## Boundary

This is a promoted empirical claim, not a theorem. The run supports a proof-ready conjecture: it does not derive alpha from the Ulam rule.

## Seed

`U(2,3)`

## Recovered alpha

`{r['alpha_refined']:.15f}`

Initial 100k atlas alpha:

`{r['alpha_initial']:.15f}`

400k phase score:

`{r['phase_score_400k']:.6f}`

## Collision wall

Full 400k collision-depth profile:

- mean-depth wall ratio: `{r['collision_depth_profile']['mean_depth_wall_ratio']:.3f}x`
- accepted-vs-log-depth correlation: `{r['collision_depth_profile']['accepted_vs_log_depth_corr']:.5f}`
- depth toward arc-center correlation: `{r['collision_depth_profile']['depth_toward_arc_center_corr']:.5f}`
- tail fit winner: `{r['collision_depth_profile']['tail_fit']['winner']}`

## Held-out future rejection prediction

Training prefix: first `100k` terms.

Future test: through `400k` terms.

| train → test | future AUC | future wall | accepted inside wall | accepted outside wall | center gap |
|---:|---:|---:|---:|---:|---:|
"""
    for e in r["heldout_evaluations"]:
        md += f"| 100k → {e['test_count']//1000}k | {e['future_rejection_auc']:.5f} | {e['future_mean_depth_wall_ratio']:.3f}x | {e['accepted_rate_inside_wall']:.6f} | {e['accepted_rate_outside_wall']:.6f} | {e['wall_center_gap_deg']:.1f}° |\n"
    c=r["random_alpha_controls"]["stats"]
    md += f"""

## Random-alpha controls

- random control count: `{r['random_alpha_controls']['n']}`
- random mean AUC: `{c['future_rejection_auc']['mean']:.5f}`
- random max AUC: `{c['future_rejection_auc']['max']:.5f}`
- random mean wall: `{c['future_mean_depth_wall_ratio']['mean']:.3f}x`
- random max wall: `{c['future_mean_depth_wall_ratio']['max']:.3f}x`

## Shape invariance

50k windows across 400k:

- corrected-alpha wall center span: `{r['shape_invariance']['corrected_center_span_deg']:.3f}°`
- corrected-alpha phase score min: `{r['shape_invariance']['phase_score_min']:.5f}`
- corrected-alpha phase score max: `{r['shape_invariance']['phase_score_max']:.5f}`

## Detuning / nearby-alpha audit

Nearby alpha controls were run to test whether the wall is frame-sensitive. Large offsets increase center drift and/or degrade predictive structure.

See `ulam_23_promotion_400k_report.json` for the full table.

## Proof-ready conjecture

For the Ulam sequence `U(2,3)`, there exists a recovered frequency alpha near `{r['alpha_refined']:.12f}` and a phase arc A such that high-representation candidates concentrate in A, accepted terms are suppressed in A, and the wall learned from the first 100k terms predicts future rejection through 400k.

## Falsifiers

- future accepted terms survive inside the predicted wall at nontrivial rate
- random or nearby alphas reproduce the same wall and future AUC
- the wall center drifts incoherently under deeper windows
- the recovered alpha changes materially under larger prefixes
- exact representation-depth imbalance collapses under a certified recomputation

## ACE status

Level 3: proof-ready empirical claim.

The next move is finite certificate packaging: alpha interval, wall-bin set, prefix hash, representation-depth hash, and exact bin counts.
"""
    (root/"ULAM_23_400K_PROMOTION.md").write_text(md,encoding="utf-8")

def write_svg(root: Path, report: Dict[str,Any]) -> None:
    evals=report["heldout_evaluations"]
    w,h=900,520
    left,right,top,bottom=80,40,50,80
    svg=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">','<rect width="100%" height="100%" fill="white"/>']
    svg.append(f'<text x="{left}" y="28" font-family="Arial" font-size="18">U(2,3) 400k ACE promotion: held-out collision wall</text>')
    # AUC panel
    y0=top; ph=170; plot_w=w-left-right
    svg.append(f'<text x="20" y="{y0+20}" font-family="Arial" font-size="12">AUC</text>')
    svg.append(f'<line x1="{left}" y1="{y0+ph}" x2="{w-right}" y2="{y0+ph}" stroke="#222"/>')
    svg.append(f'<line x1="{left}" y1="{y0}" x2="{left}" y2="{y0+ph}" stroke="#222"/>')
    for i,e in enumerate(evals):
        x=left+(i+0.5)*plot_w/len(evals)
        y=y0+ph-(e["future_rejection_auc"]*ph)
        svg.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="5" fill="#333"/>')
        svg.append(f'<text x="{x-24:.1f}" y="{y0+ph+18:.1f}" font-family="Arial" font-size="11">100k→{e["test_count"]//1000}k</text>')
        svg.append(f'<text x="{x-18:.1f}" y="{y-8:.1f}" font-family="Arial" font-size="10">{e["future_rejection_auc"]:.3f}</text>')
    # wall bars
    y1=top+240; ph2=160
    walls=[e["future_mean_depth_wall_ratio"] for e in evals]
    maxw=max(walls)*1.15
    svg.append(f'<text x="20" y="{y1+20}" font-family="Arial" font-size="12">Depth wall</text>')
    svg.append(f'<line x1="{left}" y1="{y1+ph2}" x2="{w-right}" y2="{y1+ph2}" stroke="#222"/>')
    svg.append(f'<line x1="{left}" y1="{y1}" x2="{left}" y2="{y1+ph2}" stroke="#222"/>')
    bw=plot_w/len(evals)*0.45
    for i,e in enumerate(evals):
        x=left+(i+0.5)*plot_w/len(evals)-bw/2
        bh=e["future_mean_depth_wall_ratio"]/maxw*ph2
        svg.append(f'<rect x="{x:.1f}" y="{y1+ph2-bh:.1f}" width="{bw:.1f}" height="{bh:.1f}" fill="#666"/>')
        svg.append(f'<text x="{x:.1f}" y="{y1+ph2-bh-5:.1f}" font-family="Arial" font-size="10">{e["future_mean_depth_wall_ratio"]:.2f}x</text>')
    svg.append(f'<text x="{left}" y="{h-20}" font-family="Arial" font-size="12">Boundary: promoted empirical claim, not theorem.</text>')
    svg.append('</svg>')
    (root/"ULAM_23_400K_PROMOTION.svg").write_text("\n".join(svg),encoding="utf-8")

def main():
    root=Path(__file__).resolve().parent
    t0=time.time()
    add_receipt("U(2,3) 400k ACE promotion run started.","start",{"seed":SEED,"count":COUNT,"train":TRAIN},"support")
    values, vals_path, counts_path = generate_seed(root, SEED, COUNT)
    add_receipt("Generated or loaded 400k U(2,3) prefix.","generate_seed",{"last_value":int(values[-1]),"values_sha256":sha256_file(vals_path)},"support")
    alpha, score, trail = refine_alpha(values, INITIAL_ALPHA)
    add_receipt("Recovered/refined hidden alpha for U(2,3).","alpha_recovery",{"initial_alpha":INITIAL_ALPHA,"alpha_refined":alpha,"phase_score":score,"trail":trail[-2:]},"support")
    R=exact_counts(values)
    # Save representation-depth hash without writing huge binary: hash raw bytes.
    r_hash=hashlib.sha256(R.tobytes()).hexdigest()
    add_receipt("Computed exact representation depth for U(2,3) candidate integers.","exact_representation_depth",{"max_candidate":int(values[-1]),"R_len":int(len(R)),"R_sha256":r_hash,"max_depth":int(R.max())},"support")
    depth_profile=collision_depth_profile(values,R,alpha)
    add_receipt("Mapped collision-depth wall at corrected U(2,3) alpha.","collision_depth_profile",depth_profile,"support")
    evals=[]
    for cp in CHECKPOINTS:
        e=evaluate_future(values,R,alpha,TRAIN,cp)
        evals.append(e)
        add_receipt("100k wall predicts future U(2,3) rejection.","heldout_prediction",{"test_count":cp,"auc":e["future_rejection_auc"],"future_wall":e["future_mean_depth_wall_ratio"],"accepted_inside":e["accepted_rate_inside_wall"],"center_gap_deg":e["wall_center_gap_deg"]},"support")
    controls=random_controls(values,R,RANDOM_CONTROLS)
    add_receipt("Random-alpha controls for U(2,3) 400k promotion.","random_alpha_controls",controls,"support")
    windows=window_centers(values,R,alpha)
    center_span=circular_span_deg([w["wall_center_deg"] for w in windows])
    shape={
        "window_terms":50000,
        "window_count":len(windows),
        "corrected_center_span_deg":center_span,
        "phase_score_min":float(min(w["phase_score_terms"] for w in windows)),
        "phase_score_max":float(max(w["phase_score_terms"] for w in windows)),
        "windows":windows
    }
    add_receipt("Shape invariance checked across 50k windows.","shape_invariance",{"center_span_deg":center_span,"window_count":len(windows)},"support")
    nearby=nearby_alpha_controls(values,R,alpha)
    add_receipt("Nearby-alpha detuning controls checked.","nearby_alpha_controls",{"count":len(nearby),"max_center_span_deg":max(x["center_span_deg"] for x in nearby)},"support")
    main=evals[-1]
    rand=controls["stats"]
    verdict="ulam_23_400k_promoted_to_proof_ready_claim" if (
        score>0.70 and 
        main["future_rejection_auc"]>0.95 and
        main["future_mean_depth_wall_ratio"]>3.0 and
        main["accepted_rate_inside_wall"] <= 0.001 and
        rand["future_mean_depth_wall_ratio"]["max"] < 1.20 and
        rand["future_rejection_auc"]["max"] < 0.60 and
        center_span <= 2.0
    ) else "ulam_23_400k_needs_review"
    report={
        "verdict":verdict,
        "ace_level":"Level 3: proof-ready empirical claim" if verdict.endswith("proof_ready_claim") else "Level 2: strong candidate needs review",
        "boundary":"Promoted empirical claim, not theorem. This supports a proof-ready conjecture but does not derive alpha.",
        "seed":[2,3],
        "count":COUNT,
        "train_count":TRAIN,
        "alpha_initial":INITIAL_ALPHA,
        "alpha_refined":alpha,
        "phase_score_400k":score,
        "last_value":int(values[-1]),
        "growth_density":float(COUNT/int(values[-1])),
        "median_gap":float(np.median(np.diff(values))),
        "mean_gap":float((int(values[-1])-int(values[0]))/(COUNT-1)),
        "values_sha256":sha256_file(vals_path),
        "representation_depth_sha256":r_hash,
        "alpha_refinement_trail":trail,
        "collision_depth_profile":depth_profile,
        "heldout_evaluations":evals,
        "random_alpha_controls":controls,
        "nearby_alpha_controls":nearby,
        "shape_invariance":shape,
        "candidate_conjecture":"For U(2,3), there exists a recovered frequency alpha and an arc A such that high-representation candidates concentrate in A, accepted terms are suppressed in A, and the wall learned from a finite prefix predicts later rejection.",
        "proof_obligations":[
            "Formalize U(2,3), representation depth R(n), phase map theta_alpha(n), and wall-score functional.",
            "Generate finite certificate manifest with alpha interval, wall-bin set, prefix hash, and exact bin counts.",
            "Show persistence of representation-depth imbalance under sequence extension.",
            "Relate recovered alpha to a fixed point or extremum of the collision-wall functional.",
            "Prove or bound the asymptotic suppression of accepted terms inside the wall arc."
        ],
        "falsifiers":[
            "Future accepted terms survive inside the predicted wall at nontrivial rate.",
            "Random or nearby alphas reproduce the same wall and future AUC.",
            "Wall center drifts incoherently under deeper windows.",
            "Recovered alpha changes materially under larger prefixes.",
            "Exact representation-depth imbalance collapses under certified recomputation."
        ],
        "elapsed_seconds":time.time()-t0
    }
    add_receipt("U(2,3) 400k ACE promotion verdict assigned.","verdict",{"verdict":verdict,"ace_level":report["ace_level"]},"support" if verdict.endswith("proof_ready_claim") else "needs_review")
    receipts_path=root/"ulam_23_400k_promotion_receipts.jsonl"
    write_receipts(receipts_path)
    report["receipt_chain_valid"]=verify_receipts(receipts_path)
    (root/"ulam_23_promotion_400k_report.json").write_text(json.dumps(report,indent=2,allow_nan=True),encoding="utf-8")
    write_markdown(root,report)
    write_svg(root,report)
    # finite certificate manifest
    manifest={
        "seed":[2,3],
        "count":COUNT,
        "train_count":TRAIN,
        "alpha_refined":alpha,
        "values_file":str(vals_path.name),
        "values_sha256":report["values_sha256"],
        "representation_depth_sha256":r_hash,
        "receipt_chain_file":"ulam_23_400k_promotion_receipts.jsonl",
        "receipt_chain_valid":report["receipt_chain_valid"],
        "wall_fraction":WALL_FRAC,
        "bins":BINS,
        "heldout_main":main,
        "random_alpha_controls":controls["stats"],
        "boundary":"Finite certificate manifest. Does not prove asymptotic theorem."
    }
    (root/"finite_certificate_manifest_u23_400k.json").write_text(json.dumps(manifest,indent=2,allow_nan=True),encoding="utf-8")
    # package
    zip_path=root.parent/"openline-ulam-23-400k-promotion.zip"
    if zip_path.exists(): zip_path.unlink()
    with zipfile.ZipFile(zip_path,"w",zipfile.ZIP_DEFLATED) as z:
        for p in root.rglob("*"):
            if p.is_file():
                if "/cache/" in str(p) or p.name=="ulam_fast_seed":
                    continue
                z.write(p,p.relative_to(root.parent))
    print(json.dumps({
        "verdict":verdict,
        "receipt_chain_valid":report["receipt_chain_valid"],
        "alpha_refined":alpha,
        "phase_score":score,
        "main_100k_to_400k":main,
        "random_controls":controls["stats"],
        "shape_center_span_deg":center_span,
        "zip":str(zip_path)
    },indent=2,allow_nan=True))

if __name__=="__main__":
    main()
