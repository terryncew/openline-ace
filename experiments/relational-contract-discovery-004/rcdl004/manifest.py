"""Write and independently verify RCDL-004 pressure-test manifests."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from rcdl.canonical import canonical_json, load_json_bytes

from .bindings import verify_frozen_bindings
from .corpus import load_frozen_corpus
from .features import feature_schema_digest
from .metrics import ClassificationScore, score_predictions

MANIFEST_SCHEMA = "rcdl.learned-pressure-test-manifest/0.4"
PREDICTION_SCHEMA = "rcdl.pressure-test-prediction/0.1"
ALLOWED_VERDICTS = frozenset(
    {"LEARNED_PARITY", "RCDL_STRICT_WIN", "LEARNED_STRICT_WIN", "MIXED_RESULT"}
)


class ManifestVerificationError(ValueError):
    pass


@dataclass(frozen=True)
class ManifestVerification:
    digest: str
    scientific_verdict: str
    prediction_count: int
    best_learned_model: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "verified": True,
            "digest": self.digest,
            "scientific_verdict": self.scientific_verdict,
            "prediction_count": self.prediction_count,
            "best_learned_model": self.best_learned_model,
            "promotion_authorized": False,
        }


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _is_digest(value: Any) -> bool:
    return isinstance(value, str) and len(value) == 64 and all(
        character in "0123456789abcdef" for character in value
    )


def write_bound_json(document: dict[str, Any], path: str | Path) -> str:
    target = Path(path)
    payload = canonical_json(document) + b"\n"
    target.write_bytes(payload)
    digest = _sha256(payload)
    target.with_suffix(target.suffix + ".sha256").write_text(
        f"{digest}  {target.name}\n", encoding="utf-8"
    )
    return digest


def _load_bound(path: Path) -> tuple[dict[str, Any], str]:
    payload = path.read_bytes()
    document = load_json_bytes(payload)
    if not isinstance(document, dict) or payload != canonical_json(document) + b"\n":
        raise ManifestVerificationError("manifest is not canonical")
    digest = _sha256(payload)
    sidecar = path.with_suffix(path.suffix + ".sha256")
    parts = sidecar.read_text(encoding="utf-8").strip().split() if sidecar.is_file() else []
    if len(parts) != 2 or parts[0] != digest or parts[1] != path.name:
        raise ManifestVerificationError("manifest sidecar mismatch")
    return document, digest


def _score_from_dict(value: dict[str, Any]) -> ClassificationScore:
    required = {"true_positive", "true_negative", "false_positive", "false_negative"}
    if not required <= set(value):
        raise ManifestVerificationError("score confusion matrix is incomplete")
    return ClassificationScore(*(value[key] for key in (
        "true_positive", "true_negative", "false_positive", "false_negative"
    )))


def _verdict(rcdl: ClassificationScore, learned: ClassificationScore) -> str:
    rcdl_key = (rcdl.balanced_accuracy_ppm, rcdl.failure_f1_ppm)
    learned_key = (learned.balanced_accuracy_ppm, learned.failure_f1_ppm)
    if rcdl_key == learned_key:
        return "LEARNED_PARITY"
    if rcdl.balanced_accuracy_ppm > learned.balanced_accuracy_ppm and rcdl.failure_f1_ppm >= learned.failure_f1_ppm:
        return "RCDL_STRICT_WIN"
    if learned.balanced_accuracy_ppm > rcdl.balanced_accuracy_ppm and learned.failure_f1_ppm >= rcdl.failure_f1_ppm:
        return "LEARNED_STRICT_WIN"
    return "MIXED_RESULT"


def _load_predictions(path: Path) -> tuple[dict[str, Any], ...]:
    rows: list[dict[str, Any]] = []
    previous = ""
    for line_number, raw in enumerate(path.read_bytes().splitlines(), 1):
        document = load_json_bytes(raw)
        if not isinstance(document, dict) or raw != canonical_json(document):
            raise ManifestVerificationError(f"non-canonical prediction row: {line_number}")
        if set(document) != {
            "schema", "example_id", "failed", "rcdl_prediction", "learned_predictions"
        } or document["schema"] != PREDICTION_SCHEMA:
            raise ManifestVerificationError(f"prediction schema failed: {line_number}")
        example_id = document["example_id"]
        if not isinstance(example_id, str) or example_id <= previous:
            raise ManifestVerificationError("predictions are not strictly ordered")
        previous = example_id
        rows.append(document)
    return tuple(rows)


def verify_manifest(path: str | Path) -> ManifestVerification:
    manifest_path = Path(path)
    document, digest = _load_bound(manifest_path)
    required = {
        "schema", "tool_version", "experiment_id", "pressure_test_id", "ace",
        "protocol", "tournament", "predictions", "claim_effect", "limitations", "verdict"
    }
    if set(document) != required or document["schema"] != MANIFEST_SCHEMA:
        raise ManifestVerificationError("manifest closure failed")
    if document["experiment_id"] != "relational-contract-discovery-004" or not _is_digest(document["pressure_test_id"]):
        raise ManifestVerificationError("manifest identity failed")
    if document["ace"] != {
        "level": "1_CANDIDATE",
        "promotion_authorized": False,
        "receipt_gate_authorization": "NONE",
    }:
        raise ManifestVerificationError("manifest authority expanded")
    protocol = document["protocol"]
    if protocol != {
        "status": "VALID_RESULT",
        "development_seeds_excluded": True,
        "final_audit_seed_count": 32,
        "same_builder": True,
        "independent_developer_or_lab": False,
        "stochastic_samples": False,
    }:
        raise ManifestVerificationError("protocol boundary changed")
    tournament = document["tournament"]
    if not isinstance(tournament, dict) or tournament.get("schema") != "rcdl.learned-baseline-tournament/0.1":
        raise ManifestVerificationError("tournament schema failed")
    if tournament.get("protocol_status") != "VALID_RESULT" or tournament.get("scientific_verdict") not in ALLOWED_VERDICTS:
        raise ManifestVerificationError("tournament verdict failed")
    binding = verify_frozen_bindings().to_dict()
    corpus = load_frozen_corpus()
    if tournament.get("bindings") != binding or tournament.get("corpus") != corpus.to_dict():
        raise ManifestVerificationError("tournament frozen binding mismatch")
    if tournament.get("feature_schema_digest") != feature_schema_digest():
        raise ManifestVerificationError("feature schema changed")
    prediction_record = document["predictions"]
    if not isinstance(prediction_record, dict) or set(prediction_record) != {
        "path", "sha256", "row_count", "schema"
    } or prediction_record["schema"] != PREDICTION_SCHEMA:
        raise ManifestVerificationError("prediction binding failed")
    prediction_path = (manifest_path.parent / prediction_record["path"]).resolve()
    if manifest_path.parent.resolve() not in prediction_path.parents or not prediction_path.is_file():
        raise ManifestVerificationError("prediction path escaped output directory")
    payload = prediction_path.read_bytes()
    if _sha256(payload) != prediction_record["sha256"]:
        raise ManifestVerificationError("prediction digest mismatch")
    rows = _load_predictions(prediction_path)
    test = corpus.split("test")
    if len(rows) != len(test) or prediction_record["row_count"] != len(rows):
        raise ManifestVerificationError("prediction count mismatch")
    models = tournament.get("learned_models")
    if not isinstance(models, list) or len(models) < 4:
        raise ManifestVerificationError("learned model tournament is incomplete")
    model_names = [item.get("name") for item in models if isinstance(item, dict)]
    if len(model_names) != len(models) or len(set(model_names)) != len(model_names):
        raise ManifestVerificationError("learned model identities failed")
    labels: list[bool] = []
    rcdl_predictions: list[bool] = []
    learned_predictions: dict[str, list[bool]] = {name: [] for name in model_names}
    for row, example in zip(rows, test):
        if row["example_id"] != example.example_id or row["failed"] is not example.failed:
            raise ManifestVerificationError("prediction row is not bound to frozen corpus")
        predictions = row["learned_predictions"]
        if not isinstance(predictions, dict) or set(predictions) != set(model_names):
            raise ManifestVerificationError("prediction model closure failed")
        if not isinstance(row["rcdl_prediction"], bool) or any(
            not isinstance(predictions[name], bool) for name in model_names
        ):
            raise ManifestVerificationError("prediction values must be boolean")
        labels.append(row["failed"])
        rcdl_predictions.append(row["rcdl_prediction"])
        for name in model_names:
            learned_predictions[name].append(predictions[name])
    rcdl_score = score_predictions(labels, rcdl_predictions)
    if tournament["rcdl_contract_predictor"]["test_score"] != rcdl_score.to_dict():
        raise ManifestVerificationError("RCDL score does not recompute")
    observed: dict[str, ClassificationScore] = {}
    for model in models:
        name = model["name"]
        score = score_predictions(labels, learned_predictions[name])
        observed[name] = score
        if model.get("test_score") != score.to_dict():
            raise ManifestVerificationError(f"learned score does not recompute: {name}")
    best_name = max(
        model_names,
        key=lambda name: (
            observed[name].balanced_accuracy_ppm,
            observed[name].failure_f1_ppm,
            observed[name].accuracy_ppm,
            name,
        ),
    )
    best_score = observed[best_name]
    if tournament.get("best_learned_model") != best_name or tournament.get("best_learned_score") != best_score.to_dict():
        raise ManifestVerificationError("best learned model selection failed")
    scientific = _verdict(rcdl_score, best_score)
    if tournament["scientific_verdict"] != scientific or document["verdict"] != f"PRESSURE_TEST_VALID_{scientific}":
        raise ManifestVerificationError("scientific verdict does not recompute")
    expected_effect = (
        "PREDICTIVE_SUPERIORITY_FALSIFIED_WITHIN_TOURNAMENT"
        if scientific in {"LEARNED_PARITY", "LEARNED_STRICT_WIN"}
        else "BOUNDED_PREDICTIVE_ADVANTAGE_SUPPORTED"
        if scientific == "RCDL_STRICT_WIN"
        else "PREDICTIVE_COMPARISON_UNDECIDABLE"
    )
    if document["claim_effect"] != expected_effect:
        raise ManifestVerificationError("claim effect mismatch")
    return ManifestVerification(digest, scientific, len(rows), best_name)

