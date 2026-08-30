from __future__ import annotations

import hashlib
import itertools
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Iterable

from .fixtures import SCHEMA, canonical_rows

VALID_STATUSES = {"FEASIBLE", "INFEASIBLE", "UNKNOWN"}


class CorpusError(ValueError):
    pass


def load_policy(path: Path | None = None) -> dict:
    path = path or Path(__file__).resolve().parents[1] / "PREREGISTRATION.json"
    return json.loads(path.read_text(encoding="utf-8"))


def load_jsonl(path: Path) -> list[dict]:
    rows: list[dict] = []
    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError as exc:
            raise CorpusError(f"line {line_no}: invalid JSON") from exc
        if not isinstance(row, dict):
            raise CorpusError(f"line {line_no}: row must be an object")
        rows.append(row)
    return rows


def _dataset_sha256(rows: Iterable[dict]) -> str:
    payload = "".join(
        json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n"
        for row in canonical_rows(rows)
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _validate(rows: list[dict]) -> tuple[str, list[str], list[str], list[int]]:
    if not rows:
        raise CorpusError("corpus is empty")
    required = {
        "schema",
        "dataset_id",
        "context_id",
        "snapshot_sha256",
        "apparent_risk_bucket",
        "action_id",
        "lag_ms",
        "replicate",
        "trial_id",
        "recovered",
        "target_sha256",
        "policy_authority",
    }
    dataset_ids: set[str] = set()
    target_hashes: set[str] = set()
    trial_ids: set[str] = set()
    by_context: dict[str, dict[str, set]] = defaultdict(
        lambda: {"snapshots": set(), "risks": set(), "targets": set()}
    )
    actions: set[str] = set()
    lags: set[int] = set()
    cell_replicates: dict[tuple[str, str, int], set[int]] = defaultdict(set)
    for index, row in enumerate(rows):
        missing = sorted(required - set(row))
        if missing:
            raise CorpusError(f"row {index}: missing fields {missing}")
        if row["schema"] != SCHEMA:
            raise CorpusError(f"row {index}: unsupported schema")
        if row["policy_authority"] != "NONE":
            raise CorpusError(f"row {index}: policy_authority must be NONE")
        if not isinstance(row["recovered"], bool):
            raise CorpusError(f"row {index}: recovered must be boolean")
        if not isinstance(row["lag_ms"], int) or row["lag_ms"] < 0:
            raise CorpusError(f"row {index}: lag_ms must be a nonnegative integer")
        if not isinstance(row["replicate"], int) or row["replicate"] < 0:
            raise CorpusError(f"row {index}: replicate must be a nonnegative integer")
        for field in ("snapshot_sha256", "target_sha256"):
            value = row[field]
            if not isinstance(value, str) or len(value) != 64:
                raise CorpusError(f"row {index}: {field} must be a SHA-256 hex string")
            try:
                int(value, 16)
            except ValueError as exc:
                raise CorpusError(f"row {index}: {field} must be hexadecimal") from exc
        trial_id = str(row["trial_id"])
        if trial_id in trial_ids:
            raise CorpusError(f"duplicate trial_id: {trial_id}")
        trial_ids.add(trial_id)
        dataset_ids.add(str(row["dataset_id"]))
        target_hashes.add(str(row["target_sha256"]))
        context_id = str(row["context_id"])
        by_context[context_id]["snapshots"].add(row["snapshot_sha256"])
        by_context[context_id]["risks"].add(str(row["apparent_risk_bucket"]))
        by_context[context_id]["targets"].add(row["target_sha256"])
        actions.add(str(row["action_id"]))
        lags.add(int(row["lag_ms"]))
        cell_key = (context_id, str(row["action_id"]), int(row["lag_ms"]))
        replicate = int(row["replicate"])
        if replicate in cell_replicates[cell_key]:
            raise CorpusError(
                f"cell {cell_key}: duplicate replicate index {replicate}"
            )
        cell_replicates[cell_key].add(replicate)
    if len(dataset_ids) != 1:
        raise CorpusError("exactly one dataset_id is required")
    if len(target_hashes) != 1:
        raise CorpusError("exactly one recovery-target hash is required")
    for context_id, values in by_context.items():
        if len(values["snapshots"]) != 1:
            raise CorpusError(f"context {context_id}: snapshot changed across branches")
        if len(values["risks"]) != 1:
            raise CorpusError(f"context {context_id}: apparent-risk bucket changed")
        if len(values["targets"]) != 1:
            raise CorpusError(f"context {context_id}: recovery target changed")
    return next(iter(dataset_ids)), sorted(by_context), sorted(actions), sorted(lags)


def _cell_status(rate: float, policy: dict) -> str:
    thresholds = policy["thresholds"]
    if rate >= thresholds["feasible_recovery_rate"]:
        return "FEASIBLE"
    if rate <= thresholds["infeasible_recovery_rate"]:
        return "INFEASIBLE"
    return "UNKNOWN"


def _gate(observed, relation: str, required) -> dict:
    if relation == ">=":
        passed = observed >= required
    elif relation == "<=":
        passed = observed <= required
    elif relation == "==":
        passed = observed == required
    else:
        raise ValueError(relation)
    return {
        "passed": bool(passed),
        "observed": observed,
        "relation": relation,
        "required": required,
    }


def audit_rows(rows: list[dict], policy: dict | None = None) -> dict:
    policy = policy or load_policy()
    thresholds = policy["thresholds"]
    try:
        dataset_id, contexts, actions, lags = _validate(rows)
    except CorpusError as exc:
        return {
            "schema": "openline.ace.intervention-sufficiency.report.v1",
            "experiment_id": policy["experiment_id"],
            "verdict": policy["invalid_verdict"],
            "errors": [str(exc)],
            "policy_authority": "NONE",
            "execution_authority": "NONE",
        }

    cell_trials: dict[tuple[str, str, int], list[bool]] = defaultdict(list)
    risk_by_context: dict[str, str] = {}
    for row in rows:
        key = (str(row["context_id"]), str(row["action_id"]), int(row["lag_ms"]))
        cell_trials[key].append(bool(row["recovered"]))
        risk_by_context[str(row["context_id"])] = str(row["apparent_risk_bucket"])

    expected_lags = [int(v) for v in thresholds["required_lags_ms"]]
    expected_cells = len(contexts) * len(actions) * len(expected_lags)
    complete_contexts = 0
    for context in contexts:
        complete = all(
            len(cell_trials.get((context, action, lag), []))
            >= thresholds["min_replicates_per_cell"]
            for action in actions
            for lag in expected_lags
        )
        complete_contexts += int(complete)
    complete_context_rate = complete_contexts / len(contexts)

    statuses: dict[tuple[str, str, int], str] = {}
    recovery_rates: dict[tuple[str, str, int], float] = {}
    for context in contexts:
        for action in actions:
            for lag in expected_lags:
                trials = cell_trials.get((context, action, lag), [])
                if not trials:
                    statuses[(context, action, lag)] = "UNKNOWN"
                    continue
                rate = sum(trials) / len(trials)
                recovery_rates[(context, action, lag)] = rate
                if len(trials) < thresholds["min_replicates_per_cell"]:
                    statuses[(context, action, lag)] = "UNKNOWN"
                else:
                    statuses[(context, action, lag)] = _cell_status(rate, policy)

    determinate = sum(status != "UNKNOWN" for status in statuses.values())
    determinate_rate = determinate / expected_cells if expected_cells else 0.0

    state_dependent_strata = 0
    global_correct = 0
    global_total = 0
    for action in actions:
        for lag in expected_lags:
            observed = [statuses[(context, action, lag)] for context in contexts]
            determinate_observed = [s for s in observed if s != "UNKNOWN"]
            if {"FEASIBLE", "INFEASIBLE"}.issubset(set(determinate_observed)):
                state_dependent_strata += 1
            counts = Counter(determinate_observed)
            if not counts:
                prediction = "UNKNOWN"
            elif counts["FEASIBLE"] == counts["INFEASIBLE"]:
                prediction = "UNKNOWN"
            else:
                prediction = counts.most_common(1)[0][0]
            for status in determinate_observed:
                global_total += 1
                global_correct += int(prediction == status)
    global_accuracy = global_correct / global_total if global_total else 1.0

    pair_keys: set[tuple[str, str]] = set()
    paired_contexts: set[str] = set()
    contexts_by_risk: dict[str, list[str]] = defaultdict(list)
    for context in contexts:
        contexts_by_risk[risk_by_context[context]].append(context)
    for risk_contexts in contexts_by_risk.values():
        for left, right in itertools.combinations(sorted(risk_contexts), 2):
            divergent = False
            for lag in expected_lags:
                left_set = {
                    action for action in actions if statuses[(left, action, lag)] == "FEASIBLE"
                }
                right_set = {
                    action for action in actions if statuses[(right, action, lag)] == "FEASIBLE"
                }
                if left_set and right_set and left_set != right_set:
                    divergent = True
                    break
            if divergent:
                pair_keys.add((left, right))
                paired_contexts.update((left, right))

    contractions: list[dict] = []
    for context in contexts:
        for action in actions:
            sequence = [statuses[(context, action, lag)] for lag in expected_lags]
            feasible_indices = [i for i, s in enumerate(sequence) if s == "FEASIBLE"]
            infeasible_indices = [i for i, s in enumerate(sequence) if s == "INFEASIBLE"]
            if feasible_indices and infeasible_indices and max(feasible_indices) < max(infeasible_indices):
                first_infeasible_after = next(
                    (i for i in infeasible_indices if i > min(feasible_indices)), None
                )
                if first_infeasible_after is not None and not any(
                    sequence[i] == "FEASIBLE" for i in range(first_infeasible_after + 1, len(sequence))
                ):
                    contractions.append(
                        {
                            "context_id": context,
                            "action_id": action,
                            "last_feasible_lag_ms": expected_lags[
                                max(i for i in feasible_indices if i < first_infeasible_after)
                            ],
                            "first_infeasible_lag_ms": expected_lags[first_infeasible_after],
                        }
                    )

    gates = {
        "contexts": _gate(len(contexts), ">=", thresholds["min_contexts"]),
        "actions": _gate(len(actions), ">=", thresholds["min_actions"]),
        "required_lags": _gate(lags, "==", expected_lags),
        "complete_context_rate": _gate(
            complete_context_rate, ">=", thresholds["min_complete_context_rate"]
        ),
        "determinate_cell_rate": _gate(
            determinate_rate, ">=", thresholds["min_determinate_cell_rate"]
        ),
        "state_dependent_action_lag_strata": _gate(
            state_dependent_strata,
            ">=",
            thresholds["min_state_dependent_action_lag_strata"],
        ),
        "remedy_divergent_risk_pairs": _gate(
            len(pair_keys), ">=", thresholds["min_remedy_divergent_risk_pairs"]
        ),
        "contexts_in_divergent_pairs": _gate(
            len(paired_contexts), ">=", thresholds["min_contexts_in_divergent_pairs"]
        ),
        "lag_contractions": _gate(
            len(contractions), ">=", thresholds["min_lag_contractions"]
        ),
        "global_action_delay_cell_accuracy": _gate(
            global_accuracy,
            "<=",
            thresholds["max_global_action_delay_cell_accuracy"],
        ),
    }
    passed = all(gate["passed"] for gate in gates.values())
    verdict = policy["success_verdict"] if passed else policy["failure_verdict"]
    return {
        "schema": "openline.ace.intervention-sufficiency.report.v1",
        "experiment_id": policy["experiment_id"],
        "dataset_id": dataset_id,
        "dataset_sha256": _dataset_sha256(rows),
        "verdict": verdict,
        "metrics": {
            "row_count": len(rows),
            "context_count": len(contexts),
            "action_count": len(actions),
            "lags_ms": expected_lags,
            "expected_cell_count": expected_cells,
            "observed_cell_count": len(cell_trials),
            "complete_context_rate": complete_context_rate,
            "determinate_cell_rate": determinate_rate,
            "state_dependent_action_lag_strata": state_dependent_strata,
            "remedy_divergent_risk_pairs": len(pair_keys),
            "contexts_in_divergent_pairs": len(paired_contexts),
            "lag_contraction_count": len(contractions),
            "global_action_delay_cell_accuracy": global_accuracy,
        },
        "gates": gates,
        "lag_contractions": contractions,
        "capacity_selector_training_authorized": False,
        "next_if_passed": policy["next_if_success"],
        "claim_boundary": "Data sufficiency only; no model accuracy, capacity benefit, hardware safety, or execution authority is established.",
        "policy_authority": "NONE",
        "execution_authority": "NONE",
        "receipt_gate_required_for_execution": True,
    }
