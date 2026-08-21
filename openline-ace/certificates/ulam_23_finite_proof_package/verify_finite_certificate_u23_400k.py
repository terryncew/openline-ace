#!/usr/bin/env python3
"""
Verify finite certificate for U(2,3), N=400000.

This verifier checks a finite computational claim, not the infinite theorem.

It loads the accepted-prefix binary, verifies the U(2,3) greedy unique-sum rule
against saturated counts, recomputes exact representation depth by convolution,
learns the wall only from the first 100k terms, and recomputes the held-out
metrics through 400k.
"""
from __future__ import annotations
import argparse, hashlib, json, math
from pathlib import Path
import numpy as np

TAU = 2 * math.pi

def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()

def exact_counts(values: np.ndarray) -> np.ndarray:
    max_v = int(values[-1])
    indicator = np.zeros(max_v + 1, dtype=np.float64)
    indicator[values] = 1.0
    conv_len = 2 * max_v + 1
    fft_len = 1 << (conv_len - 1).bit_length()
    spec = np.fft.rfft(indicator, n=fft_len)
    conv = np.fft.irfft(spec * spec, n=fft_len)[:conv_len]
    ordered = np.rint(conv).astype(np.int64)
    self_pairs = np.zeros(conv_len, dtype=np.int64)
    self_pairs[values * 2] = 1
    out = (ordered - self_pairs) // 2
    out[out < 0] = 0
    return out

def verify_ulam_prefix(values: np.ndarray, seed=(2,3)) -> bool:
    a, b = sorted(seed)
    if len(values) < 2 or int(values[0]) != a or int(values[1]) != b:
        return False

    # Saturated counts: 0, 1, or 2 where 2 means "2 or more".
    limit = int(values[-1]) + int(values[-2]) + 8
    counts = np.zeros(limit + 1, dtype=np.uint8)
    counts[a + b] = 1

    candidate = b + 1
    for k in range(2, len(values)):
        expected = int(values[k])
        while candidate < len(counts) and counts[candidate] != 1:
            candidate += 1
        if candidate != expected:
            print(f"prefix mismatch at index {k}: expected/generated {candidate}, file has {expected}")
            return False

        # Add new accepted value to representation counts.
        prev = values[:k].astype(np.int64)
        sums = prev + expected
        for s in sums:
            if counts[int(s)] < 2:
                counts[int(s)] += 1
        candidate += 1
    return True

def phase_bins(n: np.ndarray, alpha: float, bins: int) -> np.ndarray:
    phases = (n.astype(np.float64) * alpha) % TAU
    idx = np.floor(phases / TAU * bins).astype(np.int64)
    idx[idx == bins] = bins - 1
    return idx

def circular_smooth(x: np.ndarray, radius: int = 3) -> np.ndarray:
    y = np.zeros_like(x, dtype=float)
    for k in range(-radius, radius + 1):
        y += np.roll(x, k)
    return y / (2 * radius + 1)

def profile_for_interval(candidates: np.ndarray, R: np.ndarray, accepted_mask: np.ndarray, alpha: float, bins: int):
    idx = phase_bins(candidates, alpha, bins)
    total = np.bincount(idx, minlength=bins).astype(float)
    acc = np.bincount(idx[accepted_mask], minlength=bins).astype(float)
    crowded_mask = R[candidates] >= 2
    crowd = np.bincount(idx[crowded_mask], minlength=bins).astype(float)
    depth_sum = np.bincount(idx, weights=R[candidates].astype(float), minlength=bins)

    acc_density = np.divide(acc, total, out=np.zeros_like(acc), where=total > 0)
    crowd_density = np.divide(crowd, total, out=np.zeros_like(crowd), where=total > 0)
    mean_depth = np.divide(depth_sum, total, out=np.zeros_like(depth_sum), where=total > 0)

    md = circular_smooth(np.log1p(mean_depth), 3)
    ad = circular_smooth(acc_density, 3)

    def z(v):
        s = np.std(v)
        return (v - np.mean(v)) / (s if s > 0 else 1.0)

    score = z(md) - z(ad)
    return {
        "score": score,
        "acc_density": acc_density,
        "crowd_density": crowd_density,
        "mean_depth": mean_depth,
    }

def top_fraction_mask(score: np.ndarray, frac: float) -> np.ndarray:
    k = max(1, int(round(len(score) * frac)))
    order = np.argsort(score)[::-1]
    mask = np.zeros(len(score), dtype=bool)
    mask[order[:k]] = True
    return mask

def auc_binned(scores_by_bin: np.ndarray, pos_by_bin: np.ndarray, neg_by_bin: np.ndarray) -> float:
    order = np.argsort(scores_by_bin)
    total_pos = float(pos_by_bin.sum())
    total_neg = float(neg_by_bin.sum())
    if total_pos == 0 or total_neg == 0:
        return float("nan")
    cum_neg = 0.0
    win = 0.0
    i = 0
    while i < len(order):
        j = i + 1
        while j < len(order) and scores_by_bin[order[j]] == scores_by_bin[order[i]]:
            j += 1
        group = order[i:j]
        gpos = float(pos_by_bin[group].sum())
        gneg = float(neg_by_bin[group].sum())
        win += gpos * cum_neg + 0.5 * gpos * gneg
        cum_neg += gneg
        i = j
    return win / (total_pos * total_neg)

def verify_metrics(values: np.ndarray, R: np.ndarray, cert: dict) -> dict:
    alpha = float(cert["alpha"])
    bins = int(cert["bins"])
    wall_fraction = float(cert["wall_fraction"])
    train_count = int(cert["train_count"])
    test_count = int(cert["test_count"])

    train_max = int(values[train_count - 1])
    test_max = int(values[test_count - 1])

    train_candidates = np.arange(1, train_max + 1, dtype=np.int64)
    test_candidates = np.arange(train_max + 1, test_max + 1, dtype=np.int64)

    accepted = np.zeros(test_max + 1, dtype=bool)
    accepted[values[:test_count]] = True

    train_prof = profile_for_interval(train_candidates, R, accepted[train_candidates], alpha, bins)
    wall_mask = top_fraction_mask(train_prof["score"], wall_fraction)

    test_idx = phase_bins(test_candidates, alpha, bins)
    in_wall = wall_mask[test_idx]
    test_R = R[test_candidates]
    is_accepted = accepted[test_candidates]
    reachable = test_R >= 1
    rejected = test_R >= 2

    pos = np.bincount(test_idx[reachable & rejected], minlength=bins).astype(float)
    neg = np.bincount(test_idx[reachable & (~rejected)], minlength=bins).astype(float)
    auc = auc_binned(train_prof["score"], pos, neg)

    accepted_inside = float(is_accepted[in_wall].mean())
    accepted_outside = float(is_accepted[~in_wall].mean())
    mean_depth_wall = float(test_R[in_wall].mean())
    mean_depth_outside = float(test_R[~in_wall].mean())
    crowded_wall = float((test_R[in_wall] >= 2).mean())
    crowded_outside = float((test_R[~in_wall] >= 2).mean())

    future_prof = profile_for_interval(test_candidates, R, is_accepted, alpha, bins)
    center_train = int(np.argmax(circular_smooth(train_prof["score"], 5)))
    center_future = int(np.argmax(circular_smooth(future_prof["mean_depth"], 5)))
    gap = abs(center_train - center_future)
    gap = min(gap, bins - gap)

    return {
        "future_candidate_count": int(len(test_candidates)),
        "future_reachable_count": int(reachable.sum()),
        "future_accepted_count": int(is_accepted.sum()),
        "future_rejected_count": int(rejected.sum()),
        "rejection_auc": float(auc),
        "accepted_rate_inside_wall": accepted_inside,
        "accepted_rate_outside_wall": accepted_outside,
        "future_mean_depth_wall_ratio": mean_depth_wall / mean_depth_outside,
        "future_crowded_density_wall_ratio": crowded_wall / crowded_outside,
        "wall_center_gap_deg": float(gap * 360.0 / bins),
        "wall_bin_count": int(wall_mask.sum()),
        "wall_bins": np.nonzero(wall_mask)[0].astype(int).tolist(),
    }

def approx_equal(a, b, tol):
    return abs(float(a) - float(b)) <= tol

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cert", default="finite_certificate_u23_400k.json")
    ap.add_argument("--skip-prefix-rule-check", action="store_true",
                    help="Skip slow greedy prefix verification; still verifies hashes and metrics.")
    args = ap.parse_args()

    cert_path = Path(args.cert)
    cert = json.loads(cert_path.read_text())
    values_path = cert_path.parent / cert["values_file"]

    print("Loading values:", values_path)
    values = np.fromfile(values_path, dtype=np.int64)
    if len(values) != int(cert["N"]):
        raise SystemExit(f"wrong value count: got {len(values)}")

    got_hash = sha256_file(values_path)
    print("values_sha256:", got_hash)
    if got_hash != cert["values_sha256"]:
        raise SystemExit("values hash mismatch")

    if not args.skip_prefix_rule_check:
        print("Verifying greedy U(2,3) prefix rule. This may take time.")
        if not verify_ulam_prefix(values, tuple(cert["seed"])):
            raise SystemExit("Ulam prefix rule verification failed")
        print("prefix_rule: OK")
    else:
        print("prefix_rule: SKIPPED")

    print("Computing exact representation-depth counts.")
    R = exact_counts(values)
    r_hash = hashlib.sha256(R.tobytes()).hexdigest()
    print("representation_depth_sha256:", r_hash)
    if r_hash != cert["representation_depth_sha256"]:
        raise SystemExit("representation-depth hash mismatch")

    print("Recomputing held-out wall metrics.")
    metrics = verify_metrics(values, R, cert)
    reported = cert["reported_metrics"]

    tolerances = {
        "rejection_auc": 5e-6,
        "accepted_rate_inside_wall": 5e-8,
        "accepted_rate_outside_wall": 5e-6,
        "future_mean_depth_wall_ratio": 5e-5,
        "future_crowded_density_wall_ratio": 5e-5,
        "wall_center_gap_deg": 1e-9,
    }

    checks = {}
    for k, tol in tolerances.items():
        checks[k] = {
            "computed": metrics[k],
            "reported": reported[k],
            "tolerance": tol,
            "ok": approx_equal(metrics[k], reported[k], tol)
        }

    for k in ["future_candidate_count", "future_reachable_count", "future_accepted_count", "future_rejected_count"]:
        checks[k] = {
            "computed": metrics[k],
            "reported": reported[k],
            "tolerance": 0,
            "ok": int(metrics[k]) == int(reported[k])
        }

    ok = all(v["ok"] for v in checks.values())
    output = {
        "verdict": "finite_certificate_verified" if ok else "finite_certificate_failed",
        "checks": checks,
        "wall_bin_count": metrics["wall_bin_count"],
        "wall_bins_sha256": hashlib.sha256(json.dumps(metrics["wall_bins"], sort_keys=True).encode()).hexdigest(),
        "boundary": "Finite metrics verified; infinite conjecture not proven."
    }
    out_path = cert_path.parent / "finite_certificate_verification_result.json"
    out_path.write_text(json.dumps(output, indent=2, allow_nan=True))
    print(json.dumps(output, indent=2, allow_nan=True))
    if not ok:
        raise SystemExit(1)

if __name__ == "__main__":
    main()
