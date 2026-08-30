from __future__ import annotations

import hashlib
import itertools
import json
import math
from collections import Counter, defaultdict
from pathlib import Path
from typing import Iterable

from .fixtures import SCHEMA, canonical_rows

EVIDENCE_MODES = {
    "deterministic_rollout",
    "stochastic_rollout",
    "validated_dynamics_model",
}


class CorpusError(ValueError):
    pass


def load_policy(path: Path | None = None) -> dict:
    path = path or Path(__file__).resolve().parents[1] / "PREREGISTRATION.json"
    return json.loads(path.read_text(encoding="utf-8"))


def load_jsonl(path: Path) -> list[dict]:
    rows: list[dict] = []
    for line_number, line in enumerate(
        path.read_text(encoding="utf-8").splitlines(), 1
    ):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError as exc:
            raise CorpusError(f"line {line_number}: invalid JSON") from exc
        if not isinstance(row, dict):
            raise CorpusError(f"line {line_number}: row must be an object")
        rows.append(row)
    return rows


def dataset_sha256(rows: Iterable[dict]) -> str:
    payload = "".join(
        json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n"
        for row in canonical_rows(rows)
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _is_sha256(value: object) -> bool:
    if not isinstance(value, str) or len(value) != 64:
        return False
    try:
        int(value, 16)
    except ValueError:
        return False
    return True


def _validate(
    rows: list[dict], policy: dict
) -> tuple[str, str, list[str], list[str], list[int]]:
    if not rows:
        raise CorpusError("corpus is empty")

    required = {
        "schema",
        "dataset_id",
        "evidence_mode",
        "context_id",
        "snapshot_sha256",
        "apparent_risk_bucket",
        "action_id",
        "lag_ms",
        "replicate",
        "trial_id",
        "target_sha256",
        "constraint_set_sha256",
        "policy_authority",
    }
    dataset_ids: set[str] = set()
    modes: set[str] = set()
    target_hashes: set[str] = set()
    constraint_hashes: set[str] = set()
    validation_hashes: set[str] = set()
    trial_ids: set[str] = set()
    contexts: dict[str, dict[str, set[str]]] = defaultdict(
        lambda: {"snapshots": set(), "risks": set()}
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

        mode = str(row["evidence_mode"])
        if mode not in EVIDENCE_MODES:
            raise CorpusError(f"row {index}: unsupported evidence_mode")
        modes.add(mode)
        if row["policy_authority"] != "NONE":
            raise CorpusError(f"row {index}: policy_authority must be NONE")

        if not isinstance(row["lag_ms"], int) or row["lag_ms"] < 0:
            raise CorpusError(f"row {index}: lag_ms must be a nonnegative integer")
        if not isinstance(row["replicate"], int) or row["replicate"] < 0:
            raise CorpusError(f"row {index}: replicate must be a nonnegative integer")
        if mode != "stochastic_rollout" and row["replicate"] != 0:
            raise CorpusError(
                f"row {index}: one-row evidence modes require replicate zero"
            )

        for field in (
            "snapshot_sha256",
            "target_sha256",
            "constraint_set_sha256",
        ):
            if not _is_sha256(row[field]):
                raise CorpusError(f"row {index}: {field} must be SHA-256 hex")

        if mode in {"deterministic_rollout", "stochastic_rollout"}:
            if not isinstance(row.get("outcome_success"), bool):
                raise CorpusError(f"row {index}: outcome_success must be boolean")
        else:
            probability = row.get("success_probability")
            if (
                isinstance(probability, bool)
                or not isinstance(probability, (int, float))
                or not math.isfinite(float(probability))
                or not 0.0 <= float(probability) <= 1.0
            ):
                raise CorpusError(
                    f"row {index}: success_probability must be finite in [0,1]"
                )
            validation_hash = row.get("model_validation_receipt_sha256")
            if not _is_sha256(validation_hash):
                raise CorpusError(
                    f"row {index}: validated model requires a validation receipt"
                )
            validation_hashes.add(str(validation_hash))

        dataset_id = str(row["dataset_id"]).strip()
        context_id = str(row["context_id"]).strip()
        action_id = str(row["action_id"]).strip()
        risk_bucket = str(row["apparent_risk_bucket"]).strip()
        trial_id = str(row["trial_id"]).strip()
        if not all((dataset_id, context_id, action_id, risk_bucket, trial_id)):
            raise CorpusError(f"row {index}: identity fields must be nonempty")
        if trial_id in trial_ids:
            raise CorpusError(f"duplicate trial_id: {trial_id}")
        trial_ids.add(trial_id)

        dataset_ids.add(dataset_id)
        target_hashes.add(str(row["target_sha256"]))
        constraint_hashes.add(str(row["constraint_set_sha256"]))
        contexts[context_id]["snapshots"].add(str(row["snapshot_sha256"]))
        contexts[context_id]["risks"].add(risk_bucket)
        actions.add(action_id)
        lag = int(row["lag_ms"])
        lags.add(lag)
        cell_key = (context_id, action_id, lag)
        replicate = int(row["replicate"])
        if replicate in cell_replicates[cell_key]:
            raise CorpusError(
                f"cell {cell_key}: duplicate replicate index {replicate}"
            )
        cell_replicates[cell_key].add(replicate)

    if len(dataset_ids) != 1:
        raise CorpusError("exactly one dataset_id is required")
    if len(modes) != 1:
        raise CorpusError("exactly one evidence_mode is required")
    if len(target_hashes) != 1:
        raise CorpusError("exactly one recovery-target hash is required")
    if len(constraint_hashes) != 1:
        raise CorpusError("exactly one constraint-set hash is required")
    mode = next(iter(modes))
    if mode == "validated_dynamics_model" and len(validation_hashes) != 1:
        raise CorpusError("exactly one model-validation receipt is required")

    for context_id, values in contexts.items():
        if len(values["snapshots"]) != 1:
            raise CorpusError(f"context {context_id}: snapshot changed across arms")
        if len(values["risks"]) != 1:
            raise CorpusError(f"context {context_id}: apparent-risk bucket changed")

    if mode != "stochastic_rollout":
        repeated = [key for key, values in cell_replicates.items() if len(values) != 1]
        if repeated:
            raise CorpusError(
                "one-row evidence mode contains repeated cells; deterministic "
                "pseudoreplication is forbidden"
            )

    return (
        next(iter(dataset_ids)),
        mode,
        sorted(contexts),
        sorted(actions),
        sorted(lags),
    )


def _status(probability: float, thresholds: dict) -> str:
    if probability >= thresholds["feasible_success_probability"]:
        return "FEASIBLE"
    if probability <= thresholds["infeasible_success_probability"]:
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


def _invalid_report(policy: dict, error: str) -> dict:
    return {
        "schema": "openline.ace.intervention-sufficiency.report.v2",
        "experiment_id": policy["experiment_id"],
        "verdict": policy["invalid_verdict"],
        "errors": [error],
        "transition_confirmation_authorized": False,
        "capacity_selector_training_authorized": False,
        "policy_authority": "NONE",
        "execution_authority": "NONE",
    }


def audit_rows(rows: list[dict], policy: dict | None = None) -> dict:
    policy = policy or load_policy()
    thresholds = policy["thresholds"]
    try:
        dataset_id, mode, contexts, actions, lags = _validate(rows, policy)
    except CorpusError as exc:
        return _invalid_report(policy, str(exc))

    values: dict[tuple[str, str, int], list[float]] = defaultdict(list)
    risk_by_context: dict[str, str] = {}
    for row in rows:
        key = (
            str(row["context_id"]),
            str(row["action_id"]),
            int(row["lag_ms"]),
        )
        if mode == "validated_dynamics_model":
            values[key].append(float(row["success_probability"]))
        else:
            values[key].append(float(bool(row["outcome_success"])))
        risk_by_context[str(row["context_id"])] = str(
            row["apparent_risk_bucket"]
        )

    required_actions = sorted(str(value) for value in thresholds["required_actions"])
    required_lags = sorted(int(value) for value in thresholds["required_lags_ms"])
    expected_cells = len(contexts) * len(required_actions) * len(required_lags)
    stochastic_min = int(thresholds["stochastic_min_replicates_per_cell"])

    complete_contexts = 0
    statuses: dict[tuple[str, str, int], str] = {}
    for context in contexts:
        context_complete = True
        for action in required_actions:
            for lag in required_lags:
                cell = values.get((context, action, lag), [])
                required_count = stochastic_min if mode == "stochastic_rollout" else 1
                if len(cell) < required_count:
                    context_complete = False
                    statuses[(context, action, lag)] = "UNKNOWN"
                else:
                    statuses[(context, action, lag)] = _status(
                        sum(cell) / len(cell), thresholds
                    )
        complete_contexts += int(context_complete)

    complete_rate = complete_contexts / len(contexts) if contexts else 0.0
    determinate_count = sum(value != "UNKNOWN" for value in statuses.values())
    determinate_rate = (
        determinate_count / expected_cells if expected_cells else 0.0
    )

    state_dependent_strata = 0
    global_correct = 0
    global_total = 0
    for action in required_actions:
        for lag in required_lags:
            observed = [statuses[(context, action, lag)] for context in contexts]
            observed = [value for value in observed if value != "UNKNOWN"]
            distinct = set(observed)
            if {"FEASIBLE", "INFEASIBLE"}.issubset(distinct):
                state_dependent_strata += 1
            counts = Counter(observed)
            if counts:
                global_correct += max(counts.values())
                global_total += sum(counts.values())
    global_accuracy = global_correct / global_total if global_total else 1.0

    contexts_by_risk: dict[str, list[str]] = defaultdict(list)
    for context in contexts:
        contexts_by_risk[risk_by_context[context]].append(context)
    divergent_pairs: set[tuple[str, str]] = set()
    paired_contexts: set[str] = set()
    pair_examples: list[dict] = []
    for risk_bucket, risk_contexts in sorted(contexts_by_risk.items()):
        for left, right in itertools.combinations(sorted(risk_contexts), 2):
            for lag in required_lags:
                left_set = {
                    action
                    for action in required_actions
                    if statuses[(left, action, lag)] == "FEASIBLE"
                }
                right_set = {
                    action
                    for action in required_actions
                    if statuses[(right, action, lag)] == "FEASIBLE"
                }
                left_only = left_set - right_set
                right_only = right_set - left_set
                if left_only and right_only:
                    divergent_pairs.add((left, right))
                    paired_contexts.update((left, right))
                    if len(pair_examples) < 12:
                        pair_examples.append(
                            {
                                "risk_bucket": risk_bucket,
                                "context_a": left,
                                "context_b": right,
                                "lag_ms": lag,
                                "a_only": sorted(left_only),
                                "b_only": sorted(right_only),
                            }
                        )
                    break

    contractions: list[dict] = []
    for context in contexts:
        for action in required_actions:
            sequence = [statuses[(context, action, lag)] for lag in required_lags]
            contraction = None
            for later in range(1, len(sequence)):
                if sequence[later] != "INFEASIBLE":
                    continue
                earlier_feasible = [
                    index
                    for index in range(later)
                    if sequence[index] == "FEASIBLE"
                ]
                if earlier_feasible and "FEASIBLE" not in sequence[later + 1 :]:
                    contraction = {
                        "context_id": context,
                        "action_id": action,
                        "last_feasible_lag_ms": required_lags[max(earlier_feasible)],
                        "first_terminal_infeasible_lag_ms": required_lags[later],
                    }
                    break
            if contraction:
                contractions.append(contraction)

    gates = {
        "contexts": _gate(
            len(contexts), "==", int(thresholds["required_contexts"])
        ),
        "actions": _gate(actions, "==", required_actions),
        "lags": _gate(lags, "==", required_lags),
        "complete_context_rate": _gate(
            complete_rate, ">=", thresholds["min_complete_context_rate"]
        ),
        "determinate_cell_rate": _gate(
            determinate_rate, ">=", thresholds["min_determinate_cell_rate"]
        ),
        "state_dependent_action_lag_strata": _gate(
            state_dependent_strata,
            ">=",
            thresholds["min_state_dependent_action_lag_strata"],
        ),
        "bidirectional_remedy_divergent_risk_pairs": _gate(
            len(divergent_pairs),
            ">=",
            thresholds["min_bidirectional_remedy_divergent_risk_pairs"],
        ),
        "contexts_in_divergent_pairs": _gate(
            len(paired_contexts),
            ">=",
            thresholds["min_contexts_in_divergent_pairs"],
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
        "schema": "openline.ace.intervention-sufficiency.report.v2",
        "experiment_id": policy["experiment_id"],
        "dataset_id": dataset_id,
        "dataset_sha256": dataset_sha256(rows),
        "evidence_mode": mode,
        "verdict": verdict,
        "metrics": {
            "row_count": len(rows),
            "context_count": len(contexts),
            "action_count": len(actions),
            "lags_ms": required_lags,
            "expected_cell_count": expected_cells,
            "observed_cell_count": len(values),
            "complete_context_rate": complete_rate,
            "determinate_cell_rate": determinate_rate,
            "state_dependent_action_lag_strata": state_dependent_strata,
            "bidirectional_remedy_divergent_risk_pairs": len(divergent_pairs),
            "contexts_in_divergent_pairs": len(paired_contexts),
            "lag_contraction_count": len(contractions),
            "global_action_delay_cell_accuracy": global_accuracy,
        },
        "gates": gates,
        "remedy_divergence_examples": pair_examples,
        "lag_contraction_examples": contractions[:12],
        "transition_confirmation_authorized": passed,
        "capacity_selector_training_authorized": False,
        "next_step": (
            policy["next_if_success"] if passed else policy["next_if_failure"]
        ),
        "scientific_standing": policy["scientific_standing"],
        "claim_boundary": (
            "Data sufficiency only. No model performance, complete feasible set, "
            "capacity benefit, hardware transfer, or execution authority is established."
        ),
        "policy_authority": "NONE",
        "execution_authority": "NONE",
        "receipt_gate_required_for_execution": True,
    }
